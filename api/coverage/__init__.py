import azure.functions as func
import json

def main(req: func.HttpRequest) -> func.HttpResponse:
    return func.HttpResponse(
        json.dumps({"status": "ok", "message": "function is alive"}),
        status_code=200,
        headers={"Content-Type": "application/json"}
    )
