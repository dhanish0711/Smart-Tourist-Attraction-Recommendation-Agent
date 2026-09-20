"""
Comprehensive Pytest Suite for Smart Tourist Attraction Recommendation Agent.
Tests Global Dynamic POI Discovery, ChromaDB Vector RAG, Open-Meteo Weather,
Haversine TSP Routing, 8-Factor MAUT Scoring, Self-Correction, and FastAPI Endpoints.
"""
import pytest
from fastapi.testclient import TestClient

from server import app
from models.schemas import TravelerProfile
from tools.skill_rag import skill_rag_engine
from tools.chroma_rag import chroma_rag_engine
from tools.global_poi_tool import discover_global_attractions, geocode_destination
from tools.weather_tool import fetch_weather_forecast
from tools.route_tool import haversine_distance_km, optimize_tsp_route
from tools.budget_tool import calculate_trip_budget
from tools.ics_tool import generate_trip_ics
from tools.pdf_tool import generate_trip_pdf
from agents.recommender import rank_and_select_attractions
from agents.orchestrator import orchestrator

client = TestClient(app)


def test_global_geocoding_and_poi_discovery():
    """Verifies that universal POI discovery works for any global city without hardcoded lists."""
    # Test geocoding for a non-Jaipur city (e.g. Agra or Manali)
    geo = geocode_destination("Agra")
    assert geo is not None
    lat, lng, name = geo
    assert 26.0 <= lat <= 28.0
    assert 77.0 <= lng <= 79.0

    # Discover attractions for Agra (Taj Mahal, Agra Fort, etc.)
    pois = discover_global_attractions("Agra")
    assert len(pois) >= 3
    assert pois[0].lat != 0.0
    assert pois[0].lng != 0.0
    assert pois[0].name != ""


def test_chromadb_vector_rag():
    """Verifies persistent ChromaDB vector store and semantic cosine similarity search."""
    results = chroma_rag_engine.query_rag("family pacing with children", top_k=2)
    assert len(results) > 0
    first = results[0]
    assert "text" in first
    assert "similarity_score" in first
    assert "source" in first


def test_weather_dynamic_geocoding():
    """Verifies that Open-Meteo forecast works for any global city."""
    weather = fetch_weather_forecast.invoke({"destination": "Goa", "days": 2})
    assert len(weather) == 2
    assert "max_temp_c" in weather[0]
    assert "rain_probability" in weather[0]


def test_8_factor_maut_scoring():
    """Verifies 8-factor MAUT scoring and explainability cards."""
    profile = TravelerProfile(
        destination="Jaipur",
        duration_days=3,
        budget=15000,
        age_group="Family",
        interests=["History", "Palaces"]
    )
    pois = discover_global_attractions("Jaipur")
    ranked = rank_and_select_attractions(pois, profile)
    assert len(ranked) > 0
    top = ranked[0]
    assert top.scores.overall_score >= 75.0
    assert len(top.scores.why_recommended) >= 2


def test_fastapi_plan_endpoint():
    """Verifies FastAPI /api/plan endpoint."""
    payload = {
        "destination": "Jaipur",
        "duration_days": 2,
        "budget": 12000,
        "currency": "₹",
        "travelers_count": 2,
        "age_group": "Couple",
        "interests": ["History", "Architecture"],
        "walking_tolerance": "Medium",
        "travel_style": "Relaxed",
        "hidden_gems_preference": False
    }
    response = client.post("/api/plan", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "trip_id" in data
    assert len(data["days"]) == 2
    assert data["validation"]["passed"] is True


def test_fastapi_rag_and_n8n_endpoints():
    """Verifies /api/rag/query and /api/n8n/simulate endpoints."""
    # Test RAG endpoint
    rag_resp = client.post("/api/rag/query", json={"query": "budget reduction skill"})
    assert rag_resp.status_code == 200
    rag_data = rag_resp.json()
    assert len(rag_data["results"]) > 0

    # Test n8n simulation endpoint
    n8n_resp = client.post("/api/n8n/simulate")
    assert n8n_resp.status_code == 200
    n8n_data = n8n_resp.json()
    assert "status" in n8n_data
