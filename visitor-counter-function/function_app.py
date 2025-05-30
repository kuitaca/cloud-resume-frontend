import azure.functions as func
import json

app = func.FunctionApp()

@app.route(route="GetVisitorStats", auth_level=func.AuthLevel.ANONYMOUS, methods=["GET"])
def GetVisitorStats(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        "Hello from Azure Functions! This is working!",
        status_code=200
    )

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
