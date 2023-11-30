import json
from datetime import datetime

from fastapi import FastAPI, HTTPException
from google.cloud import bigquery
from typing import Union


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}


@app.get("/forecast-stats")
def forecast_stats(reach_id: int, lat: float, lon: float, date: str):


    return 

@app.get("/forecast-records")
def forecast_records(feature_id: int, start_date: str, end_date: str, reference_time: str, ensemble: int):

    # Construct the BigQuery query to select specific columns
    query = f"""
        SELECT 
            time, streamflow, velocity
        FROM 
            `ciroh-water-demo.national_water_model_demo.channel_rt_long_range`
        WHERE 
            feature_id = {feature_id} 
            AND time > '{start_date}'
            AND time < '{end_date}'
            AND reference_time = '{reference_time}'
            AND ensemble = {ensemble}
        ORDER BY 
            time
    """

    # Make API request to BigQuery and retrieve data
    results = run_query(query)

    # Create a list of JSON objects with the selected columns
    response_json = []
    for row in results:
        # Convert the BigQuery Row object to a dictionary
        json_obj = dict(row.items())

        # Convert datetime objects to string
        for key, value in json_obj.items():
            if isinstance(value, datetime):
                json_obj[key] = value.strftime("%Y-%m-%dT%H:%M:%S")

        response_json.append(json_obj)

    # Return results as a JSON response
    return json.dumps(response_json)


@app.get("/daily-averages")
def daily_averages(reach_id, lat, lon):

    return


@app.get("/forecast-stats-by-area")
def forecast_stats_by_area(area, start_date, end_date):

    return


@app.get("/forecast-records-by-area")
def forecast_records_by_area(area, start_date, end_date):

    return


@app.get("/reach-id-by-area")
def reach_id_by_area(area):

    return

def run_query(query):
    # Set up BigQuery client
    client = bigquery.Client()

    # Make API request to BigQuery and retrieve data
    query_job = client.query(query)
    results = query_job.result()

    return results