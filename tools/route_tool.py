"""
Route Optimization and Geospatial Distance Tool using LangChain @tool decorator.
Calculates Haversine distance matrix, solves TSP nearest-neighbor ordering,
estimates multi-modal transit modes (Walking, Metro, Auto, Cab), fares, and CO2 footprint.
"""
import math
from typing import List, Dict, Tuple, Any
from langchain_core.tools import tool
from models.schemas import Attraction

EARTH_RADIUS_KM = 6371.0


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two geographic coordinates in kilometers."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_KM * c


def optimize_tsp_route(attractions: List[Attraction]) -> List[Attraction]:
    """
    Applies greedy nearest-neighbor TSP heuristic to sequence sights
    in order to minimize total travel distance and eliminate cross-town backtracking.
    """
    if len(attractions) <= 2:
        return attractions

    unvisited = list(attractions)
    # Start with the northernmost / primary anchor attraction
    current = min(unvisited, key=lambda a: -a.lat)
    route = [current]
    unvisited.remove(current)

    while unvisited:
        nearest = min(
            unvisited,
            key=lambda a: haversine_distance_km(current.lat, current.lng, a.lat, a.lng)
        )
        route.append(nearest)
        unvisited.remove(nearest)
        current = nearest

    return route


def estimate_transit_leg(distance_km: float, is_south_asia: bool = True) -> Dict[str, Any]:
    """
    Estimates optimal transit mode, travel duration (mins), fare, and CO2 emissions.
    Adapts transit mode natively based on whether the destination is in South Asia (Auto-Rickshaw)
    or International (City Tram / Metro / Bus).
    """
    if distance_km <= 1.2:
        mode = "Walking 🚶"
        mins = int(max(distance_km / 4.5 * 60, 5))
        fare = 0.0
        co2 = 0.0
    elif distance_km <= 5.5:
        if is_south_asia:
            mode = "Auto-Rickshaw / Cab 🛺"
            mins = int(max(distance_km / 22.0 * 60 + 5, 8))
            fare = round(30.0 + distance_km * 14.0, 0)
            co2 = round(distance_km * 0.065, 2)
        else:
            mode = "Metro / City Tram 🚊"
            mins = int(max(distance_km / 25.0 * 60 + 5, 10))
            fare = round(50.0 + distance_km * 10.0, 0)
            co2 = round(distance_km * 0.035, 2)
    elif distance_km <= 12.0:
        mode = "Metro / Electric Transit 🚊"
        mins = int(max(distance_km / 28.0 * 60 + 8, 15))
        fare = round(40.0 + distance_km * 18.0, 0)
        co2 = round(distance_km * 0.045, 2)
    else:
        mode = "Cab / Taxi 🚕"
        mins = int(max(distance_km / 30.0 * 60 + 10, 20))
        fare = round(100.0 + distance_km * 22.0, 0)
        co2 = round(distance_km * 0.140, 2)

    return {
        "mode": mode,
        "transit_mins": mins,
        "estimated_fare": fare,
        "co2_kg": co2
    }


# Authentic local culinary hubs paired with nearby attractions
LOCAL_FOOD_STOPS = {
    "amber_fort": {
        "name": "1135 AD / Heritage Courtyard Thali",
        "type": "Authentic Rajasthani Royal Lunch",
        "specialty": "Laal Maas, Dal Baati Churma & Bajre ki Roti",
        "distance_m": 150,
        "cost_per_person": 600.0
    },
    "hawa_mahal": {
        "name": "Wind View Cafe & Tattoo Cafe",
        "type": "Rooftop View & Spiced Chai",
        "specialty": "Masala Chai, Pyaaz Kachori & Cold Coffee overlooking Hawa Mahal",
        "distance_m": 50,
        "cost_per_person": 250.0
    },
    "city_palace_jaipur": {
        "name": "The Palace Cafe / Baradari",
        "type": "Courtyard Heritage Bistro",
        "specialty": "Govind Gatta Curry, Missi Roti & Saffron Lassi",
        "distance_m": 100,
        "cost_per_person": 550.0
    },
    "johari_bazaar": {
        "name": "Laxmi Mishthan Bhandar (LMB)",
        "type": "Iconic 1727 Sweet & Thali House",
        "specialty": "Royal Rajasthani Thali, Ghevar & Paneer Ghewar",
        "distance_m": 80,
        "cost_per_person": 450.0
    }
}


@tool
def calculate_route_plan(attractions_data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Computes TSP-optimized order, total distance, leg-by-leg transit times,
    and associated transit costs.
    """
    attractions = [Attraction(**a) for a in attractions_data]
    optimized = optimize_tsp_route(attractions)

    total_km = 0.0
    total_fare = 0.0
    legs = []

    for i in range(len(optimized) - 1):
        from_poi = optimized[i]
        to_poi = optimized[i + 1]
        dist = haversine_distance_km(from_poi.lat, from_poi.lng, to_poi.lat, to_poi.lng)
        total_km += dist
        leg_info = estimate_transit_leg(dist)
        total_fare += leg_info["estimated_fare"]

        legs.append({
            "from": from_poi.name,
            "to": to_poi.name,
            "distance_km": round(dist, 2),
            **leg_info
        })

    return {
        "optimized_order": [a.id for a in optimized],
        "total_distance_km": round(total_km, 2),
        "total_transit_fare": round(total_fare, 0),
        "legs": legs
    }
