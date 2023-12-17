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

        # get the latest reference_time
        reference_time = latest_reference_time_query[-1]['latest_reference_time']

    else:
        # Convert the input reference_time string to a datetime object
        try:
            reference_time = parser.parse(reference_time)

        except ValueError as e:
            raise HTTPException(status_code=400, description=f"Error parsing reference_time: {str(e)}")

    # If hydroshare_id is provided, use it to retrieve comids
    if hydroshare_id:
        hydroshare_url = f"https://www.hydroshare.org/resource/{hydroshare_id}/data/contents/nwm_comids.json"
        try:
            hydroshare_response = requests.get(hydroshare_url)
            hydroshare_data = hydroshare_response.json()
            # Extract comids from the HydroShare data
            comids = [item.get('comid') for item in hydroshare_data]
            
        except Exception as e:
            raise HTTPException(status_code=500, description=f"Error retrieving HydroShare data: {str(e)}")
        
    elif comids:
        # If comids is provided, split by comma
        comids = list(map(int, comids.split(','))) if comids else None

    else:
        raise HTTPException(status_code=400, description="No valid comids found. Please provide valid comids or a valid HydroShare resource ID.")

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
            SELECT *
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
        raise HTTPException(status_code=400, description='Unsupported output format. Supported formats are JSON and CSV.')
    
    return response


@app.get("/geometry")
def geometry(reach_id, lat, lon):

    return


def run_query(query):
    # Set up BigQuery client
    client = bigquery.Client()

    # Make API request to BigQuery and retrieve data
    query_job = client.query(query)
    results = query_job.result()

    return results