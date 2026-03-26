import azure.functions as func
import json
import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    headers = {
        "Content-Type": "application/json",
        "Access-Control-Allow-Origin": "*",
    }

    try:
        import anthropic

        elid = req.params.get("elid")
        if not elid:
            return func.HttpResponse(
                json.dumps({"error": "elid parameter required"}),
                status_code=400, headers=headers
            )

        path = os.path.join(os.path.dirname(__file__), "locations.json")
        with open(path) as f:
            locations = json.load(f)

        location = next((l for l in locations if str(l["elid"]) == str(elid)), None)
        if not location:
            return func.HttpResponse(
                json.dumps({"error": f"Location not found: {elid}"}),
                status_code=404, headers=headers
            )

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            return func.HttpResponse(
                json.dumps({"error": "ANTHROPIC_API_KEY not set"}),
                status_code=500, headers=headers
            )

        client = anthropic.Anthropic(api_key=api_key)

        payload = {
            "address": location["display_name"],
            "type": location["type"],
            "in_5g_coverage": location["in_5g_coverage"],
            "outdoor_signal_class": location["outdoor_signal_class"],
            "indoor_signal_class": location["indoor_signal_class"],
            "nearest_tower": location["nearest_tower"],
            "nearest_5g_tower": location.get("nearest_5g_tower"),
            "active_outages": [location["outage_description"]] if location["active_outage"] else [],
            "property_type": location["property_type"],
            "property_levels": location["property_levels"],
            "upgrade_planned": location["upgrade_planned"],
            "upgrade_site": location.get("upgrade_site"),
            "upgrade_within_months": location.get("upgrade_within_months"),
        }

        SYSTEM_PROMPT = """You are a helpful coverage advisor for Spark New Zealand. Your job is to take a structured JSON payload describing a customer's mobile coverage situation and write a plain-English explanation of it.

RULES:
- Write 2-4 sentences only. No bullet points. No headings.
- Use plain English at a Year 10 reading level.
- Always distinguish between outdoor and indoor signal.
- If in_5g_coverage is false but a nearest_5g_tower exists, mention it positively.
- If active_outages is non-empty, lead with that as the likely cause.
- If upgrade_planned is true, mention it as good news for the future.
- If property_levels is greater than 1, acknowledge upper floors may differ.
- Never mention technical terms like dBm, band numbers, or sector IDs.
- Never mention competitor networks.
- End with one clear implication for the customer.
- Tone: honest, warm, helpful. Not defensive. Not salesy.
- For areas refer to 'this area' rather than 'your address'.

Respond with only the narrative paragraph. No preamble, no JSON, no labels."""

        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=400,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": json.dumps(payload)}]
        )

        narrative = message.content[0].text.strip()

        return func.HttpResponse(
            json.dumps({
                "elid": elid,
                "location": location,
                "narrative": narrative,
            }),
            status_code=200, headers=headers
        )

    except Exception as e:
        import traceback
        return func.HttpResponse(
            json.dumps({
                "error": str(e),
                "traceback": traceback.format_exc()
            }),
            status_code=500, headers=headers
        )
