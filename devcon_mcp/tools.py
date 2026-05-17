from .engine import mcp, LOGGER
from .logic import list_available_output_files, query_output_file_from_output_selector
from pydantic import Field
from typing_extensions import Annotated, Optional, Dict, Any
from .validations import CONFIGURATIONS, FORECASTS, DATE_PATTERN, VPUS

@mcp.tool(
    name="get_nrds_parquet_output_file",
    description="Get a list of output files for a given configuration, date, forecast, cycle, ensemble, vpu, index",
)
def list_available_nrds_output_files(
    configuration: Annotated[CONFIGURATIONS, Field(description="Configuration name (e.g., 'cfe_nom', 'lstm', 'routing_only')")],
    date: Annotated[
        Optional[str],
        Field(description="YYYY-MM-DD or YYYY/MM/DD", pattern=DATE_PATTERN),
    ] = None,
    forecast: Annotated[FORECASTS, Field(description="Forecast id - Available forecast per configuration")] = None,
    cycle: Annotated[str, Field(description="Cycle", pattern=r"^(?:[01]\d|2[0-3])$")] = "00",
    ensemble: Annotated[
        Optional[str],
        Field(description="Only available for medium_range forecast", pattern=r"^\d+$"),
    ] = None,
    vpu: Annotated[
        Optional[VPUS],
        Field(
            description="VPU identifier - Available VPUs per configuration and forecast",
        ),
    ] = None,
) -> str:
    """
    Get a list of output files for a given configuration, date, forecast, cycle, ensemble, vpu, index.
    Args:
        configuration (str): The configuration name.
        date (str): The date in YYYYMMDD format.
        forecast (str): The forecast hour in HH format.
        cycle (str): The cycle in HH format.
        ensemble (str): The ensemble member in MM format.
        vpu (str): The VPU number in VV format.
    Returns:
        List[str]: A list of output file paths.
    """
    params: Dict[str, Any] = {
        "configuration": configuration,
        "date": date,
        "forecast": forecast,
        "cycle": cycle,
        "vpu": vpu,
    }
    if ensemble is not None:
        params["ensemble"] = ensemble

    result = list_available_output_files(
        configuration=params["configuration"],
        date=params["date"],
        forecast=params["forecast"],
        cycle=params["cycle"],
        vpu=params["vpu"],
        ensemble=params.get("ensemble"),
    )

    return result


@mcp.tool(
    name="query_output_file_from_output_selector",
    description=(
        "Resolve one NRDS output file from configuration/date/forecast/cycle/vpu and run a read-only "
        "DuckDB SQL query against it in one step. "
        "Supports parquet (.parquet) and netcdf (.nc, .nc4). "
        "Use this when you know configuration/date/forecast/cycle/vpu instead of a direct s3_url. "
        "If file_name is provided it is used; otherwise index is used and defaults to 0 "
        "(the first sorted output file). "
        "The SQL query must be a single read-only SELECT or WITH...SELECT statement and must read FROM output."
    ),
)


def query_output_file_from_output_selector_tool(
    configuration: Annotated[CONFIGURATIONS, Field(description="configuration id - call list_available_configurations to discover valid values")] = None,
    date: Annotated[
        Optional[str],
        Field(description="YYYY-MM-DD or YYYY/MM/DD", pattern=DATE_PATTERN),
    ] = None,
    forecast: Annotated[FORECASTS, Field(description="Forecast id - call list_available_forecasts to discover valid values")] = None,
    cycle: Annotated[
        str,
        Field(
            description="Cycle (00-23)",
            pattern=r"^(?:[01]\d|2[0-3])$",
        ),
    ] = "00",
    vpu: Annotated[
        str,
        Field(
            description="VPU identifier - call list_available_vpus to discover valid values. Accepts formats like '06', 'VPU_06', or '3W'"
        ),
    ] = None,
    query: Annotated[
        str,
        Field(
            description=(
                "DuckDB SQL query against table `output`. "
                "Single read-only SELECT or WITH...SELECT statement only. Must read FROM output."
            ),
            pattern=r"(?is)^\s*(?:WITH\b.*?\bSELECT\b|SELECT\b).*$",
        ),
    ] = "SELECT * FROM output LIMIT 10",
    ensemble: Annotated[
        Optional[str],
        Field(description="Optional ensemble member for medium_range.", pattern=r"^\d+$"),
    ] = None,
    file_name: Annotated[
        Optional[str],
        Field(
            description=(
                "Exact filename to query. If provided, it is used and index is ignored."
            )
        ),
    ] = None,
    index: Annotated[
        Optional[int],
        Field(
            description=(
                "0-based index into the sorted output file list. "
                "Used only when file_name is not provided. Defaults to 0 (first file)."
            ),
            ge=0,
        ),
    ] = 0,
) -> Dict[str, Any]:

    LOGGER.info(
        "Tool query_output_file_from_output_selector called configuration=%s date=%s forecast=%s cycle=%s "
        "vpu=%s ensemble=%s file_name=%s index=%s query_preview=%s",
        configuration,
        date,
        forecast,
        cycle,
        vpu,
        ensemble,
        file_name,
        index,
        query,
    )

    params: Dict[str, Any] = {
        "configuration": configuration,
        "date": date,
        "forecast": forecast,
        "cycle": cycle,
        "vpu": vpu,
        "query": query,
    }

    if ensemble is not None:
        params["ensemble"] = ensemble

    if file_name is not None:
        params["file_name"] = file_name
    else:
        params["index"] = 0 if index is None else index

    result = query_output_file_from_output_selector(
        configuration=params["configuration"],
        date=params["date"],
        forecast=params["forecast"],
        cycle=params["cycle"],
        vpu=params["vpu"],
        query=params["query"],
        ensemble=params.get("ensemble"),
        file_name=params.get("file_name"),
        index=params.get("index"),
    )

    LOGGER.info(
        "Tool query_output_file_from_output_selector completed configuration=%s date=%s forecast=%s cycle=%s vpu=%s",
        configuration,
        date,
        params["forecast"],
        cycle,
        params["vpu"],
    )
    LOGGER.info(
        "query_output_file_from_output_selector result: %s",
        result,
    )
    return result