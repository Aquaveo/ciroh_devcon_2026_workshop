from .engine import mcp
from .logic import list_available_output_files
from pyndatic import Field
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
    pass

    params: Dict[str, Any] = {
        "configuration": configuration,
        "date": date.isoformat(),
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