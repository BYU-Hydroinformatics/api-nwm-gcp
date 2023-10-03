from google.cloud import bigquery
import json
from datetime import datetime

def forecast_records(request):
    # Set up BigQuery client
    client = bigquery.Client()

    feature_id = request.args.get('feature_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    reference_time = request.args.get('reference_time')
    ensemble = request.args.get('ensemble')

    # Check if any query parameters are missing
    if not all([feature_id, start_date, end_date, reference_time, ensemble]):
        # Return an error message
        return 'Please provide all four query parameters: feature_id, start_date, end_date, reference_time, ensemble.'

    # Construct the BigQuery query to select specific columns
    query = f"""
        SELECT time, streamflow, velocity, Shape_Length, geometry
        FROM 
            `ciroh-water-demo.national_water_model_demo.channel_rt_long_range`
        JOIN
            `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS`
        ON
            `ciroh-water-demo.national_water_model_demo.channel_rt_long_range`.feature_id = `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS`.station_id
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
    query_job = client.query(query)
    results = query_job.result()

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
