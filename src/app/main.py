# Import libraries required for data processing
import csv
from datetime import datetime
from dateutil import parser
from io import StringIO
import requests

# Import libraries associated with FastAPI and BIGQUERY
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse, StreamingResponse
from fastapi.openapi.utils import get_openapi
from google.cloud import bigquery
from typing import Union

# Strings corresponding to BIGQUERY table names for different forecast options
FORECAST_OPTS = dict(
    long_range = 'bigquery-public-data.national_water_model.long_range_channel_rt',
    medium_range = 'bigquery-public-data.national_water_model.medium_range_channel_rt',
    short_range = 'bigquery-public-data.national_water_model.short_range_channel_rt',
)

# Create an app instance of the class FastAPI
app = FastAPI()

# Customize the documentation page as per the OpenAPI framework
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="National Water Model API Documentation",
        version="1.1.0",
        summary="This is the OpenAPI schema for the National Water Model API.",
        description = (
            "This API provides access to data produced by the National Water Model.\n"
            "It includes endpoints for retrieving retrospective and forecast data.\n "
            "Users can filter data by location, time, and other parameters.\n"
            "Please refer to the individual endpoint documentation for more details on how to use each function."
        ),
        routes=app.routes,
    )
    openapi_schema["info"]["x-logo"] = {
        "url": "https://ciroh.ua.edu/wp-content/uploads/2022/08/CIROHLogo_200x200.png"
    }
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Add the custom documentation in the generated API application
app.openapi = custom_openapi


# Create path operation decorator for the DOCUMENTATION API
@app.get("/")

# Define the ROOT function
def root():
    return RedirectResponse("/docs")

# Create path operation decorator for the FORECAST API
@app.get("/forecast")

# Define the FORECAST function
def forecast(
    forecast_type: str,
    reference_time: str | None = None,
    comids: str | None = None,
    hydroshare_id: str | None = None,
    ensemble: str | None = None,
    output_format: str = 'json',
):
    """Retrieve forecast data from the National Water Model based on the provided parameters.

    Args:

        forecast_type (str): The forecast run to extract data from.
            Supported values are 'long_range', 'medium_range', and 'short_range'.
        reference_time (str, optional): The reference time for the forecast.
            If None then defaults to the latest available forecast reference time
            in specified table.
            Defaults to None.
            Example: "2023-11-25 06:00:00 UTC"
        comids (str, optional): A comma-separated list of reach IDs for the forecast.
            Defaults to None.
            Example: "15039097,1239657"
        hydroshare_id (str, optional): The hydroshare id with specified comids to
            extract the forecast. If comids is not provided, this will be used
            to extract comids.
            Defaults to None.
            Example: "643dc03878704a30849536e302bdb2c0"
        ensemble (str, optional): A comma-separated list of ensembles for the forecast.
            If None then the average of all available ensembles will be taken.
            Defaults to None.
            Supported values are 0 for short_range, 0 to 5 for medium_range, and
            0 to 3 for long_range
        output_format (str, optional): The output format for the forecast dataset.
            Defaults to 'json'.
            Supported values are 'json' and 'csv'.


    Returns:

        The forecast data in the specified output format.
    """

    # Select the appropriate table based on the "type" parameter
    if forecast_type in FORECAST_OPTS.keys():
        table_name = FORECAST_OPTS[forecast_type]
    else:
        raise HTTPException(status_code=400, detail=f"Invalid forecast type. Supported values are {FORECAST_OPTS.keys()}.")

    # Default reference_time to the latest available if not specified
    if reference_time is None:
        # Query to get the latest reference_time
        latest_reference_time_query = f"""
            SELECT
                MAX(reference_time) AS latest_reference_time
            FROM
                `{table_name}`
            WHERE
                DATETIME(reference_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
                AND feature_id = 101
                AND ensemble = 0
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

# Create path operation decorator for the Analysis-Assimilation API
@app.get("/analysis-assim")

# Define the Analysis-Assimilation app function
def analysis_assim(
    start_time: str | None = None,
    end_time: str | None = None,
    comids: str | None = None,
    hydroshare_id: str | None = None,
    output_format: str = 'json',
    run_offset: int = 1,
):
    """
    Retrieve the analysis assimilation data from the National Water Model for the specified parameters.

    Args:

        start_time (str | None): The start time of the data range.
            Defaults to None. If None, defaults to "2018-09-17T00:00:00".
        end_time (str | None): The end time of the data range.
            Defaults to None. If None, defaults to the current time.
        comids (str, optional): A comma-separated list of reach IDs for the forecast.
            Defaults to None.
            Example: "15039097,1239657"
        hydroshare_id (str, optional): The hydroshare id with specified comids to
            extract the forecast. If comids is not provided, this will be used
            to extract comids.
            Defaults to None.
            Example: "643dc03878704a30849536e302bdb2c0"
        output_format (str): The format of the analysis-assimilation response data.
            Defaults to 'json'.
            Supported values are 'json' and 'csv'.
        run_offset (int): The analysis_assim result time offset.
            Defaults to 1.
            Supported values are 1, 2, and 3.

    Returns:

        The analysis_assim data in the specified output format.

    """

    # Extract comids from either the comid or hydroshare_id input
    comids = extract_comid_input(comids, hydroshare_id)

    if run_offset not in range(1,4):
        raise HTTPException(status_code=400, detail="Invalid run_offset. Supported values are 1, 2, and 3.")

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
            `bigquery-public-data.national_water_model.analysis_assim_channel_rt`
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


# Create path operation decorator for the Geometry API
@app.get("/geometry")

# Define the GEOMETRY app function
def geometry(
    comids: str | None = None,
    hydroshare_id: str | None = None,
    lat: float | None = None,
    lon: float | None = None,
    output_format: str = 'json'
):
    """Retrieve reach spatial geometry and attribute data from the National Water
      Model based on the provided parameters.

    Args:

        comids (str, optional): A comma-separated list of comids for the forecast.
            Defaults to None.
            Example: "15039097,1239657"
        hydroshare_id (str, optional): The hydroshare id with specified comids to
            extractt the forecast. If comids is not provided, this will be used
            to extract comids.
            Defaults to None.
            Example: "643dc03878704a30849536e302bdb2c0"
        lat (float, optional): A latitude value to query using a geometry point.
            Must provide lon as well if provided.
            Defaults to None.
            Example: 40.0
        lon (float, optional): A longitude value to query using a geometry point.
            Must provide lat as well if provided.
            Defaults to None.
            Example: -111.0
        output_format (str, optional): The output format of the geometry data.
            Defaults to 'json'.
            Supported values are 'json' and 'csv'.
    Returns:

        The geometry data in the specified output format.
    """
    # Validate input combinations
    if comids:
        # If comids are provided, use them
        station_ids = comids.split(',')
        hydroshare_id = None
        lat = None
        lon = None

        # Construct the BigQuery query to select specific columns with a JOIN statement
        query = f"""
            SELECT
                *
            FROM
                `bigquery-public-data.national_water_model.stream_network`
            WHERE
                station_id IN ({", ".join(map(str, station_ids))})
            ORDER BY
                station_id
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
            SELECT
                *
            FROM
                `bigquery-public-data.national_water_model.stream_network`
            WHERE
                station_id IN ({", ".join(map(str, station_ids))})
            ORDER BY
                station_id
        """

    elif lat and lon:
        # If lat and lon are provided, find the closest 'to' using Haversine formula
        query = f"""
            SELECT
                streams.*,
                ST_DISTANCE(streams.geometry, ST_GEOGPOINT({lon}, {lat})) AS distance
            FROM
                `bigquery-public-data.national_water_model.stream_network` AS streams
            ORDER BY distance
            LIMIT 1
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


# Create path operation decorator for the Flood Return-Periods API
@app.get("/return-period")

# Define the Flood Return-Periods app function
def flood_return_periods(
    comids: str | None = None,
    hydroshare_id: str | None = None,
    return_periods: str | None = None,
    output_format: str = 'json',
    order_by_comid: bool = False,
):
    """
    Retrieve the flood return-periods data for specified reach IDs in desired output format.


    Args:

        comids (str, optional): A comma-separated list of comids for the return-
            periods data.
            Defaults to None.
            Example: "15039097,1239657"
        hydroshare_id (str, optional): The hydroshare id with specified comids to
            extract the forecast. If comids is not provided, this will be used
            to extract comids.
            Defaults to None.
            Example: "643dc03878704a30849536e302bdb2c0"
        return_periods (str, optional): A comma-separated list of return-period
            fields to be included in the response.
            Defaults to None. None will extract all six return-periods namely
            2, 5, 10, 25, 50, and 100.
            Example: "10,50,100"
        output_format (str): The format of the return-period response data.
            Defaults to 'json'.
            Supported values are 'json' and 'csv'.
        order_by_comid (bool, optional): Whether to order the results by comids.
            Defaults to False. The records will be in the order of input comids
            If True, the results will be ordered by comids in ascending order.

    Returns:

        The flood return periods data in the specified output format.

    """

    # Extract comids from either the comid or hydroshare_id input
    comids = extract_comid_input(comids, hydroshare_id)

    # Customize extracted fields based on return_periods chosen
    selected_fields = "feature_id"
    tabs = "\t    "
    if return_periods == None:
      # Extract all six return periods data by default
      selected_fields = (selected_fields +
                        (f",\n{tabs}return_period_2,\n{tabs}return_period_5," +
                        f"\n{tabs}return_period_10,\n{tabs}return_period_25," +
                        f"\n{tabs}return_period_50, \n{tabs}return_period_100"))
    else:
      # Extract only the listed return periods data
      requested_return_periods = return_periods.split(",")
      for return_period in requested_return_periods:
          selected_fields = selected_fields + f",\n{tabs}return_period_{return_period}"

    # Assemble the main body of the flood return-period data query
    query = f"""
            SELECT
                {selected_fields}
            FROM
                `bigquery-public-data.national_water_model.flood_return_periods`
            WHERE
                feature_id IN ({", ".join(map(str, comids))})
        """

    if order_by_comid:
      #  Add the sorting statement if order_by_comid is True
      query += "    ORDER BY feature_id"


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


def extract_comid_input(comids: str | None, hydroshare_id: str | None):

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
        response = JSONResponse(content=response_data)

    elif output_format.lower() == 'csv':
        # Return results as a CSV response
        csv_output = StringIO()
        csv_writer = csv.DictWriter(csv_output, fieldnames=response_data[0].keys())

        # Write header
        csv_writer.writeheader()

        # Write rows
        csv_writer.writerows(response_data)

        response = StreamingResponse(
            iter([csv_output.getvalue()]),
            media_type="text/csv"
        )

        csv_output.close()
    else:
        raise HTTPException(status_code=400, detail='Unsupported output format. Supported formats are JSON and CSV.')

    return response
