"""
file logic.py
Description: Implements the core logic for listing and querying NRDS output files on S3, as well as looking up hydrofabric features. 
This is the main "M" in MCP, and is called
"""

import os
import logging

from typing import Dict, Any, Optional

from .utils import (
    normalize_date_folder,
    success_payload,
    s3_filesystem,
    error_payload,
    get_output_file,
    query_output_file,
)

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

BUCKET = os.getenv("BUCKET", "ciroh-community-ngen-datastream")
OUTPUTS_DIR = "outputs"
PREFIX_HYDROFABRIC = "v2.2_hydrofabric"
NGEN_RUN_PREFIX = "ngen-run/outputs/troute"


def list_available_output_files(
    configuration: str, 
    date: str, 
    forecast: str, 
    cycle: str, 
    vpu: str, 
    ensemble: str= None
) -> Dict:
    """
    Get a list of output files for a given configuration, date, forecast, cycle, ensemble, vpu, index.
    """    

    logger.info(f"Getting output files for configuration={configuration}, date={date}, forecast={forecast}, cycle={cycle}, vpu={vpu}, ensemble={ensemble}")
    date = normalize_date_folder(date) 
    s3_dir = f"s3://{BUCKET}/{OUTPUTS_DIR}/{configuration}/{PREFIX_HYDROFABRIC}/{date}/{forecast}/{cycle}"
    
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

        ## Challenge 1A
        ## Sort the files, and return a list of dicts with name and path
        ## save the diles on the varaible "items"
        ## if you need an answer you can go to answers on the  README 
        # this is the answer for the answer 
        # files = sorted(files)
        # items = [{"name": f.split("/")[-1], "path": f} for f in files]
        
        items=[]

        logger.info(f"Found {len(items)} files in S3 directory: {s3_dir}")
        return success_payload(
            path=s3_dir,
            count=len(items),
            files= items,
        )

    except Exception as e:
        logger.exception(f"Error accessing S3 directory: {s3_dir}")
        return error_payload(
            "Error accessing S3 directory",
            str(e)
        )
    

def query_output_file_from_output_selector(
    configuration: str,
    date: str,
    forecast: str,
    cycle: str,
    vpu: str,
    query: str,
    ensemble: Optional[str] = None,
    file_name: Optional[str] = None,
    index: Optional[int] = 0,
) -> Dict:
    """Resolve one NRDS output file by selector, then run a DuckDB query against it.

    Conceptually this is two steps:
      1. resolve a single file from the selector  -> get_output_file(...)
      2. run the SQL query against that file      -> query_output_file(...)
    """
    logger.info(
        "query_output_file_from_output_selector configuration=%s date=%s forecast=%s "
        "cycle=%s vpu=%s ensemble=%s file_name=%s index=%s",
        configuration, date, forecast, cycle, vpu, ensemble, file_name, index,
    )

    # === CHALLENGE 1B ===
    # Two lines. Resolve the file with get_output_file(...), then call
    # query_output_file(s3_url=..., query=query) on the resolved path.
    #
    # Hint: get_output_file returns {"ok": True, "selected": {"path": "..."}, ...}
    # when it succeeds. If get_output_file returned ok=False, return it directly
    # so the LLM sees the structured error envelope.
    #
    # Answer is in README.md under "Answers > 1B".
    resolved = success_payload(selected=None)
    return resolved
    # === END CHALLENGE 1B ===