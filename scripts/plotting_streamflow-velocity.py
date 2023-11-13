import requests
import matplotlib.pyplot as plt

# Replace 'YOUR_API_KEY' with your actual API key
api_key = 'YOUR_API_KEY'

# API URL with the featureID and other parameters as query parameters
feature_id = '12068774'
start_date = '2023-04-04'
end_date = '2023-04-10'
reference_time = '2023-03-25T00:00:00'
ensemble = 0
api_url = f"https://long-range-forecast-9f6idmxh.uc.gateway.dev/forecast_records?feature_id={feature_id}&start_date={start_date}&end_date={end_date}&reference_time={reference_time}&ensemble={ensemble}"

# Make an API request with the API key in the headers
headers = {
    "x-api-key": api_key
}

try:
    # Make the API request
    response = requests.get(api_url, headers=headers)

    # Check if the request was successful (status code 200)
    if response.status_code == 200:
        data = response.json()

        # Extract data for plotting
        time = [item['time'] for item in data]
        streamflow = [item['streamflow'] for item in data]
        velocity = [item['velocity'] for item in data]

        # Create the graph with two y-axes
        fig, ax1 = plt.subplots(figsize=(12, 6))

        # Plot streamflow on the left y-axis (ax1)
        ax1.plot(time, streamflow, color='tab:blue', label='Streamflow')
        ax1.set_xlabel('Time')
        ax1.set_ylabel('Streamflow (cfs)', color='tab:blue')
        ax1.tick_params(axis='y', labelcolor='tab:blue')

        # Create a second y-axis on the right (ax2)
        ax2 = ax1.twinx()

        # Plot velocity on the right y-axis (ax2)
        ax2.plot(time, velocity, color='tab:red', label='Velocity')
        ax2.set_ylabel('Velocity (ft/s)', color='tab:red')
        ax2.tick_params(axis='y', labelcolor='tab:red')

        # Add legends
        lines1, labels1 = ax1.get_legend_handles_labels()
        lines2, labels2 = ax2.get_legend_handles_labels()
        ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper right')

        # Set the title
        plt.title("Feature ID " + feature_id + ", forecasted on " + reference_time)

        # Show every other date on the x-axis
        x_ticks = time[::2]  # Show every other date
        x_labels = [label for i, label in enumerate(time) if i % 2 == 0]  # Labels for every other date
        ax1.set_xticks(x_ticks)
        ax1.set_xticklabels(x_labels, rotation=40)

        # Show the graph
        plt.grid(True)
        plt.show()

    else:
        print("API request failed with status code:", response.status_code)

except Exception as e:
    print("An error occurred:", str(e))
