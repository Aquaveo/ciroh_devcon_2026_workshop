"""MCP tool definitions for the DevCon workshop.

Each tool below has the same shape:
  1. @mcp.tool decorator names the tool and writes its description
  2. function signature uses Annotated[...] + Field(...) for LLM-visible schema
  3. body calls into logic.py and returns the result

You only fill in the body for CHALLENGE 2. Everything above the body is a
contract between the LLM and this server — the LLM uses the description +
Field hints to decide whether to call this tool and what to pass.
"""

import logging

from typing_extensions import Annotated
from typing import Optional, Dict, Any
from pydantic import Field

from .engine import mcp
from .logic import (
    list_available_output_files,
    query_output_file_from_output_selector,
)
from .validations import CONFIGURATIONS, FORECASTS, DATE_PATTERN, VPUS

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


@mcp.tool(
    name="list_available_output_files",
    description=(
        "List NRDS parquet/netcdf output files for one "
        "configuration/date/forecast/cycle/vpu combination."
    ),
)
def list_available_output_files_tool(
    configuration: Annotated[CONFIGURATIONS, Field(description="Configuration id")],
    date: Annotated[str, Field(description="YYYY-MM-DD or YYYY/MM/DD", pattern=DATE_PATTERN)],
    forecast: Annotated[FORECASTS, Field(description="Forecast id")],
    cycle: Annotated[str, Field(description="Cycle 00-23", pattern=r"^(?:[01]\d|2[0-3])$")] = "00",
    vpu: Annotated[VPUS, Field(description="VPU identifier")] = None,
    ensemble: Annotated[Optional[str], Field(description="Only for medium_range", pattern=r"^\d+$")] = None,
) -> Dict[str, Any]:
    logger.info(
        "Tool list_available_output_files called: configuration=%s date=%s forecast=%s cycle=%s vpu=%s ensemble=%s",
        configuration, date, forecast, cycle, vpu, ensemble,
    )
    # === CHALLENGE 2 (part A) ===
    # One line. Call list_available_output_files(...) with the arguments you
    # received and return the result. The function lives in logic.py.
    # Answer is in README.md under "Answers > 2".
    return {"ok": False, "error": {"code": "not_implemented", "message": "Challenge 2A"}}
    # === END CHALLENGE 2 (part A) ===


@mcp.tool(
    name="query_output_file_from_output_selector",
    description=(
        "Resolve one NRDS output file by configuration/date/forecast/cycle/vpu "
        "and run a read-only DuckDB SQL query against it in one step. "
        "Supports parquet (.parquet) and netcdf (.nc, .nc4). "
        "The query must be a single SELECT (or WITH ... SELECT) reading FROM output."
    ),
)
def query_output_file_from_output_selector_tool(
    configuration: Annotated[CONFIGURATIONS, Field(description="Configuration id")],
    date: Annotated[str, Field(description="YYYY-MM-DD or YYYY/MM/DD", pattern=DATE_PATTERN)],
    forecast: Annotated[FORECASTS, Field(description="Forecast id")],
    cycle: Annotated[str, Field(description="Cycle 00-23", pattern=r"^(?:[01]\d|2[0-3])$")] = "00",
    vpu: Annotated[VPUS, Field(description="VPU identifier")] = None,
    query: Annotated[
        str,
        Field(
            description="DuckDB SQL: single read-only SELECT FROM output.",
            pattern=r"(?is)^\s*(?:WITH\b.*?\bSELECT\b|SELECT\b).*$",
        ),
    ] = "SELECT * FROM output LIMIT 10",
    ensemble: Annotated[Optional[str], Field(description="Only for medium_range", pattern=r"^\d+$")] = None,
    file_name: Annotated[Optional[str], Field(description="Exact filename; overrides index when set")] = None,
    index: Annotated[Optional[int], Field(description="0-based index into sorted files", ge=0)] = 0,
) -> Dict[str, Any]:
    logger.info(
        "Tool query_output_file_from_output_selector called: configuration=%s date=%s forecast=%s cycle=%s vpu=%s query=%r",
        configuration, date, forecast, cycle, vpu, query,
    )
    # === CHALLENGE 2 (part B) ===
    # One line. Call query_output_file_from_output_selector(...) with the
    # arguments you received and return the result. The function lives in logic.py.
    # Answer is in README.md under "Answers > 2".
    return {"ok": False, "error": {"code": "not_implemented", "message": "Challenge 2B"}}
    # === END CHALLENGE 2 (part B) ===
