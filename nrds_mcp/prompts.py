from .engine import mcp
from typing_extensions import Annotated
from pyndatic import Field
from .validations import CONFIGURATION_HINT, DATE_HINT, FORECAST_HINT, CYCLE_HINT, VPU_HINT


@mcp.prompt
def list_output_files(
    configuration: Annotated[str, Field(description=CONFIGURATION_HINT)],
    date: Annotated[str, Field(description=DATE_HINT)],
    forecast: Annotated[
        str, Field(description=FORECAST_HINT)
    ],
    cycle: Annotated[str, Field(description=CYCLE_HINT)],
    vpu: Annotated[str, Field(description=VPU_HINT)],
) -> str:
    """List the available output files for a given NRDS configuration, date, forecast,
    cycle, and VPU.
    """
    
    return (
        f"you need to do this prompt using . . ."
    )
    ## the following is the answer fir the prompt template
    # return (
    #     f"List the available output files for the {configuration} configuration on {date}, "
    #     f"{forecast} forecast, cycle {cycle}, vpu {vpu}."
    # )