import azure.functions as func
import datetime
import json
import logging
import os
import requests
from azure.data.tables import TableServiceClient
from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
import uuid

app = func.FunctionApp()

@app.route(route="GetVisitorStats", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET", "POST"])
def GetVisitorStats(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Visitor counter function triggered.')
    
    try:
        # Get CosmosDB connection
        connection_string = os.environ["COSMOS_CONNECTION_STRING"]
        table_service = TableServiceClient.from_connection_string(connection_string)
        table_client = table_service.get_table_client("visitors")
        
        # Get visitor's IP and country
        visitor_ip = req.headers.get('X-Forwarded-For', req.headers.get('X-Real-IP', '127.0.0.1'))
        if ',' in visitor_ip:
            visitor_ip = visitor_ip.split(',')[0].strip()
        
        country = get_country_from_ip(visitor_ip)
        current_time = datetime.datetime.utcnow()
        current_month = current_time.strftime("%Y-%m")
        
        # Record this visit
        visit_id = str(uuid.uuid4())
        visit_entity = {
            "PartitionKey": "visits",
            "RowKey": visit_id,
            "Timestamp": current_time,
            "Country": country,
            "IP": hash(visitor_ip),  # Store hash for privacy
            "Month": current_month
        }
        
        try:
            table_client.create_entity(visit_entity)
        except ResourceExistsError:
            pass  # Entity already exists, that's ok
        
        # Update total counter
        try:
            total_entity = table_client.get_entity("stats", "total")
            total_count = total_entity.get("Count", 0) + 1
            total_entity["Count"] = total_count
            table_client.update_entity(total_entity)
        except ResourceNotFoundError:
            # Create initial counter
            total_entity = {
                "PartitionKey": "stats",
                "RowKey": "total", 
                "Count": 1
            }
            table_client.create_entity(total_entity)
            total_count = 1
        
        # Update monthly counter
        try:
            monthly_entity = table_client.get_entity("stats", current_month)
            monthly_count = monthly_entity.get("Count", 0) + 1
            monthly_entity["Count"] = monthly_count
            table_client.update_entity(monthly_entity)
        except ResourceNotFoundError:
            # Create monthly counter
            monthly_entity = {
                "PartitionKey": "stats",
                "RowKey": current_month,
                "Count": 1
            }
            table_client.create_entity(monthly_entity)
            monthly_count = 1
        
        # Get unique countries count
        unique_countries = get_unique_countries(table_client)
        
        # Return dashboard data
        dashboard_data = {
            "totalVisits": total_count,
            "countries": unique_countries,
            "thisMonth": monthly_count,
            "lastUpdated": current_time.isoformat()
        }
        
        response = func.HttpResponse(
            json.dumps(dashboard_data),
            status_code=200,
            headers={
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": "Content-Type"
            }
        )
        
        logging.info(f'Visitor counter updated: {dashboard_data}')
        return response
        
    except Exception as e:
        logging.error(f'Error in visitor counter: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": "Internal server error"}),
            status_code=500,
            headers={"Content-Type": "application/json"}
        )

def get_country_from_ip(ip_address):
    """Get country from IP address using a free geolocation service"""
    try:
        if ip_address in ['127.0.0.1', 'localhost', '::1']:
            return "Local"
        
        # Using ip-api.com (free, no API key needed)
        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if data.get('status') == 'success':
                return data.get('country', 'Unknown')
    except Exception as e:
        logging.warning(f'Could not get country for IP {ip_address}: {str(e)}')
    
    return "Unknown"

def get_unique_countries(table_client):
    """Count unique countries from visit records"""
    try:
        # Query all visit entities
        visits = table_client.query_entities("PartitionKey eq 'visits'")
        countries = set()
        
        for visit in visits:
            country = visit.get('Country', 'Unknown')
            if country and country != 'Unknown':
                countries.add(country)
        
        return len(countries)
    except Exception as e:
        logging.warning(f'Could not count unique countries: {str(e)}')
        return 0

# Handle CORS preflight requests
@app.route(route="GetVisitorStats", auth_level=func.AuthLevel.ANONYMOUS, methods=["OPTIONS"])
def GetVisitorStats_options(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        "",
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type"
        }
    )
