"""MCP prompts for the DevCon workshop.

A prompt is a reusable template the LLM can request by name and parameters.
The body returned here becomes the user-side message the LLM will respond to.
"""

from typing_extensions import Annotated
from pydantic import Field

from .engine import mcp
from .validations import (
    CONFIGURATION_HINT,
    DATE_HINT,
    FORECAST_HINT,
    CYCLE_HINT,
    VPU_HINT,
    QUERY_HINT,
)


@mcp.prompt
def list_output_files(
    configuration: Annotated[str, Field(description=CONFIGURATION_HINT)],
    date: Annotated[str, Field(description=DATE_HINT)],
    forecast: Annotated[str, Field(description=FORECAST_HINT)],
    cycle: Annotated[str, Field(description=CYCLE_HINT)],
    vpu: Annotated[str, Field(description=VPU_HINT)],
) -> str:
    """Ask the LLM to list available output files for a selector."""
    # === CHALLENGE 3 ===
    # Two lines. Return an f-string that asks the LLM to list the output files
    # for the given configuration/date/forecast/cycle/vpu. Use the parameter
    # names as f-string placeholders.
    # Answer is in README.md under "Answers > 3".
    return "TODO: write the prompt template"
    # === END CHALLENGE 3 ===


@mcp.prompt
def query_output_file(
    configuration: Annotated[str, Field(description=CONFIGURATION_HINT)],
    date: Annotated[str, Field(description=DATE_HINT)],
    forecast: Annotated[str, Field(description=FORECAST_HINT)],
    cycle: Annotated[str, Field(description=CYCLE_HINT)],
    vpu: Annotated[str, Field(description=VPU_HINT)],
    query: Annotated[str, Field(description=QUERY_HINT)],
) -> str:
    """Ask the LLM to run a DuckDB SQL query against a selected output file."""
    # === CHALLENGE 4 ===
    # Two lines. Return an f-string that asks the LLM to run `query` against
    # the output file for the given configuration/date/forecast/cycle/vpu.
    # Use the parameter names as f-string placeholders.
    # Answer is in README.md under "Answers > 4".
    return "TODO: write the prompt template"
    # === END CHALLENGE 4 ===
