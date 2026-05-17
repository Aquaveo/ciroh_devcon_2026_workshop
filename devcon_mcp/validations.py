from typing import Literal

## This is for the prompts templates
CONFIGURATION_HINT = "cfe_nom / lstm / routing_only"
FORECAST_HINT = "short_range / medium_range / analysis_assim_extend"
DATE_HINT = "yyyy-mm-dd"
CYCLE_HINT = "00-23, e.g., 00"
VPU_HINT = "06, VPU_06, or 3W"


## This is for the tools

FORECASTS = Literal["short_range", "medium_range", "analysis_assim_extend"]
CONFIGURATIONS = Literal["cfe_nom", "lstm", "routing_only"]
DATE_PATTERN = r"^(?:\d{4}-\d{2}-\d{2}|\d{4}/\d{2}/\d{2})$"
VPUS = Literal[
    "VPU_18",
    "VPU_16",
    "VPU_15",
    "VPU_14",
    "VPU_13",
    "VPU_12",
    "VPU_11",
    "VPU_10U",
    "VPU_10L",
    "VPU_09",
    "VPU_08",
    "VPU_07",
    "VPU_06",
    "VPU_05",
    "VPU_04",
    "VPU_03W",
    "VPU_03S",
    "VPU_03N",
    "VPU_02",
    "VPU_01",
]