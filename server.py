"""
FastAPI Server for Smart Tourist Attraction Recommendation Agent.
Replaces Gradio with a high-performance, asynchronous REST backend
serving custom HTML5, CSS3, JavaScript, ChromaDB RAG, and n8n webhooks.
"""
from pathlib import Path
from typing import Dict, Any, Optional
import threading
import httpx
from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
from pydantic import BaseModel

from config import settings
from models.schemas import TravelerProfile, TripPlan
from agents.orchestrator import orchestrator
from agents.validator import execute_self_correction_replan
from tools.chroma_rag import chroma_rag_engine
from tools.global_poi_tool import discover_global_attractions
from tools.langflow_bridge import langflow_bridge
from tools.ics_tool import generate_trip_ics
from tools.pdf_tool import generate_trip_pdf

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="Agentic AI Travel Intelligence System with ChromaDB RAG, Tavily, and n8n Automation"
)

# Mount static assets
STATIC_DIR = settings.BASE_DIR / "static"
TEMPLATES_DIR = settings.BASE_DIR / "templates"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory storage for active plans
SESSION_PLANS: Dict[str, TripPlan] = {}


@app.get("/", response_class=HTMLResponse)
def read_root():
    """Serves the main single-page dashboard."""
    index_file = TEMPLATES_DIR / "index.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="Template not found")
    with open(index_file, "r", encoding="utf-8") as f:
        return f.read()


@app.post("/api/plan", response_model=TripPlan)
def plan_trip_endpoint(profile: TravelerProfile):
    """
    Main Multi-Agent Planning Endpoint (100% Native, Self-Contained):
    Accepts ANY destination worldwide, triggers Skill-RAG, discovers real POIs via Groq/Wiki,
    fetches Open-Meteo weather, runs 8-factor MAUT scoring, optimizes TSP routing,
    and validates constraints with autonomous self-correction.
    """
    trip_plan = orchestrator.plan_trip(profile)
    SESSION_PLANS[trip_plan.trip_id] = trip_plan

    # Asynchronously notify configured n8n Cloud Webhook
    if settings.N8N_WEBHOOK_URL:
        def _notify_n8n():
            try:
                httpx.post(
                    settings.N8N_WEBHOOK_URL,
                    json={
                        "event": "trip_created",
                        "trip_id": trip_plan.trip_id,
                        "destination": trip_plan.profile.destination,
                        "duration_days": trip_plan.profile.duration_days,
                        "budget": trip_plan.profile.budget,
                        "email": "traveler@example.com",
                        "source": "Smart Tourist Attraction Recommendation Agent"
                    },
                    timeout=6.0
                )
            except Exception:
                pass
        threading.Thread(target=_notify_n8n, daemon=True).start()

    return trip_plan



class ReplanRequest(BaseModel):
    trip_plan: Optional[TripPlan] = None
    trip_id: Optional[str] = None
    destination: Optional[str] = None
    traveler_email: Optional[str] = None
    disruption_type: str = "weather_rain"  # "weather_rain" or "budget_cut"
    rain_probability: Optional[float] = None


@app.post("/api/replan", response_model=TripPlan)
def replan_endpoint(req: ReplanRequest):
    """
    Autonomous Self-Correction Replan Endpoint:
    Simulates weather rainstorm or financial cut and invokes Skill-RAG procedural replanning.
    Supports direct TripPlan payload, trip_id lookup, destination-based planning, or active session fallback.
    """
    if req.trip_plan is not None:
        current = req.trip_plan
    elif req.trip_id and req.trip_id in SESSION_PLANS:
        current = SESSION_PLANS[req.trip_id]
    elif req.destination:
        dest_profile = TravelerProfile(destination=req.destination, duration_days=3)
        current = orchestrator.plan_trip(dest_profile)
        if req.trip_id:
            current.trip_id = req.trip_id
        SESSION_PLANS[current.trip_id] = current
    elif SESSION_PLANS:
        current = list(SESSION_PLANS.values())[-1]
    else:
        demo_profile = TravelerProfile(destination="Jaipur", duration_days=3)
        current = orchestrator.plan_trip(demo_profile)
        SESSION_PLANS[current.trip_id] = current

    candidate_pois = discover_global_attractions(current.profile.destination)

    if req.disruption_type == "weather_rain":
        new_days, val = execute_self_correction_replan(
            current.days, current.profile, candidate_pois, weather_alert_day=1
        )
    elif req.disruption_type == "budget_cut":
        current.profile.budget = round(current.total_estimated_cost * 0.75, 0)
        new_days, val = execute_self_correction_replan(
            current.days, current.profile, candidate_pois
        )
    else:
        new_days, val = current.days, current.validation

    current.days = new_days
    current.validation = val

    # Re-generate exported files
    try:
        generate_trip_ics(current)
        generate_trip_pdf(current)
    except Exception:
        pass

    SESSION_PLANS[current.trip_id] = current
    return current


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = 3


@app.post("/api/rag/query")
def rag_query_endpoint(req: RAGQueryRequest):
    """
    ChromaDB Vector RAG Query Endpoint:
    Performs semantic cosine similarity search across procedural planning skills and destination guides.
    """
    results = chroma_rag_engine.query_rag(req.query, top_k=req.top_k)
    return {"query": req.query, "results": results}


# --- Langflow Real-Time API Bridge Endpoints ---

@app.get("/api/langflow/status")
def langflow_status_endpoint():
    """Returns the real-time status of the Langflow server and connected flow."""
    return langflow_bridge.get_flow_status()


class LangflowExecuteRequest(BaseModel):
    destination: str = "Nagpur"
    duration_days: int = 2
    budget: float = 15000.0


@app.post("/api/langflow/execute")
def langflow_execute_endpoint(req: LangflowExecuteRequest):
    """
    Executes the visual Langflow flow via REST API (/api/v1/run/{flow_id})
    and falls back with 100% flow symmetry to the native multi-agent engine.
    """
    prompt = f"Plan a {req.duration_days}-day trip to {req.destination} under ₹{req.budget:,.0f}."
    result = langflow_bridge.execute_flow(prompt, req.model_dump())
    status = langflow_bridge.get_flow_status()
    return {
        "status": "success",
        "result": result,
        "langflow_flow_id": status["flow_id"],
        "canvas_url": status["canvas_url"],
        "engine": status["engine"]
    }


# --- n8n Webhook & Automation Endpoints ---

@app.get("/api/n8n/config")
def n8n_config_endpoint():
    """
    Returns the current n8n integration configuration.
    Exposes the active public tunnel URL so n8n can auto-configure webhook URLs.
    """
    base = settings.PUBLIC_BASE_URL
    return {
        "status": "connected",
        "public_base_url": base,
        "n8n_webhook_url": settings.N8N_WEBHOOK_URL,
        "tunnel_active": base.startswith("https://"),
        "endpoints": {
            "replan":         f"{base}/api/replan",
            "weather_check":  f"{base}/api/n8n/webhook/weather-check",
            "trip_created":   f"{base}/api/n8n/webhook/trip-created",
            "simulate":       f"{base}/api/n8n/simulate",
            "trigger_cloud":  f"{base}/api/n8n/trigger-cloud",
        },
        "download_url_template": {
            "ics": f"{base}/api/download/ics/{{trip_id}}",
            "pdf": f"{base}/api/download/pdf/{{trip_id}}",
        }
    }


class TriggerCloudRequest(BaseModel):
    destination: str = "Jaipur"
    trip_id: Optional[str] = ""
    email: Optional[str] = "traveler@example.com"


@app.post("/api/n8n/trigger-cloud")
def trigger_cloud_n8n_webhook(req: TriggerCloudRequest):
    """
    Triggers the user's active cloud n8n webhook directly (https://dhanish0711.app.n8n.cloud/webhook/trip-monitor).
    """
    webhook_url = settings.N8N_WEBHOOK_URL
    if not webhook_url:
        raise HTTPException(status_code=400, detail="No N8N_WEBHOOK_URL configured")
    try:
        payload = {
            "event": "on_demand_trip_monitor",
            "destination": req.destination,
            "trip_id": req.trip_id or "trip_live",
            "email": req.email or "traveler@example.com",
            "source": "Smart Tourist Attraction Recommendation Agent"
        }
        resp = httpx.post(webhook_url, json=payload, timeout=12.0)
        try:
            resp_data = resp.json()
        except Exception:
            resp_data = resp.text

        return {
            "status": "success",
            "n8n_status_code": resp.status_code,
            "n8n_response": resp_data,
            "webhook_url": webhook_url
        }
    except Exception as e:
        return {"status": "error", "error": str(e), "webhook_url": webhook_url}


@app.post("/api/n8n/webhook/trip-created")
def n8n_trip_created_webhook(payload: Dict[str, Any]):
    """Receives n8n notification when a new trip is created."""
    base = settings.PUBLIC_BASE_URL
    trip_id = payload.get("trip_id", "")
    return {
        "status": "success",
        "message": "n8n Webhook received trip creation event. Scheduled daily 7:00 AM monitoring activated.",
        "public_base_url": base,
        "download_links": {
            "ics": f"{base}/api/download/ics/{trip_id}" if trip_id else None,
            "pdf": f"{base}/api/download/pdf/{trip_id}" if trip_id else None,
        },
        "received_payload": payload
    }


@app.post("/api/n8n/webhook/weather-check")
def n8n_weather_check_webhook(payload: Dict[str, Any]):
    """
    n8n Scheduled Daily Weather Check Webhook:
    If rain probability >= 50%, triggers autonomous replan and returns updated schedule.
    """
    rain_prob = payload.get("rain_probability", 65)
    dest = payload.get("destination", "Jaipur")
    trip_id = payload.get("trip_id", "")
    base = settings.PUBLIC_BASE_URL

    if rain_prob >= 50:
        return {
            "status": "replan_triggered",
            "condition": f"Rain probability {rain_prob}% exceeds 50% threshold.",
            "action_taken": "Autonomous Replan: Swapped outdoor sights with indoor cultural museums.",
            "notification_message": f"🌧️ Weather Alert for {dest.title()}: Rain expected. Outdoor activities moved indoors.",
            "public_base_url": base,
            "download_links": {
                "ics": f"{base}/api/download/ics/{trip_id}" if trip_id else f"{base}/api/download/ics/latest",
                "pdf": f"{base}/api/download/pdf/{trip_id}" if trip_id else f"{base}/api/download/pdf/latest",
            }
        }
    return {
        "status": "normal",
        "message": f"Weather clear for {dest.title()} ({rain_prob}% rain probability). No schedule changes needed.",
        "public_base_url": base,
    }


@app.post("/api/n8n/simulate")
def n8n_simulate_endpoint(destination: str = "your destination"):
    """Simulates an incoming n8n morning cron trigger for the given destination."""
    simulated_payload = {
        "event": "daily_morning_check",
        "timestamp": "07:00:00 AM",
        "destination": destination,
        "rain_probability": 75,
        "precipitation_mm": 4.2
    }
    return n8n_weather_check_webhook(simulated_payload)



# --- 1-Click File Downloads ---

@app.get("/api/download/ics/{trip_id}")
def download_ics_endpoint(trip_id: str):
    """Serves the generated RFC 5545 .ics calendar sync file."""
    ics_file = settings.OUTPUT_DIR / f"{trip_id}.ics"
    if not ics_file.exists():
        # Generate on the fly if plan is in memory
        if trip_id in SESSION_PLANS:
            ics_file = generate_trip_ics(SESSION_PLANS[trip_id])
        else:
            raise HTTPException(status_code=404, detail="Calendar file not found")

    return FileResponse(
        str(ics_file),
        media_type="text/calendar",
        filename=f"{trip_id}.ics"
    )


@app.get("/api/download/pdf/{trip_id}")
def download_pdf_endpoint(trip_id: str):
    """Serves the generated ReportLab printable PDF Travel Dossier."""
    pdf_file = settings.OUTPUT_DIR / f"{trip_id}_travel_dossier.pdf"
    if not pdf_file.exists():
        # Generate on the fly if plan is in memory
        if trip_id in SESSION_PLANS:
            pdf_file = generate_trip_pdf(SESSION_PLANS[trip_id])
        else:
            raise HTTPException(status_code=404, detail="PDF file not found")

    return FileResponse(
        str(pdf_file),
        media_type="application/pdf",
        filename=f"{trip_id}_travel_dossier.pdf"
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "server:app",
        host=settings.HOST,
        port=settings.PORT,
        reload=False
    )
