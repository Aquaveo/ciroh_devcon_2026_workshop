"""
file logic.py
Description: Implements the core logic for listing and querying NRDS output files on S3, as well as looking up hydrofabric features. 
This is the main "M" in MCP, and is called
"""

import os
import logging

from typing import Dict, Any, Optional

from .utils_rest import (
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
    configuration,
    date,
    forecast,
    cycle,
    vpu,
    query,
    ensemble: Optional[str] = None,
    file_name: Optional[str] = None,
    index: Optional[int] = 0,
) -> Dict:
    """Resolve an output file by selector and run a raw query against the selected parquet or netcdf file."""

    logger.info(
        "Received request to query output file from selector with "
        "configuration=%s date=%s forecast=%s cycle=%s vpu=%s ensemble=%s file_name=%s index=%s query=%s",
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

    resolved = get_output_file(
        configuration=configuration,
        date=date,
        forecast=forecast,
        cycle=cycle,
        vpu=vpu,
        file_name=file_name,
        index=None if file_name is not None else (0 if index is None else index),
        ensemble=ensemble,
    )

    if not isinstance(resolved, dict):
        return error_payload(
            "execution_error",
            "Unexpected response while resolving output file.",
        )

    if resolved.get("ok") is False:
        return resolved

    selected = resolved.get("selected")
    if not selected:
        return error_payload(
            "not_found",
            "No output file matched the selector.",
            dir=resolved.get("dir"),
            count=resolved.get("count", 0),
            selected=None,
        )

    selected_path = str((selected or {}).get("path") or "").strip()
    if not selected_path:
        return error_payload(
            "not_found",
            "Resolved output file does not include a path.",
            dir=resolved.get("dir"),
            count=resolved.get("count", 0),
            selected=selected,
        )

    query_result = query_output_file(
        s3_url=selected_path,
        query=query,
    )

    if isinstance(query_result, dict):
        query_result.setdefault("dir", resolved.get("dir"))
        query_result.setdefault("count", resolved.get("count"))
        query_result.setdefault("selected", selected)

    return query_result