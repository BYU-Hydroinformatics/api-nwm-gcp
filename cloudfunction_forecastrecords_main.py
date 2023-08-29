from google.cloud import bigquery
from flask import jsonify, abort

def query_bigquery(request):
    feature_id = request.args.get('featureID')
    if not feature_id:
        return 'Error: "featureID" query parameter is required.', 400

    # Construct the BigQuery query
    query = f"""
        SELECT feature_id, reference_time, time, streamflow
        FROM 
            `ciroh-water-demo.national_water_model_demo.channel_rt_analysis_assim`
        WHERE 
            feature_id = {feature_id} 
            AND forecast_offset = 1
            AND time > '2023-03-03'
            AND time < '2023-04-02'
        ORDER BY 
            time
    """

    # Execute the query
    client = bigquery.Client()

    try:
        # Run the query and fetch the results
        query_job = client.query(query)
        results = query_job.result()

        # Process the results
        data = []
        for row in results:
            # Convert Row object to dictionary
            row_dict = dict(row.items())
            data.append(row_dict)

        # Return the response as JSON
        return jsonify(data)

    except Exception as e:
        # Handle any exceptions
        return f"An error occurred: {str(e)}", 500
