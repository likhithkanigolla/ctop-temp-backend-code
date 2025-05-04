import json
import random
import os
from datetime import datetime, timedelta
import csv

# Load node configuration
def load_config():
    with open(os.path.join(os.path.dirname(__file__), "nodes.json"), "r") as f:
        return json.load(f)

# Create a directory for data if it doesn't exist
def ensure_data_directory():
    data_dir = os.path.join(os.path.dirname(__file__), "data")
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    return data_dir

# Find node details by ID
def find_node(nodes_config, node_id):
    for domain in nodes_config["domains"]:
        for sensor_type in domain["sensor_types"]:
            for node in sensor_type["nodes"]:
                if node["node_id"] == node_id:
                    return {
                        "node": node,
                        "sensor_type": sensor_type,
                        "domain": domain
                    }
    return None

# Get parameters for a node
def get_node_parameters(nodes_config, node_id):
    node_info = find_node(nodes_config, node_id)
    if not node_info:
        return None
    
    parameters = []
    sensor_type = node_info["sensor_type"]
    domain = node_info["domain"]
    
    for param_name in sensor_type["parameters"]:
        # Find the parameter details in the domain parameters
        for param in domain["parameters"]:
            if param["parameter_name"] == param_name:
                parameters.append(param)
                break
    
    return parameters

# Generate random value for a parameter
def generate_random_value(param, timestamp):
    # Extract numeric part from resolution
    resolution_str = param["resolution"]
    decimal_places = 1  # default
    if "." in resolution_str:
        parts = resolution_str.split(".")
        if len(parts) > 1 and len(parts[1]) > 0:
            num_str = ""
            for char in parts[1]:
                if char.isdigit():
                    num_str += char
                else:
                    break
            if num_str:
                decimal_places = len(num_str)
    
    # Extract numeric part from accuracy for range
    accuracy_str = param["accuracy"]
    range_val = 1.0  # default
    for part in accuracy_str.split():
        if part.startswith("±"):
            num_str = ""
            for char in part[1:]:
                if char.isdigit() or char == '.':
                    num_str += char
                else:
                    break
            if num_str:
                range_val = float(num_str)
            break
    
    # Generate a random value based on typical ranges for the parameter
    base_value = 0
    if "Temperature" in param["parameter_name"]:
        # Add some daily variation
        hour = timestamp.hour
        base_value = 20 + 7 * (1 - abs(hour - 12) / 12)  # Higher during day, lower at night
        # Add some seasonal variation if needed
        day_of_year = timestamp.timetuple().tm_yday
        seasonal_factor = 0.5 * (1 + (day_of_year % 365) / 365 * 2 - 1)  # Simplified seasonal factor
        base_value += seasonal_factor * 5
    elif "Humidity" in param["parameter_name"]:
        hour = timestamp.hour
        base_value = 60 - 20 * (1 - abs(hour - 12) / 12)  # Lower during day, higher at night
    elif "PM2.5" in param["parameter_name"]:
        hour = timestamp.hour
        # Higher during morning and evening rush hours
        rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
        base_value = 15 + rush_hour_factor * 30
    elif "CO2" in param["parameter_name"]:
        hour = timestamp.hour
        # Higher during daytime when activity is high
        activity_factor = max(0, 1 - abs(hour - 14) / 10)
        base_value = 400 + activity_factor * 800
    elif "O3" in param["parameter_name"]:
        hour = timestamp.hour
        # Higher during sunny afternoon
        sun_factor = max(0, 1 - abs(hour - 14) / 8)
        base_value = 0.02 + sun_factor * 0.05
    elif "NO2" in param["parameter_name"]:
        hour = timestamp.hour
        # Higher during morning and evening rush hours
        rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
        base_value = 0.02 + rush_hour_factor * 0.05
    elif "pH" in param["parameter_name"]:
        base_value = 7.0 + random.uniform(-0.5, 0.5)
    elif "Turbidity" in param["parameter_name"]:
        # Check if it's a rainy day (random)
        is_rainy = random.random() < 0.3
        base_value = 2.0 + (5.0 if is_rainy else 0)
    elif "Dissolved Oxygen" in param["parameter_name"]:
        # Temperature affects dissolved oxygen
        temperature = 20 + 7 * (1 - abs(timestamp.hour - 12) / 12)
        # Inverse relationship with temperature
        base_value = 14 - temperature * 0.3
        if base_value < 4:
            base_value = 4
    else:
        base_value = random.uniform(0, 100)
    
    # Add some random noise within the accuracy range
    value = round(base_value + random.uniform(-range_val, range_val), decimal_places)
    
    # Ensure values are within reasonable physical limits
    if "Temperature" in param["parameter_name"] and (value < -20 or value > 50):
        value = max(-20, min(50, value))
    elif "Humidity" in param["parameter_name"] and (value < 0 or value > 100):
        value = max(0, min(100, value))
    elif "pH" in param["parameter_name"] and (value < 0 or value > 14):
        value = max(0, min(14, value))
    
    return value

# Generate historical data for a week for a node
def generate_weekly_data(nodes_config, node_id):
    parameters = get_node_parameters(nodes_config, node_id)
    if not parameters:
        return None
    
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    current_time = start_time
    
    data = []
    
    # Generate data points at 15-minute intervals
    while current_time <= end_time:
        data_point = {
            "timestamp": current_time.strftime("%Y-%m-%d %H:%M:%S"),
            "values": {}
        }
        
        for param in parameters:
            value = generate_random_value(param, current_time)
            data_point["values"][param["parameter_name"]] = value
        
        data.append(data_point)
        current_time += timedelta(minutes=15)
    
    return data

# Save data to CSV file
def save_to_csv(data, node_id, data_dir):
    if not data:
        return
    
    file_path = os.path.join(data_dir, f"{node_id}_historical_data.csv")
    
    with open(file_path, 'w', newline='') as csvfile:
        # Get all parameter names from the first data point
        param_names = list(data[0]["values"].keys())
        fieldnames = ["timestamp"] + param_names
        
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        
        for data_point in data:
            row = {"timestamp": data_point["timestamp"]}
            row.update(data_point["values"])
            writer.writerow(row)
    
    print(f"Generated historical data for node {node_id} saved to {file_path}")

# Main function to generate data for all nodes
def generate_all_data():
    nodes_config = load_config()
    data_dir = ensure_data_directory()
    
    # Collect all node IDs
    node_ids = []
    for domain in nodes_config["domains"]:
        for sensor_type in domain["sensor_types"]:
            for node in sensor_type["nodes"]:
                node_ids.append(node["node_id"])
    
    # Generate data for each node
    for node_id in node_ids:
        data = generate_weekly_data(nodes_config, node_id)
        if data:
            save_to_csv(data, node_id, data_dir)

if __name__ == "__main__":
    generate_all_data()
    print("Data generation complete.")
