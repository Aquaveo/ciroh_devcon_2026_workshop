from datetime import datetime
from typing import Any, Dict, Optional
import fsspec
import xarray as xr
import duckdb
import pandas as pd
import re
import logging
from botocore.exceptions import ClientError

HTTP_TIMEOUT_SECONDS = 60
BUCKET = "ciroh-community-ngen-datastream"
OUTPUTS_DIR = "outputs"
PREFIX_HYDROFABRIC = "v2.2_hydrofabric"
NGEN_RUN_PREFIX = "ngen-run/outputs/troute"
_OUTPUT_SQL_START_RE = re.compile(r"(?is)^\s*(?:WITH\b.*?\bSELECT\b|SELECT\b)")
_OUTPUT_SQL_FROM_OUTPUT_RE = re.compile(r"(?is)\bFROM\s+output\b")
_OUTPUT_SQL_FORBIDDEN_RE = re.compile(
    r"(?is)\b(?:INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|COPY|ATTACH|DETACH|CALL|PRAGMA|VACUUM|TRUNCATE|MERGE|REPLACE)\b"
)

_DUCKDB_CANDIDATES_RE = re.compile(
    r'Candidate bindings:\s*(.+?)(?:\n|$)', re.IGNORECASE
)
_IO_ERROR_CATALOG = {
    "timeout": (
        "Upstream request timed out.",
        "Upstream timed out. Retry the same call once; if it fails again, "
        "surface the error to the user and try a different selector "
        "(e.g., a different date or forecast cycle).",
    ),
    "permission_denied": (
        "Access denied to the upstream data store.",
        "Access denied to the upstream data store. Do NOT retry - this is "
        "a deployment configuration issue. Surface to the user as a "
        "server-side problem.",
    ),
    "upstream_error": (
        "Upstream data store error.",
        "Upstream data store error. Do NOT retry the same call - try a "
        "different selector combination (model/date/forecast/vpu) before "
        "reporting failure to the user.",
    ),
    "not_found": (
        "Requested resource was not found.",
        "Requested resource was not found. Do NOT retry the same call - "
        "the selector combination does not match any available data. Try "
        "a different selector or check what's available via the "
        "corresponding list_* tool.",
    ),
    "execution_error": (
        "Internal execution error.",
        "Internal execution error. Do NOT retry - surface to the user. If "
        "reproducible, this is a server-side bug.",
    ),
}

def _classify_io_error(exc: BaseException) -> tuple[str, str, str]:
    """Return (error_code, sanitized_message, fix_hint) for any caught IO exception.

    Maps the raised exception class to a stable error code and per-code
    sanitized text. The raw ``str(exc)`` is intentionally NOT propagated
    into the LLM-facing envelope - see _IO_ERROR_CATALOG for the rationale.

    Programmer-error DuckDB classes (BinderException, ParserException,
    CatalogException) MUST be re-raised before reaching this helper -
    classifying them as execution_error would mask wrong-column / malformed
    -SQL / missing-table bugs and let an LLM retry forever. Callers should
    check ``isinstance(exc, (duckdb.BinderException, duckdb.ParserException,
    duckdb.CatalogException))`` and re-raise before calling this function.
    """
    from botocore.exceptions import ClientError

    code: str
    if isinstance(exc, TimeoutError):
        code = "timeout"
    elif isinstance(exc, PermissionError):
        code = "permission_denied"
    elif isinstance(exc, FileNotFoundError):
        code = "not_found"
    elif isinstance(exc, ClientError):
        # Inspect the AWS error code for AccessDenied / NoSuchKey
        aws_code = exc.response.get("Error", {}).get("Code", "")
        if aws_code in ("AccessDenied", "403"):
            code = "permission_denied"
        elif aws_code in ("NoSuchKey", "NoSuchBucket", "404"):
            code = "not_found"
        else:
            code = "upstream_error"
    elif isinstance(exc, duckdb.IOException):
        code = "upstream_error"
    elif isinstance(exc, ConnectionError):
        code = "upstream_error"
    elif isinstance(exc, OSError):
        # OSError parent covers many filesystem/network classes not pinned above.
        # Default to upstream_error for these; if a more specific case
        # emerges in production, branch here.
        code = "upstream_error"
    else:
        code = "execution_error"

    message, fix_hint = _IO_ERROR_CATALOG[code]
    return code, message, fix_hint

def s3fs_config_kwargs() -> Dict:
    """Build config_kwargs for s3fs / fsspec("s3", ...) - passed directly
    to botocore.client.Config(...) by s3fs.

    Cannot use ``client_kwargs={"config": Config(...)}`` because s3fs
    already passes a `config=` kwarg internally to
    `session.create_client(...)`; supplying our own collides with
    `TypeError: got multiple values for keyword argument 'config'`.

    ``config_kwargs`` is the s3fs-supported alternative.

    Disabling retries (``max_attempts=1``) ensures the per-request budget
    isn't multiplied by the default 3 retry attempts - a 60s timeout means
    60s, not potentially 180s.
    """
    return {
        "connect_timeout": HTTP_TIMEOUT_SECONDS,
        "read_timeout": HTTP_TIMEOUT_SECONDS,
        "retries": {"max_attempts": 1},
    }

def s3_filesystem() -> Any:
    """Return a timeout-configured anonymous S3 fsspec filesystem.

    ``skip_instance_cache=True`` is load-bearing: fsspec caches filesystem
    instances by args-hash; if any prior code path called
    ``fsspec.filesystem("s3", anon=True)`` without config_kwargs, that
    instance would be returned for subsequent timeout-configured calls,
    silently dropping the config. Per-call instantiation guarantees the
    timeout reaches the underlying transport.
    """
    return fsspec.filesystem(
        "s3",
        anon=True,
        config_kwargs=s3fs_config_kwargs(),
        skip_instance_cache=True,
    )

def normalize_date_yyyymmdd(date_str: str | None) -> str | None:
    """Normalize a date string to YYYYMMDD.

    Accepts:
      - YYYYMMDD
      - YYYY-MM-DD
      - YYYY/MM/DD
    """
    if not date_str:
        return None

    s = str(date_str).strip()
    if len(s) == 8 and s.isdigit():
        return s

    s = s.replace("/", "-")
    try:
        return datetime.strptime(s, "%Y-%m-%d").strftime("%Y%m%d")
    except ValueError:
        return None

def normalize_date_folder(date_str: str | None, *, default_prefix: str = "ngen") -> str | None:
    """Normalize a date folder name for the S3 layout.

    The datastream commonly uses folders like: ngen.YYYYMMDD

    Accepts:
      - ngen.YYYYMMDD
      - ngen.YYYY-MM-DD
      - ngen.YYYY/MM/DD
      - YYYYMMDD / YYYY-MM-DD / YYYY/MM/DD (prefix added)
    """
    if not date_str:
        return None

    s = str(date_str).strip()
    if "." in s:
        prefix, tail = s.split(".", 1)
        yyyymmdd = normalize_date_yyyymmdd(tail)
        return f"{prefix}.{yyyymmdd}" if yyyymmdd else None

    yyyymmdd = normalize_date_yyyymmdd(s)
    return f"{default_prefix}.{yyyymmdd}" if yyyymmdd else None

def success_payload(**kwargs) -> Dict[str, Any]:
    return {
        "ok": True,
        "error": None,
        **kwargs,
    }

def error_payload(
    code: str,
    message: str,
    *,
    details: Any = None,
    **kwargs,
) -> Dict[str, Any]:
    error_obj = {
        "code": code,
        "message": message,
    }
    if details is not None:
        error_obj["details"] = details

    return {
        "ok": False,
        "error": error_obj,
        **kwargs,
    }

def duckdb_connect_with_httpfs(database: str = ":memory:") -> duckdb.DuckDBPyConnection:
    """Return a DuckDB connection with httpfs loaded and http_timeout set.

    ``SET http_timeout = N`` is in SECONDS (verified against DuckDB 1.x
    settings docs - `'HTTP timeout read/write/connection/retry (in seconds)'`).
    A previous plan draft had ``* 1000`` (treating it as milliseconds);
    that was wrong and would have configured an 8.3-hour effective timeout.
    """
    con = duckdb.connect(database=database)
    try:
        con.execute("LOAD httpfs")
    except Exception:
        con.execute("INSTALL httpfs")
        con.execute("LOAD httpfs")
    con.execute(f"SET http_timeout = {HTTP_TIMEOUT_SECONDS}")
    return con

def _s3fs_config_kwargs() -> dict:
    """Build config_kwargs for s3fs / fsspec("s3", ...) - passed directly
    to botocore.client.Config(...) by s3fs.
    """
    return {
        "connect_timeout": HTTP_TIMEOUT_SECONDS,
        "read_timeout": HTTP_TIMEOUT_SECONDS,
        "retries": {"max_attempts": 1},
    }

def open_fsspec_file(url: str, mode: str = "rb"):
    """Open a remote file with the timeout-configured fsspec client.
    """
    return fsspec.open(
        url,
        mode=mode,
        anon=True,
        config_kwargs=_s3fs_config_kwargs(),
    )

def _detect_output_file_kind(file_url: str) -> Optional[str]:
    lower = str(file_url or "").lower()
    if lower.endswith(".parquet"):
        return "parquet"
    if lower.endswith(".nc") or lower.endswith(".nc4"):
        return "netcdf"
    return None

def _is_duckdb_programmer_error(exc: BaseException) -> bool:
    """True if exc is a DuckDB SQL programmer-error class that must NOT be
    caught when the SQL was hardcoded by us.

    Wrong-column / malformed-SQL / missing-table errors in OUR hardcoded
    SQL should crash visibly so they're discoverable in observability logs,
    not normalized to a polite envelope. CRITICAL: this guard applies ONLY
    to hardcoded-SQL call sites (e.g. _duckdb_lookup_hydrofabric_feature).

    For LLM-supplied-SQL call sites (query_output_file's `query` arg), use
    ``_classify_llm_sql_error`` instead - the LLM CAN recover from these
    if given a structured envelope with the column list as fix_hint, the
    same pattern InputValidationEnvelopeMiddleware uses for kwarg errors.
    """
    return isinstance(
        exc,
        (
            duckdb.BinderException,
            duckdb.ParserException,
            duckdb.CatalogException,
        ),
    )

def validate_output_sql(query: str) -> str:
    """
    Validate a DuckDB query for output-file tools.

    Rules:
      - must be a single statement
      - must start with SELECT or WITH ... SELECT
      - must be read-only
      - must read FROM output
    """
    if not isinstance(query, str) or not query.strip():
        raise ValueError("query is required")

    q = query.strip()

    # Allow one trailing semicolon, but reject multi-statement SQL
    q_no_trailing = q[:-1].strip() if q.endswith(";") else q
    if ";" in q_no_trailing:
        raise ValueError("query must be a single SQL statement")

    if not _OUTPUT_SQL_START_RE.match(q):
        raise ValueError("query must start with SELECT or WITH")

    if _OUTPUT_SQL_FORBIDDEN_RE.search(q):
        raise ValueError("query must be read-only")

    if not _OUTPUT_SQL_FROM_OUTPUT_RE.search(q):
        raise ValueError("query must read FROM output")

    return q

def _extract_duckdb_candidates(exc_message: str) -> list[str]:
    """Pull the candidate column names out of a DuckDB BinderException message.

    Returns ``[]`` if no candidate-bindings clause is found (e.g., the error
    is ParserException, or the message format changed in a future DuckDB
    version). Callers should handle the empty case as "we don't know the
    columns; fix_hint can't list them."
    """
    match = _DUCKDB_CANDIDATES_RE.search(exc_message)
    if not match:
        return []
    raw = match.group(1)
    # raw looks like: '"output.feature_id", "output.velocity"'
    parts = re.findall(r'"([^"]+)"', raw)
    columns: list[str] = []
    for part in parts:
        # Strip leading table-qualifier: "output.velocity" -> "velocity"
        # Keep the original if there's no dot.
        bare = part.rsplit(".", 1)[-1] if "." in part else part
        if bare and bare not in columns:
            columns.append(bare)
    return columns

def _classify_llm_sql_error(
    exc: BaseException, file_url: str, query: str
) -> tuple[str, str, str, list[str]]:
    """Return (error_code, sanitized_message, fix_hint, available_columns)
    for a DuckDB programmer-error class fired against LLM-supplied SQL.

    The LLM-facing envelope from this classifier is the SQL analogue of
    InputValidationEnvelopeMiddleware's `invalid_args` envelope: it gives
    the LLM a structured way to recover in one retry instead of stalling
    in a thinking loop (as observed with qwen on 2026-05-10).

    Callers must use this AT LLM-supplied-SQL call sites only (currently
    ``query_output_file`` in rest.py). For hardcoded-SQL paths, use the
    existing ``_is_duckdb_programmer_error`` re-raise guard instead.
    """
    exc_msg = str(exc)
    if isinstance(exc, duckdb.BinderException):
        columns = _extract_duckdb_candidates(exc_msg)
        if columns:
            column_list = ", ".join(columns)
            fix_hint = (
                f"The query references a column that does not exist in the "
                f"output file. The actual columns are: {column_list}. "
                f"Rewrite the query using one of these column names and "
                f"retry once."
            )
        else:
            fix_hint = (
                "The query references a column that does not exist in the "
                "output file. Rewrite the query using only the columns "
                "documented for this output kind, or check what's available "
                "by running a probe query like SELECT * FROM output LIMIT 1, "
                "and retry once."
            )
        return (
            "invalid_query",
            "Query references a column that does not exist in the output file.",
            fix_hint,
            columns,
        )
    if isinstance(exc, duckdb.ParserException):
        return (
            "invalid_query",
            "Query is not valid SQL syntax.",
            (
                "The query is not valid DuckDB SQL. Common causes: missing "
                "comma, unbalanced parenthesis, wrong keyword order. Rewrite "
                "as a single SELECT statement against the `output` table and "
                "retry once."
            ),
            [],
        )
    if isinstance(exc, duckdb.CatalogException):
        return (
            "invalid_query",
            "Query references a missing table.",
            (
                "The query references a table that does not exist. The only "
                "queryable table in this context is `output`. Rewrite the "
                "FROM clause to `FROM output` and retry once."
            ),
            [],
        )
    # Other duckdb.Error subclasses or non-duckdb classes: fall back to
    # the generic IO classifier so callers always get a typed result.
    code, msg, fix_hint = _classify_io_error(exc)
    return code, msg, fix_hint, []

def _normalize_output_file_url(s3_url: str) -> str:
    file_url = str(s3_url or "").strip()
    if file_url.startswith("s3://ciroh-community-ngen-datastream"):
        file_url = file_url.replace(
            "s3://ciroh-community-ngen-datastream",
            "https://ciroh-community-ngen-datastream.s3.us-east-1.amazonaws.com",
        )
    return file_url

def _validate_nrds_output_file_url(bucket: str, file_url: str, allowed_exts: tuple[str, ...]) -> Optional[str]:
    url = str(file_url or "").strip()
    if not url:
        return "Missing required query param: s3_url"

    lower = url.lower()

    if not lower.endswith(allowed_exts):
        return f"s3_url must point to one file ending in {', '.join(allowed_exts)}"

    allowed_prefixes = (
        f"s3://{bucket.lower()}/",
        f"https://{bucket.lower()}.s3.us-east-1.amazonaws.com/",
    )
    if not any(lower.startswith(prefix) for prefix in allowed_prefixes):
        return f"s3_url must point to bucket {bucket}"

    if "/outputs/" not in lower:
        return "s3_url must point to an NRDS outputs file under /outputs/"

    return None

def ensure_full_s3_url(path: str) -> str:
    p = str(path or "").strip()
    if p.startswith(("s3://", "https://")):
        return p
    return f"s3://{p.lstrip('/')}"

def _get_troute_df(s3_nc_url: str) -> pd.DataFrame:
    """Load the t-route crosswalk DataFrame.

    Uses ``open_fsspec_file`` so the timeout-configured fsspec client
    reaches the underlying h5netcdf transport. ``xarray.open_dataset``
    cannot be called directly on a URL with a custom fsspec config - the
    OpenFile context manager handles that.
    """

    with open_fsspec_file(s3_nc_url) as f:
        nc_xarray = xr.open_dataset(f, engine="h5netcdf")
        nc_df = nc_xarray.to_dataframe()
        nc_df = nc_df.reset_index()

    return nc_df

def _duckdb_query_parquet(file_url: str, query: str) -> pd.DataFrame:
    """Execute an arbitrary DuckDB query against a parquet file exposed as temp view `output`."""
    safe_file_url = file_url.replace("'", "''")

    con = duckdb_connect_with_httpfs()
    try:
        con.execute(f"CREATE OR REPLACE TEMP VIEW output AS SELECT * FROM read_parquet('{safe_file_url}')")
        return con.sql(query).df()
    finally:
        try:
            con.close()
        except Exception:
            pass

def _duckdb_query_netcdf(df: pd.DataFrame , query: str) -> pd.DataFrame:
    """Execute an arbitrary DuckDB query against a netcdf file exposed as temp view `output`."""
    
    con = duckdb.connect(database=":memory:")
    con.register('tmp_table_nc', df)
    try:
        con.execute(f"CREATE OR REPLACE TEMP VIEW output AS SELECT * FROM tmp_table_nc")
        return con.sql(query).df()
    finally:
        try:
            con.close()
        except Exception:
            pass

def get_output_file(
    configuration: str,
    date: str, 
    forecast: str, 
    cycle: str, 
    vpu: str, 
    file_name:str=None, 
    index:str=None, 
    ensemble:str=None
) -> Dict:
    if (file_name is None) == (index is None):
        return error_payload(
            "bad_request",
            "Provide exactly one of file_name or index.",
        )

    if index is not None:
        try:
            _idx_check = int(index)
        except (TypeError, ValueError):
            return error_payload(
                "bad_request",
                "index must be an integer",
            )
        if _idx_check < 0:
            return error_payload(
                "bad_request",
                f"index out of range: {_idx_check}",
            )

    date = normalize_date_folder(date)
    s3_dir = f"s3://{BUCKET}/{OUTPUTS_DIR}/{configuration}/{PREFIX_HYDROFABRIC}/{date}/{forecast}/{cycle}"
    if forecast == "medium_range":
        ens = ensemble or "1"
        s3_dir += f"/{ens}/{vpu}/{NGEN_RUN_PREFIX}"
    else:
        s3_dir += f"/{vpu}/{NGEN_RUN_PREFIX}"

    try:
        fs = s3_filesystem()
        files = fs.ls(s3_dir, detail=False)

        files = [f for f in files if f.lower().endswith(".parquet") or f.lower().endswith(".nc")]
        files = sorted(files)

        items = [{"name": f.split("/")[-1], "path": ensure_full_s3_url(f)} for f in files]

        if file_name is not None:
            sel = next((it for it in items if it["name"] == file_name), None)
            if not sel:
                return error_payload(
                    "not_found",
                    f"file_name not found: {file_name}",
                    dir=s3_dir,
                    count=len(items),
                )
        else:
            try:
                idx = int(index)
            except Exception:
                return error_payload(
                    "bad_request",
                    "index must be an integer",
                    dir=s3_dir,
                    count=len(items),
                )

            if idx < 0 or idx >= len(items):
                return error_payload(
                    "bad_request",
                    f"index out of range: {idx}",
                    dir=s3_dir,
                    count=len(items),
                )
            sel = items[idx]

        return success_payload(
            dir=s3_dir,
            count=len(items),
            selected=sel,
        )

    except FileNotFoundError:
        return success_payload(
            dir=s3_dir,
            count=0,
            selected=None,
        )
    except Exception as e:
        return error_payload("Error", str(e))
    

def query_output_file(s3_url, query) -> Dict:
    """Run a read-only DuckDB query against one NRDS output file in S3 (parquet or netcdf)."""
    raw_url = str(s3_url or "").strip()
    kind = _detect_output_file_kind(raw_url)

    if kind == "parquet":
        err = _validate_nrds_output_file_url(BUCKET, raw_url, (".parquet",))
    elif kind == "netcdf":
        err = _validate_nrds_output_file_url(BUCKET, raw_url, (".nc", ".nc4"))
    else:
        err = "s3_url must point to one .parquet, .nc, or .nc4 NRDS output file"

    if err:
        return error_payload(
            "validation_error",
            err,
            file=raw_url,
            query=query,
        )

    file_url = _normalize_output_file_url(raw_url)
    try:
        query = validate_output_sql(query)
    except ValueError as e:
        return error_payload(
            "validation_error",
            str(e),
            file=file_url,
            query=query,
        )

    try:
        if kind == "parquet":
            df = _duckdb_query_parquet(file_url, query)
        else:
            initial_df = _get_troute_df(file_url)

            df = _duckdb_query_netcdf(initial_df, query)

        if "time" in df.columns:
            df["time"] = pd.to_datetime(df["time"], errors="coerce").dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        return success_payload(
            file=file_url,
            file_type=kind,
            query=query,
            columns=list(df.columns),
            rows=int(len(df)),
            data=df.to_dict(orient="records"),
        )

    except (duckdb.BinderException, duckdb.ParserException, duckdb.CatalogException) as e:
        code, msg, fix_hint, available_columns = _classify_llm_sql_error(
            e, file_url, query
        )
        return error_payload(
            code,
            msg,
            fix_hint=fix_hint,
            file=file_url,
            file_type=kind,
            query=query,
            available_columns=available_columns,
        )
    except (OSError, ClientError, duckdb.Error) as e:
        if _is_duckdb_programmer_error(e):
            raise
        code, msg, fix_hint = _classify_io_error(e)
        # not_found preserves the empty-result shape that callers expect
        if code == "not_found":
            return error_payload(
                code,
                msg,
                fix_hint=fix_hint,
                file=file_url,
                file_type=kind,
                query=query,
                columns=[],
                rows=0,
                data=[],
            )
        return error_payload(
            code,
            msg,
            fix_hint=fix_hint,
            file=file_url,
            file_type=kind,
            query=query,
        )
