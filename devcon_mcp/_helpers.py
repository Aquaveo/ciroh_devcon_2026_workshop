"""Internal helpers for the DevCon MCP workshop.

You do NOT need to read or edit this file to complete the workshop.

This file packages S3 access, DuckDB query setup, date normalization,
and error-envelope helpers behind a small surface. The three challenge
files (logic.py, tools.py, prompts.py) import from here.
"""

from datetime import datetime
from typing import Any, Dict, Optional
import fsspec
import xarray as xr
import duckdb
import pandas as pd
import re
import logging

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

def open_fsspec_file(url: str, mode: str = "rb"):
    """Open a remote file with the timeout-configured fsspec client.
    """
    return fsspec.open(
        url,
        mode=mode,
        anon=True,
        config_kwargs=s3fs_config_kwargs(),
    )

def _detect_output_file_kind(file_url: str) -> Optional[str]:
    lower = str(file_url or "").lower()
    if lower.endswith(".parquet"):
        return "parquet"
    if lower.endswith(".nc") or lower.endswith(".nc4"):
        return "netcdf"
    return None

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
        return error_payload(
            "not_found",
            f"No NRDS output files found at {s3_dir}. Try a different date or selector.",
            dir=s3_dir,
            count=0,
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

    except Exception as e:
        return error_payload(
            "error",
            str(e),
            file=file_url,
            file_type=kind,
            query=query,
        )
