import csv
from datetime import datetime
from dateutil import parser
from io import StringIO
import json
import requests

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from google.cloud import bigquery
from typing import Union


# constants
FORECAST_OPTS = dict(
    long_range = 'ciroh-water-demo.national_water_model_demo.channel_rt_long_range',
    medium_range = 'ciroh-water-demo.national_water_model_demo.channel_rt_medium_range',
    short_range = 'ciroh-water-demo.national_water_model_demo.channel_rt_short_range',
)

app = FastAPI()


@app.get("/")
def home():
    return RedirectResponse("/docs")


@app.get("/forecast-records")
def forecast_records(
    forecast_type: str,
    reference_time: str | None = None,
    comids: str | None = None,
    hydroshare_id: str | None = None,
    ensemble: str | None = None,
    output_format: str = 'json',
):

    # Select the appropriate table based on the "type" parameter
    if forecast_type in FORECAST_OPTS.keys():
        table_name = FORECAST_OPTS[forecast_type]
    else:
        raise HTTPException(status_code=400, detail=f"Invalid forecast type. Supported values are {FORECAST_OPTS.keys()}.")

    # Default reference_time to the latest available if not specified
    if reference_time is None:
        # Query to get the latest reference_time
        latest_reference_time_query = f"""
            SELECT MAX(reference_time) AS latest_reference_time
            FROM `{table_name}`
        """
        latest_reference_time_result = run_query(latest_reference_time_query)

        # Iterate over the results to get the latest reference_time
        for row in latest_reference_time_result:
            reference_time = row['latest_reference_time']

    else:
        # Convert the input reference_time string to a datetime object
        try:
            reference_time = parser.parse(reference_time)

        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Error parsing reference_time: {str(e)}")

    # Extract comids from either the comid or hydroshare_id input
    comids = extract_comid_input(comids, hydroshare_id)
    
    # If ensemble is provided, split by comma
    ensembles = list(map(int, ensemble.split(','))) if ensemble else None

    if not ensembles:
        # If no ensemble specified, create a new roll with "average" in the "ensemble" column
        # Combine rolls with the same values for "feature_id", "reference_time", and "time"
        # Calculate the average for the columns "streamflow" and "velocity"
        query = f"""
            WITH average_rolls AS (
                SELECT
                    feature_id,
                    reference_time,
                    time,
                    'average' AS ensemble,
                    AVG(streamflow) AS streamflow,
                    AVG(velocity) AS velocity
                FROM 
                    `{table_name}`
                WHERE 
                    feature_id IN ({", ".join(map(str, comids))})
                    AND reference_time = '{reference_time}'
                GROUP BY
                    feature_id, reference_time, time
            )
            SELECT *
            FROM average_rolls
            ORDER BY time
        """
    else:
        # If ensemble(s) is specified, use them in the query
        query = f"""
            SELECT 
                feature_id,
                reference_time,
                time,
                ensemble,
                streamflow,
                velocity
            FROM 
                `{table_name}`
            WHERE 
                feature_id IN ({", ".join(map(str, comids))})
                AND reference_time = '{reference_time}'
                AND ensemble IN ({", ".join(map(str, ensembles))})
            ORDER BY 
                time
        """

    # Make API request to BigQuery and retrieve data
    results = run_query(query)

    # Create a list of JSON objects with the selected columns
    response_data = []
    for row in results:
        # Convert the BigQuery Row object to a dictionary
        json_obj = dict(row.items())

        # Convert datetime objects to string
        for key, value in json_obj.items():
            if isinstance(value, datetime):
                json_obj[key] = value.strftime("%Y-%m-%dT%H:%M:%S")

        response_data.append(json_obj)

    response = format_response(response_data, output_format)
    
    return response


@app.get("/analysis-assim")
def analysis_assim(
    start_time: str | None = None,
    end_time: str | None = None,
    comids: str | None = None,
    hydroshare_id: str | None = None,
    output_format: str = 'json',
    run_offset: int = 1,
):
    
    # Extract comids from either the comid or hydroshare_id input
    comids = extract_comid_input(comids, hydroshare_id)

    if run_offset not in range(1,4):
        raise HTTPException(status_code=400, detail=f"Invalid run_offset. Supported values are 1, 2, and 3.")
    
    if start_time is None:
        start_time = "2018-09-17T00:00:00"

    if end_time is None:
        end_time = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")

    query = f"""
        SELECT
            feature_id,
            time,
            streamflow,
            velocity
        FROM
            `ciroh-water-demo.national_water_model_demo.channel_rt_analysis_assim`
        WHERE 
            feature_id IN ({", ".join(map(str, comids))})
            AND forecast_offset = {run_offset}
            AND time >= '{start_time}'
            AND time <= '{end_time}'
        ORDER BY 
            time
    """

    # Make API request to BigQuery and retrieve data
    results = run_query(query)

     # Create a list of JSON objects with the selected columns
    response_data = []
    for row in results:
        # Convert the BigQuery Row object to a dictionary
        json_obj = dict(row.items())

        # Convert datetime objects to string
        for key, value in json_obj.items():
            if isinstance(value, datetime):
                json_obj[key] = value.strftime("%Y-%m-%dT%H:%M:%S")

        response_data.append(json_obj)

    response = format_response(response_data, output_format)

    return response

@app.get("/geometry")
def geometry(
    comids: str | None = None,
    hydroshare_id: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    output_format: str = 'json'
):
    # Validate input combinations
    if comids:
        # If comids are provided, use them
        station_ids = comids.split(',')
        hydroshare_id = None
        lat = None
        lon = None

        # Construct the BigQuery query to select specific columns with a JOIN statement
        query = f"""
            SELECT *
            FROM 
                `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS` AS a
            JOIN 
                `nwm-ciroh.NWM_Streams_Tables.Routelink_CONUS_fsspec` AS b
            ON 
                a.station_id = b.to
            WHERE 
                a.station_id IN ({", ".join(map(str, station_ids))})
            ORDER BY 
                a.station_id
        """

    elif hydroshare_id:
        # If hydroshare_id is provided, fetch comids from HydroShare
        hydroshare_url = f"https://www.hydroshare.org/resource/{hydroshare_id}/data/contents/nwm_comids.json"
        try:
            hydroshare_response = requests.get(hydroshare_url)
            hydroshare_data = hydroshare_response.json()
        except Exception as e:
            return f"Error retrieving HydroShare data: {str(e)}"

        station_ids = [item.get('comid') for item in hydroshare_data]

        if not station_ids:
            raise HTTPException(status_code=500, detail="No feature IDs found in HydroShare data.")

        # Construct the BigQuery query to select specific columns with a JOIN statement
        query = f"""
            SELECT *
            FROM 
                `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS` AS a
            JOIN 
                `nwm-ciroh.NWM_Streams_Tables.Routelink_CONUS_fsspec` AS b
            ON 
                a.station_id = b.to
            WHERE 
                a.station_id IN ({", ".join(map(str, station_ids))})
            ORDER BY 
                a.station_id
        """
    
    elif lat and lon:
        # If lat and lon are provided, find the closest 'to' using Haversine formula
        query = f"""
        WITH DistanceCalc AS (
            SELECT
                b.*,
                # Haversine formula to calculate distance
                ACOS(SIN({lat} * 0.0174533) * SIN(b.lat * 0.0174533) +
                    COS({lat} * 0.0174533) * COS(b.lat * 0.0174533) *
                    COS((b.lon - {lon}) * 0.0174533)) * 6371 AS distance
            FROM 
                `nwm-ciroh.NWM_Streams_Tables.Routelink_CONUS_fsspec` AS b
        ),
        ClosestTo AS (
            SELECT *
            FROM DistanceCalc
            ORDER BY distance
            LIMIT 1
        )
        SELECT *
        FROM 
            `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS` AS a
        JOIN 
            ClosestTo AS c
        ON 
            a.station_id = c.link
    """

    else:
        # If none of the input combinations match, return an error
        raise HTTPException(status_code=400, detail='Please provide either "comids", "hs_resource", or (lat and lon) query parameters.')

    # Make API request to BigQuery and retrieve data
    results = run_query(query)

    # Create a list of JSON objects with the selected columns
    response_data = []
    for row in results:
        # Convert the BigQuery Row object to a dictionary
        json_obj = dict(row.items())
        response_data.append(json_obj)

    response = format_response(response_data, output_format)

    return response


def run_query(query):
    # Set up BigQuery client
    client = bigquery.Client()
    job_config = bigquery.QueryJobConfig(use_query_cache=True)

    # Make API request to BigQuery and retrieve data
    query_job = client.query(query, job_config=job_config)
    results = query_job.result()

    return results


def extract_comid_input(comids: str | None , hydroshare_id: str | None):

    # If hydroshare_id is provided, use it to retrieve comids
    if hydroshare_id:
        hydroshare_url = f"https://www.hydroshare.org/resource/{hydroshare_id}/data/contents/nwm_comids.json"
        try:
            hydroshare_response = requests.get(hydroshare_url)
            hydroshare_data = hydroshare_response.json()
            # Extract comids from the HydroShare data
            comids = [item.get('comid') for item in hydroshare_data]
            
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Error retrieving HydroShare data: {str(e)}")
        
    elif comids:
        # If comids is provided, split by comma
        comids = list(map(int, comids.split(','))) if comids else None

    else:
        raise HTTPException(status_code=400, detail="No valid comids found. Please provide valid comids or a valid HydroShare resource ID.")
    
    return comids

def format_response(response_data, output_format):
    # Check the output format and return the corresponding response
    if output_format.lower() == 'json':
        # Return results as a JSON response
        response = json.dumps(response_data)
    
    elif output_format.lower() == 'csv':
        # Return results as a CSV response
        csv_output = StringIO()
        csv_writer = csv.DictWriter(csv_output, fieldnames=response_data[0].keys())

        # Write header
        csv_writer.writeheader()

        # Write rows
        csv_writer.writerows(response_data)

        response = csv_output.getvalue()
    else:
        raise HTTPException(status_code=400, detail='Unsupported output format. Supported formats are JSON and CSV.')
    
    return response
