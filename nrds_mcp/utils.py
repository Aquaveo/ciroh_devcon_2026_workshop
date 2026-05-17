from datetime import datetime
from typing import Any, Dict
import fsspec


HTTP_TIMEOUT_SECONDS = 60

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


def _success_payload(**kwargs) -> Dict[str, Any]:
    return {
        "ok": True,
        "error": None,
        **kwargs,
    }

def _error_payload(
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