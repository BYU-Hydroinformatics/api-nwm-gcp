from google.cloud import bigquery
import json

def geometry(request):
    # Set up BigQuery client
    client = bigquery.Client()

    # Set table ID
    table_id = "nwm-ciroh.NWM_Streams_Tables.Routelink_CONUS_fsspec"

    # Get the query parameters from the request URL
    coordinates = request.args.get('coordinates')

    # Check if coordinates parameter is missing
    if not coordinates:
        # Return an error message
        return 'Please provide the coordinates parameter as a list of points.'

    # Parse the list of coordinates
    try:
        polygon = json.loads(coordinates)
    except:
        # Return an error message
        return 'The coordinates parameter should be a valid JSON array.'

    # Convert the polygon to a string in the format expected by BigQuery
    polygon_string = ','.join([f'{point[1]} {point[0]}' for point in polygon])

    # Set up SQL query to retrieve data
    full_query = f"""
    SELECT *
    FROM 
        `nwm-ciroh.NWM_Streams_Tables.Routelink_CONUS_fsspec`
    JOIN
        `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS`
    ON
        `nwm-ciroh.NWM_Streams_Tables.Routelink_CONUS_fsspec`.link = `nwm-ciroh.NWM_Streams_Tables.NWMApp_CONUS`.station_id
    WHERE 
        ST_WITHIN(ST_GEOGPOINT(lon, lat), ST_GEOGFROMTEXT('POLYGON(({polygon_string}))'))
    ORDER BY 
        link ASC
    """

    # Make API request to BigQuery and retrieve data
    query_job = client.query(full_query)
    results = query_job.result()

    # Convert results to list of dictionaries
    response_json = []
    for row in results:
        response_json.append(dict(row.items()))

    # Return results as a JSON response
    return json.dumps(response_json)
