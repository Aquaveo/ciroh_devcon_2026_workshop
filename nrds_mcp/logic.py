"""
file logic.py
Description: Implements the core logic for listing and querying NRDS output files on S3, as well as looking up hydrofabric features. 
This is the main "M" in MCP, and is called
"""

import os
import logging

from typing import Dict

from .utils_rest import (
    normalize_date_folder,
    _success_payload,
    s3_filesystem,
    _error_payload,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET = os.getenv("BUCKET", "ciroh-community-ngen-datastream")
OUTPUTS_DIR = "outputs"
PREFIX_HYDROFABRIC = "v2.2_hydrofabric"
NGEN_RUN_PREFIX = "ngen-run/outputs/troute"


def list_available_output_files(
    model: str, 
    date: str, 
    forecast: str, 
    cycle: str, 
    vpu: str, 
    ensemble: str= None
) -> Dict:
    """
    Get a list of output files for a given configuration, date, forecast, cycle, ensemble, vpu, index.
    """    

    logger.info(f"Getting output files for model={model}, date={date}, forecast={forecast}, cycle={cycle}, vpu={vpu}, ensemble={ensemble}")
    date = normalize_date_folder(date) 
    s3_dir = f"s3://{BUCKET}/{OUTPUTS_DIR}/{model}/{PREFIX_HYDROFABRIC}/{date}/{forecast}/{cycle}"
    
    if forecast == "medium_range":
        ens = ensemble or "1"
        s3_dir += f"/{ens}/{vpu}/{NGEN_RUN_PREFIX}"
    else:
        s3_dir += f"/{vpu}/{NGEN_RUN_PREFIX}"

    try:
        ## The following is what needs to be done by the user
        fs = s3_filesystem()
        files = fs.ls(s3_dir, detail=False)
        files = [f for f in files if f.lower().endswith(".parquet") or f.lower().endswith(".nc")]
        files = sorted(files)
        items = [{"name": f.split("/")[-1], "path": f} for f in files]

        # logger.info(f"Found {len(items)} files in S3 directory: {s3_dir}")
        return _success_payload(
            path=s3_dir,
            count=len(items),
            files= items,
        )

    except Exception as e:
        logger.exception(f"Error accessing S3 directory: {s3_dir}")
        return _error_payload(
            "Error accessing S3 directory",
            str(e)
        )