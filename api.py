from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
import random
import json
from datetime import datetime, timedelta
import os
import uuid

app = FastAPI(title="IoT Data API", description="API for IoT sensor data and descriptors")

# Load node configuration from nodes.json
with open(os.path.join(os.path.dirname(__file__), "nodes.json"), "r") as f:
    nodes_config = json.load(f)

# Helper function to find node details
def find_node(node_id):
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

# Helper function to get parameters for a node
def get_node_parameters(node_id):
    node_info = find_node(node_id)
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

# Helper function to generate random values for parameters
def generate_random_data(parameters):
    data = []
    for param in parameters:
        if param["data_type"] == "float":
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
                base_value = random.uniform(15, 35)
            elif "Humidity" in param["parameter_name"]:
                base_value = random.uniform(30, 90)
            elif "PM2.5" in param["parameter_name"]:
                base_value = random.uniform(5, 50)
            elif "CO2" in param["parameter_name"]:
                base_value = random.uniform(350, 1500)
            elif "O3" in param["parameter_name"]:
                base_value = random.uniform(0.01, 0.08)
            elif "NO2" in param["parameter_name"]:
                base_value = random.uniform(0.01, 0.1)
            elif "pH" in param["parameter_name"]:
                base_value = random.uniform(6.5, 8.5)
            elif "Turbidity" in param["parameter_name"]:
                base_value = random.uniform(0.5, 10)
            elif "Dissolved Oxygen" in param["parameter_name"]:
                base_value = random.uniform(4, 12)
            else:
                base_value = random.uniform(0, 100)
            
            # Add some random variation within the accuracy range
            value = round(base_value + random.uniform(-range_val, range_val), decimal_places)
            data.append(str(value))
    
    return data

# Helper function to create response in the required format
def create_response(content):
    now = datetime.utcnow()
    timestamp = now.strftime("%Y%m%dT%H%M%S")
    expiry = (now + timedelta(days=730)).strftime("%Y%m%dT%H%M%S")
    
    # Generate random IDs for pi and ri
    pi = f"3-{random.randint(10000000000000000000, 99999999999999999999)}"
    ri = f"4-{random.randint(10000000000000000000, 99999999999999999999)}"
    rn = f"4-{random.randint(10000000000000000, 99999999999999999)}"
    
    return {
        "m2m:cin": {
            "pi": pi,
            "ri": ri,
            "ty": 4,
            "ct": timestamp,
            "st": random.randint(10000, 99999),
            "rn": rn,
            "lt": timestamp,
            "et": expiry,
            "lbl": ["string"],
            "cs": len(str(content)),
            "cr": f"SOriginAE-{uuid.uuid4().hex[:2].upper()}",
            "con": str(content)
        }
    }

@app.get("/descriptor")
async def get_descriptor(node: str = Query(..., description="Node ID to get descriptor for")):
    """
    Get the descriptor for a specific node.
    Returns parameter information for the given node.
    """
    parameters = get_node_parameters(node)
    if not parameters:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Node with ID {node} not found"}
        )
    
    # Format the parameters as a descriptor
    descriptor = [param["parameter_name"] for param in parameters]
    return create_response(descriptor)

@app.get("/data")
async def get_data(node: str = Query(..., description="Node ID to get data for")):
    """
    Get the latest data for a specific node.
    Returns randomly generated data for the given node.
    """
    parameters = get_node_parameters(node)
    if not parameters:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Node with ID {node} not found"}
        )
    
    # Generate random data for the parameters
    data = generate_random_data(parameters)
    return create_response(data)

@app.get("/domains")
async def get_domains():
    """
    Get a list of all available domains.
    Returns information about all domains in the system.
    """
    domains_list = []
    for domain in nodes_config["domains"]:
        domains_list.append({
            "domain_id": domain["domain_id"],
            "domain_name": domain["domain_name"],
            "domain_short_name": domain["domain_short_name"],
            "parameter_count": len(domain["parameters"]),
            "sensor_type_count": len(domain["sensor_types"])
        })
    
    return domains_list

@app.get("/domains/{domain_id}")
async def get_domain(domain_id: str):
    """
    Get detailed information about a specific domain.
    Returns domain information including parameters and sensor types.
    """
    for domain in nodes_config["domains"]:
        if domain["domain_id"] == domain_id:
            return domain
    
    return JSONResponse(
        status_code=404,
        content={"detail": f"Domain with ID {domain_id} not found"}
    )

@app.get("/sensor_types")
async def get_sensor_types():
    """
    Get a list of all available sensor types.
    Returns information about all sensor types in the system.
    """
    sensor_types_list = []
    for domain in nodes_config["domains"]:
        for sensor_type in domain["sensor_types"]:
            sensor_types_list.append({
                "sensor_type_id": sensor_type["sensor_type_id"],
                "sensor_type_name": sensor_type["sensor_type_name"],
                "domain_id": domain["domain_id"],
                "domain_name": domain["domain_name"],
                "parameter_count": len(sensor_type["parameters"]),
                "node_count": len(sensor_type["nodes"])
            })
    
    return sensor_types_list

@app.get("/sensor_types/{sensor_type_id}")
async def get_sensor_type(sensor_type_id: str):
    """
    Get detailed information about a specific sensor type.
    Returns sensor type information including parameters and nodes.
    """
    for domain in nodes_config["domains"]:
        for sensor_type in domain["sensor_types"]:
            if sensor_type["sensor_type_id"] == sensor_type_id:
                result = sensor_type.copy()
                result["domain_id"] = domain["domain_id"]
                result["domain_name"] = domain["domain_name"]
                return result
    
    return JSONResponse(
        status_code=404,
        content={"detail": f"Sensor type with ID {sensor_type_id} not found"}
    )

@app.get("/nodes")
async def get_nodes():
    """
    Get a list of all available nodes.
    Returns information about all nodes in the system.
    """
    nodes_list = []
    for domain in nodes_config["domains"]:
        for sensor_type in domain["sensor_types"]:
            for node in sensor_type["nodes"]:
                nodes_list.append({
                    "node_id": node["node_id"],
                    "node_name": node["node_name"],
                    "domain_id": domain["domain_id"],
                    "domain_name": domain["domain_name"],
                    "sensor_type_id": sensor_type["sensor_type_id"],
                    "sensor_type_name": sensor_type["sensor_type_name"],
                    "node_area": node["node_area"],
                    "node_protocol": node["node_protocol"]
                })
    
    return nodes_list

@app.get("/nodes/{node_id}")
async def get_node(node_id: str):
    """
    Get detailed information about a specific node.
    Returns node information including location and protocol details.
    """
    node_info = find_node(node_id)
    if not node_info:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Node with ID {node_id} not found"}
        )
    
    result = node_info["node"].copy()
    result["domain_id"] = node_info["domain"]["domain_id"]
    result["domain_name"] = node_info["domain"]["domain_name"]
    result["sensor_type_id"] = node_info["sensor_type"]["sensor_type_id"]
    result["sensor_type_name"] = node_info["sensor_type"]["sensor_type_name"]
    result["parameters"] = node_info["sensor_type"]["parameters"]
    
    return result

@app.get("/parameters")
async def get_parameters():
    """
    Get a list of all available parameters across all domains.
    Returns information about all parameters in the system.
    """
    parameters_list = []
    for domain in nodes_config["domains"]:
        for param in domain["parameters"]:
            param_copy = param.copy()
            param_copy["domain_id"] = domain["domain_id"]
            param_copy["domain_name"] = domain["domain_name"]
            parameters_list.append(param_copy)
    
    return parameters_list

@app.get("/domains/{domain_id}/parameters")
async def get_domain_parameters(domain_id: str):
    """
    Get parameters for a specific domain.
    Returns all parameters defined for the given domain.
    """
    for domain in nodes_config["domains"]:
        if domain["domain_id"] == domain_id:
            return domain["parameters"]
    
    return JSONResponse(
        status_code=404,
        content={"detail": f"Domain with ID {domain_id} not found"}
    )

@app.get("/sensor_types/{sensor_type_id}/nodes")
async def get_sensor_type_nodes(sensor_type_id: str):
    """
    Get nodes for a specific sensor type.
    Returns all nodes associated with the given sensor type.
    """
    for domain in nodes_config["domains"]:
        for sensor_type in domain["sensor_types"]:
            if sensor_type["sensor_type_id"] == sensor_type_id:
                return sensor_type["nodes"]
    
    return JSONResponse(
        status_code=404,
        content={"detail": f"Sensor type with ID {sensor_type_id} not found"}
    )

@app.get("/config")
async def get_full_config():
    """
    Get the complete configuration information.
    Returns the entire JSON structure with all domains, sensor types, nodes, and parameters.
    """
    return nodes_config

@app.get("/get-all")
async def get_all():
    """
    Get the complete configuration in a single response.
    Returns the entire JSON structure with all domains, sensor types, nodes, and parameters.
    Similar to /config endpoint but with a different route name.
    """
    return nodes_config

@app.get("/get-all-data")
async def get_all_data(node: str = Query(..., description="Node ID to get historical data for")):
    """
    Get one week of historical data for a specific node.
    Returns data points for the last week, with each point having the m2m:cin format.
    """
    parameters = get_node_parameters(node)
    if not parameters:
        return JSONResponse(
            status_code=404,
            content={"detail": f"Node with ID {node} not found"}
        )
    
    # Generate data for one week with 6-hour intervals (28 data points)
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    current_time = start_time
    
    data_points = []
    
    while current_time <= end_time:
        # Create a seed based on the timestamp to ensure consistent values for the same time
        seed = int(current_time.timestamp())
        random.seed(seed)
        
        # Generate data for this timestamp
        values = []
        for param in parameters:
            if param["data_type"] == "float":
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
                
                # Generate a value with realistic patterns based on time
                hour = current_time.hour
                day_of_year = current_time.timetuple().tm_yday
                
                # Base value with appropriate patterns
                base_value = 0
                if "Temperature" in param["parameter_name"]:
                    # Daily variation (higher during day, lower at night)
                    base_value = 20 + 7 * (1 - abs(hour - 12) / 12)
                    # Seasonal variation (simplified)
                    seasonal_factor = 0.5 * (1 + (day_of_year % 365) / 365 * 2 - 1)
                    base_value += seasonal_factor * 5
                elif "Humidity" in param["parameter_name"] or "Relative Humidity" in param["parameter_name"]:
                    # Inverse to temperature - higher at night, lower during day
                    base_value = 60 - 20 * (1 - abs(hour - 12) / 12)
                elif "PM2.5" in param["parameter_name"] or "PM10" in param["parameter_name"]:
                    # Higher during rush hours
                    rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
                    base_value = 15 + rush_hour_factor * 30
                elif "CO" in param["parameter_name"]:
                    # Higher during rush hours
                    rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
                    base_value = 0.5 + rush_hour_factor * 1.0
                elif "NO2" in param["parameter_name"]:
                    # Higher during rush hours
                    rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
                    base_value = 0.02 + rush_hour_factor * 0.05
                elif "pH" in param["parameter_name"]:
                    base_value = 7.0 + random.uniform(-0.5, 0.5)
                elif "Turbidity" in param["parameter_name"]:
                    # Check if it's a "rainy day" (using a hash of the day)
                    is_rainy = (hash(f"{current_time.day}-{current_time.month}") % 7) < 2
                    base_value = 2.0 + (5.0 if is_rainy else 0)
                elif "Dissolved Oxygen" in param["parameter_name"]:
                    # Temperature affects dissolved oxygen (inverse relationship)
                    temp = 20 + 7 * (1 - abs(hour - 12) / 12)
                    base_value = 14 - temp * 0.3
                    if base_value < 4:
                        base_value = 4
                elif "TDS" in param["parameter_name"]:
                    # Slight daily variation
                    base_value = 250 + random.uniform(-20, 20) + 15 * (1 - abs(hour - 12) / 12)
                elif "AQI" in param["parameter_name"]:
                    # Correlates with pollution patterns
                    rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
                    base_value = 60 + rush_hour_factor * 50
                else:
                    base_value = random.uniform(0, 100)
                
                # Add some random noise within the accuracy range
                value = round(base_value + random.uniform(-range_val, range_val), decimal_places)
                values.append(str(value))
            elif param["data_type"] == "integer":
                # For integer type parameters (like AQI)
                base_value = 0
                if "AQI" in param["parameter_name"]:
                    # Correlates with pollution patterns
                    rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
                    base_value = 60 + int(rush_hour_factor * 50)
                elif "Data Interval" in param["parameter_name"]:
                    base_value = 60  # 60 seconds default
                else:
                    base_value = random.randint(0, 100)
                
                values.append(str(base_value))
            elif param["data_type"] == "string":
                # For string type parameters (like AQL)
                if "AQL" in param["parameter_name"]:
                    aqi = 0
                    # Use the AQI value if we've already calculated it
                    for p, v in zip(parameters, values):
                        if "AQI" in p["parameter_name"]:
                            try:
                                aqi = int(float(v))
                                break
                            except:
                                pass
                    
                    # If no AQI was found, calculate a simulated one
                    if aqi == 0:
                        rush_hour_factor = max(0, 1 - min(abs(hour - 8), abs(hour - 18)) / 4)
                        aqi = 60 + int(rush_hour_factor * 50)
                    
                    # Determine AQL based on AQI
                    if aqi <= 50:
                        aql = "Good"
                    elif aqi <= 100:
                        aql = "Moderate"
                    elif aqi <= 150:
                        aql = "Unhealthy for Sensitive Groups"
                    elif aqi <= 200:
                        aql = "Unhealthy"
                    elif aqi <= 300:
                        aql = "Very Unhealthy"
                    else:
                        aql = "Hazardous"
                    
                    values.append(aql)
                elif "AQI-MP" in param["parameter_name"]:
                    # Main pollutant - pick one randomly with higher chance for common ones
                    pollutants = ["PM2.5", "PM10", "NO2", "O3", "CO", "SO2"]
                    weights = [0.4, 0.25, 0.15, 0.1, 0.05, 0.05]
                    mp = random.choices(pollutants, weights=weights, k=1)[0]
                    values.append(mp)
                else:
                    values.append("Unknown")
        
        # Reset the random seed to ensure other operations aren't affected
        random.seed()
        
        # Create a m2m:cin response for this data point
        timestamp = current_time.strftime("%Y%m%dT%H%M%S")
        expiry = (current_time + timedelta(days=730)).strftime("%Y%m%dT%H%M%S")
        
        # Generate consistent IDs for the same timestamp
        hash_base = f"{node}-{timestamp}"
        pi = f"3-{abs(hash(hash_base + 'pi')) % 90000000000000000000 + 10000000000000000000}"
        ri = f"4-{abs(hash(hash_base + 'ri')) % 90000000000000000000 + 10000000000000000000}"
        rn = f"4-{abs(hash(hash_base + 'rn')) % 90000000000000000 + 10000000000000000}"
        
        data_point = {
            "m2m:cin": {
                "pi": pi,
                "ri": ri,
                "ty": 4,
                "ct": timestamp,
                "st": abs(hash(hash_base + 'st')) % 90000 + 10000,
                "rn": rn,
                "lt": timestamp,
                "et": expiry,
                "lbl": ["historical"],
                "cs": len(str(values)),
                "cr": f"SOriginAE-{hash(hash_base + 'cr') % 256:02X}",
                "con": str(values)
            }
        }
        
        data_points.append(data_point)
        current_time += timedelta(hours=6)  # 6-hour intervals
    
    return data_points

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
