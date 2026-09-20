"""
Skill definitions for Skill-RAG procedural library.
Contains 15 actionable, structured travel planning skills.
"""
import json
from pathlib import Path
from typing import List, Dict, Any

SKILLS_REGISTRY: List[Dict[str, Any]] = [
    {
        "id": "destination_research",
        "name": "Destination Research Skill",
        "purpose": "Conduct deep, real-time research on destination attractions, historical background, and current conditions.",
        "when_to_use": "Triggered during the initial planning phase for any new trip.",
        "inputs": ["destination", "interests", "travel_dates"],
        "process": [
            "Query Tavily AI search with filtered query: f'{destination} tourist attractions opening hours entry fee 2026'.",
            "Extract candidate points of interest, categorizing into Heritage, Culture, Nature, Food, and Markets.",
            "Verify opening days, admission fees, and current temporary closures.",
            "Structure candidate POIs with GPS coordinates, indoor/outdoor flag, and typical visit duration."
        ],
        "tools": ["Tavily AI Search", "OpenStreetMap Nominatim", "Wikipedia REST API"],
        "output": "Structured list of candidate attractions with verified 2026 attributes."
    },
    {
        "id": "attraction_recommendation",
        "name": "Attraction Recommendation Skill",
        "purpose": "Score and rank candidate attractions using multi-attribute utility theory (MAUT) with transparent explainability.",
        "when_to_use": "After candidate attractions are discovered, to select the best sights for the traveler.",
        "inputs": ["candidate_attractions", "traveler_profile"],
        "process": [
            "Calculate 8-dimensional scores: Preference Match (30%), Rating (15%), Budget Fit (15%), Distance (10%), Time Fit (10%), Weather Fit (10%), Crowd Level (5%), Uniqueness (5%).",
            "Compute weighted overall score (0-100%) and confidence index.",
            "Generate human-readable explainability bullet points ('Why Recommended').",
            "Filter top-ranked attractions matching daily capacity constraints."
        ],
        "tools": ["Multi-Attribute Utility Scorer", "Explainability Generator"],
        "output": "Ranked list of scored attractions with detailed rationale and confidence scores."
    },
    {
        "id": "itinerary_planning",
        "name": "Itinerary Planning Skill",
        "purpose": "Synthesize recommended attractions into a balanced, time-slotted day-by-day travel schedule.",
        "when_to_use": "When converting ranked attractions into actionable daily plans.",
        "inputs": ["ranked_attractions", "duration_days", "travel_style", "group_type"],
        "process": [
            "Assign daily themes (e.g. Day 1: Royal Heritage; Day 2: Crafts & Culture; Day 3: Scenic Vistas).",
            "Structure daily slots: Morning (09:00-12:30), Lunch (12:30-14:00), Afternoon (14:00-17:00), Evening (17:00-19:30), Dinner (19:30-21:30).",
            "Respect opening and closing hours for each scheduled venue.",
            "Allocate buffer times between activities to prevent traveler exhaustion."
        ],
        "tools": ["Time Slot Allocator", "Opening Hours Checker"],
        "output": "Draft day-by-day timetable with assigned morning, afternoon, and evening venues."
    },
    {
        "id": "route_optimization",
        "name": "Route Optimization Skill",
        "purpose": "Minimize travel time, distance, and transit expense by solving the Traveling Salesperson Problem (TSP).",
        "when_to_use": "When sequencing sights within each day to eliminate cross-city backtracking.",
        "inputs": ["day_attractions", "hotel_starting_point"],
        "process": [
            "Calculate pairwise Haversine geodesic distance matrix between all sights.",
            "Apply greedy nearest-neighbor TSP heuristic to find optimal visitation sequence (A -> B -> C -> D).",
            "Calculate estimated transit times and recommend optimal transit mode (Walking vs. Metro vs. Auto vs. Taxi).",
            "Estimate per-leg transit fares and carbon footprint (kg CO2)."
        ],
        "tools": ["Haversine Distance Matrix", "TSP Nearest-Neighbor Solver", "Transit Cost Estimator"],
        "output": "Optimized visitation sequence with minimized total km and transit fare estimates."
    },
    {
        "id": "budget_optimization",
        "name": "Budget Optimization Skill",
        "purpose": "Enforce strict financial constraints, detect budget deficits, and substitute expensive items with top-rated free alternatives.",
        "when_to_use": "When estimated trip cost exceeds the user's budget ceiling.",
        "inputs": ["draft_itinerary", "total_budget", "travelers_count"],
        "process": [
            "Sum admission fees, estimated local transit, and meal allowances.",
            "Calculate budget variance: Delta = Estimated Cost - Target Budget.",
            "If Delta > 0: Identify highest-cost paid sights with comparable free public landmarks (e.g. public promenades, palace exterior viewpoints, heritage gates).",
            "Replace high-fee sights with top-rated free alternatives in the same geographic cluster.",
            "Recalculate total cost and verify that budget variance is non-positive (Delta <= 0)."
        ],
        "tools": ["Budget Itemizer", "Free Sights Knowledge Base", "Cost Variance Evaluator"],
        "output": "Budget-compliant itinerary with breakdown of savings and cost categories."
    },
    {
        "id": "weather_adaptation",
        "name": "Weather Adaptation Skill",
        "purpose": "Autonomously adapt daily schedules based on live weather forecasts (rain, storms, extreme heat).",
        "when_to_use": "When Open-Meteo detects rain probability > 50% or temperatures > 34°C.",
        "inputs": ["daily_weather_forecast", "draft_itinerary"],
        "process": [
            "Scan day forecast for precipitation (> 2.5 mm or rain probability > 50%).",
            "Identify scheduled outdoor activities (open-air forts, gardens, walking tours).",
            "Attempt slot-swap: move outdoor sights to a confirmed sunny day in the itinerary.",
            "If swap impossible: replace outdoor sight with top-rated indoor museum, art gallery, or royal palace hall.",
            "Tag affected day with 'Weather Adapted' badge and push update to traveler."
        ],
        "tools": ["Open-Meteo Weather API", "Indoor Sights Index", "Slot Swapping Engine"],
        "output": "Weather-resilient itinerary with indoor alternatives protecting against rain disruptions."
    },
    {
        "id": "family_planning",
        "name": "Family Trip Planning Skill",
        "purpose": "Tailor schedules for families with children or seniors, focusing on low fatigue, pacing, and interactive venues.",
        "when_to_use": "When group type is 'Family' or group contains children/seniors.",
        "inputs": ["traveler_profile", "candidate_attractions"],
        "process": [
            "Enforce pacing rule: maximum 3 major sightseeing stops per day.",
            "Insert mandatory 90-minute sit-down lunch break between 12:30 and 14:00.",
            "Filter out steep, strenuous climbs without vehicle access.",
            "Prioritize sights with interactive appeal (science centers, puppet shows, royal armories, boat rides)."
        ],
        "tools": ["Fatigue Curve Calculator", "Family Venue Scorer"],
        "output": "Family-friendly itinerary with gentle pacing and child-approved sights."
    },
    {
        "id": "solo_travel",
        "name": "Solo Trip Planning Skill",
        "purpose": "Maximize flexibility, vibrant social atmosphere, and photographic opportunities for solo adventurers.",
        "when_to_use": "When traveler group size is 1.",
        "inputs": ["traveler_profile", "candidate_attractions"],
        "process": [
            "Increase activity capacity to 4-5 dynamic stops per day.",
            "Incorporate vibrant walking heritage corridors, rooftop cafes, and photography viewpoints.",
            "Schedule golden-hour timing for iconic architectural facades.",
            "Highlight safety tips and public transit accessibility for independent travelers."
        ],
        "tools": ["Solo Pacing Engine", "Social Spots Index"],
        "output": "Fast-paced, vibrant itinerary optimized for solo discovery and photography."
    },
    {
        "id": "couple_planning",
        "name": "Couple Trip Planning Skill",
        "purpose": "Curate romantic, unhurried experiences with scenic sunset views and intimate dining.",
        "when_to_use": "When group type is 'Couple' or honeymoon.",
        "inputs": ["traveler_profile", "candidate_attractions"],
        "process": [
            "Schedule unhurried afternoon pacing with scenic panoramic viewpoints.",
            "Anchor evening slot specifically around sunset (17:30-18:45) at historic lakes or hill viewpoints.",
            "Pair evening schedule with candlelit heritage courtyard dinners.",
            "Avoid loud, commercial amusement parks unless explicitly requested."
        ],
        "tools": ["Golden Hour Calculator", "Romantic Venues Index"],
        "output": "Atmospheric itinerary featuring sunset vistas and heritage dining."
    },
    {
        "id": "food_discovery",
        "name": "Food Discovery Skill",
        "purpose": "Discover authentic culinary heritage and pair meals within walking distance of attractions.",
        "when_to_use": "When food is a specified interest or during lunch/dinner scheduling.",
        "inputs": ["scheduled_attraction_coordinates", "dietary_preferences"],
        "process": [
            "Search for authentic culinary institutions within 700m radius of morning/afternoon attractions.",
            "Identify signature regional dishes (e.g. Dal Baati Churma, Pyaaz Kachori, Ghevar in Jaipur).",
            "Filter venues for dietary compliance (Pure Vegetarian, Halal, Jain, Gluten-free).",
            "Integrate meal stops directly into the daily timeline with estimated meal costs."
        ],
        "tools": ["Culinary Geospatial Search", "Dietary Filter Engine"],
        "output": "Curated lunch and dinner stops closely paired with sightseeing locations."
    },
    {
        "id": "hidden_gems",
        "name": "Hidden Gem Discovery Skill",
        "purpose": "Unearth authentic, off-the-beaten-path cultural landmarks that typical tourist buses miss.",
        "when_to_use": "When user activates 'Hidden Gems' toggle or requests non-touristy spots.",
        "inputs": ["destination", "candidate_attractions"],
        "process": [
            "Query Tavily with anti-tourist-trap prompt: f'{destination} hidden gems off the beaten path secret viewpoints artisan workshops'.",
            "Filter for sights with high ratings (> 4.3) but lower review counts (under 1,500 reviews).",
            "Verify road accessibility and daytime safety.",
            "Substitute 1 mainstream crowded sight per day with an authentic artisan quarter or historic stepwell."
        ],
        "tools": ["Tavily Web Search", "Crowd Ratio Analyzer"],
        "output": "Inclusion of authentic hidden architectural wonders and local artisan centers."
    },
    {
        "id": "crowd_avoidance",
        "name": "Crowd Avoidance Skill",
        "purpose": "Analyze temporal congestion patterns to schedule popular monuments during low-density windows.",
        "when_to_use": "For high-traffic monuments or when traveler dislikes heavy crowds.",
        "inputs": ["candidate_attractions", "day_schedule"],
        "process": [
            "Identify high-traffic tier-1 monuments (e.g. Amber Fort, Hawa Mahal, Eiffel Tower).",
            "Schedule primary monuments at opening window (08:30-09:15 AM) to beat tourist bus arrivals.",
            "Shift secondary attractions to late afternoon lull (15:30-17:00).",
            "Display crowd forecast badges (Low 🟢, Moderate 🟡, Peak 🔴) on timeline cards."
        ],
        "tools": ["Temporal Crowd Predictor", "Early Access Scheduler"],
        "output": "Optimal arrival times avoiding peak ticketing and security queues."
    },
    {
        "id": "accessibility_planning",
        "name": "Accessibility Planning Skill",
        "purpose": "Ensure physical comfort for travelers with limited mobility, strollers, or wheelchair needs.",
        "when_to_use": "When walking tolerance is 'Low' or wheelchair/stroller needs are flagged.",
        "inputs": ["traveler_profile", "candidate_attractions"],
        "process": [
            "Filter venues for ramp access, elevators, and paved pathways.",
            "Flag fort ramparts requiring steep stair climbs and provide battery-car/golf-cart shuttle advice.",
            "Cap walking segments to under 500 meters between drop-off points.",
            "Include rest bench notes in venue descriptions."
        ],
        "tools": ["Mobility Index", "Elevation Profile Checker"],
        "output": "Accessible travel plan with minimal stair climbing and shuttle instructions."
    },
    {
        "id": "time_optimization",
        "name": "Time Optimization Skill",
        "purpose": "Allocate realistic dwell times and buffer intervals based on monument scale and category.",
        "when_to_use": "During timetable construction for all trips.",
        "inputs": ["attraction_category", "monument_scale"],
        "process": [
            "Apply category dwell standards: Massive Forts/Complexes (2.5-3.5h), Museums (2.0-2.5h), Photo Landmarks (30-45m), Gardens (1.0-1.5h), Bazaars (2.0h).",
            "Insert 20-30 minute transit buffer between adjacent stops.",
            "Prevent over-scheduling to ensure a relaxed, enjoyable experience without rushed checklists."
        ],
        "tools": ["Dwell Time Standards", "Transit Buffer Calculator"],
        "output": "Accurate time-slotted itinerary preventing scheduling overruns."
    },
    {
        "id": "itinerary_validation",
        "name": "Itinerary Validation Skill",
        "purpose": "Perform rigorous constraint verification across budget, opening hours, travel times, and weather.",
        "when_to_use": "Final phase before plan approval, and after any automated replanning iteration.",
        "inputs": ["trip_plan", "traveler_constraints"],
        "process": [
            "Test 1 (Budget): Verify Total Estimated Cost <= User Budget Cap. If failed, trigger Budget Optimization Skill.",
            "Test 2 (Hours): Verify every attraction is open on the designated day and slot. If failed, swap or shift day.",
            "Test 3 (Transit): Verify no leg exceeds 40 minutes travel time. If failed, re-cluster geographically.",
            "Test 4 (Weather): Verify no outdoor venues scheduled on heavy rain forecast days. If failed, trigger Weather Adaptation Skill.",
            "Lock plan as 'APPROVED' only when all 4 hard constraints pass simultaneously."
        ],
        "tools": ["Constraint Verification Engine", "Self-Correction Loop Orchestrator"],
        "output": "Validation report and approval seal, or trigger of autonomous replan loop."
    }
]

def export_skills_to_json(target_dir: Path):
    """Exports all 15 skills into individual JSON files for inspection."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for skill in SKILLS_REGISTRY:
        file_path = target_dir / f"{skill['id']}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(skill, f, indent=2, ensure_ascii=False)
