"""
Comprehensive Pydantic schemas for the Smart Tourist Attraction Recommendation Agent.
"""
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field


class TravelerProfile(BaseModel):
    destination: str = Field(..., description="Target city or region")
    duration_days: int = Field(default=3, ge=1, le=14, description="Trip length in days")
    budget: float = Field(default=15000.0, ge=0, description="Total budget cap")
    currency: str = Field(default="₹", description="Currency symbol or code")
    travelers_count: int = Field(default=4, ge=1, description="Number of travelers")
    age_group: str = Field(default="Family", description="Solo, Couple, Family, Friends, Seniors")
    interests: List[str] = Field(default_factory=lambda: ["History", "Food"], description="Key interests")
    walking_tolerance: str = Field(default="Medium", description="Low, Medium, High")
    travel_style: str = Field(default="Relaxed", description="Relaxed, Moderate, Intensive")
    dietary_preferences: Optional[str] = Field(default="None", description="Dietary restrictions/preferences")
    hidden_gems_preference: bool = Field(default=False, description="Prioritize lesser-known places")


class Attraction(BaseModel):
    id: str
    name: str
    category: str  # Historical, Cultural, Nature, Food, Shopping, Adventure, Viewpoint
    lat: float
    lng: float
    entry_fee: float = 0.0
    typical_duration_hours: float = 1.5
    opening_time: str = "09:00"
    closing_time: str = "18:00"
    closed_days: List[str] = Field(default_factory=list)
    is_indoor: bool = False
    rating: float = 4.5
    review_count: int = 1200
    description: str = ""
    crowd_level: str = "Medium"  # Low, Medium, High
    best_time_to_visit: str = "Morning"
    tags: List[str] = Field(default_factory=list)
    address: str = ""
    image_url: str = ""
    audio_guide_text: str = ""
    verified_source: str = "Official Tourism Portal / Tavily 2026"


class ScoreBreakdown(BaseModel):
    preference_match: float       # 0-100 (30% weight)
    rating_quality: float         # 0-100 (15% weight)
    budget_fit: float             # 0-100 (15% weight)
    distance_efficiency: float    # 0-100 (10% weight)
    time_compatibility: float     # 0-100 (10% weight)
    weather_suitability: float    # 0-100 (10% weight)
    crowd_fit: float              # 0-100 (5% weight)
    uniqueness: float             # 0-100 (5% weight)
    overall_score: float          # 0-100 weighted
    confidence_score: float = 92.0 # 0-100
    why_recommended: List[str]    # Transparent human-readable explanations
    applied_skills: List[str] = Field(default_factory=list)
    verified_sources: List[str] = Field(default_factory=list)


class ScoredAttraction(BaseModel):
    attraction: Attraction
    scores: ScoreBreakdown


class TimeSlot(BaseModel):
    slot_type: str  # Morning, Lunch, Afternoon, Evening, Dinner
    start_time: str
    end_time: str
    attraction: Optional[Attraction] = None
    activity_name: str
    notes: str = ""
    cost: float = 0.0
    transit_mins: int = 0
    distance_km: float = 0.0
    transit_mode: str = "Walking"  # Walking, Auto-Rickshaw, Metro, Taxi
    estimated_fare: float = 0.0
    co2_kg: float = 0.0
    applied_skill_badge: Optional[str] = None
    crowd_forecast: str = "Low 🟢"  # Low 🟢, Moderate 🟡, Peak 🔴


class DayPlan(BaseModel):
    day_number: int
    date_str: str
    theme: str
    weather_summary: str = "Sunny, 28°C"
    rain_probability: int = 0
    max_temp_c: float = 28.0
    time_slots: List[TimeSlot] = Field(default_factory=list)
    day_cost: float = 0.0
    total_travel_km: float = 0.0
    transit_summary: str = ""


class ValidationResult(BaseModel):
    passed: bool
    budget_status: str = "Within Budget"  # "Within Budget" or "Exceeded"
    budget_variance: float = 0.0
    hours_status: str = "All Open"
    transit_status: str = "Realistic (< 35 mins/leg)"
    weather_status: str = "Compatible"
    detected_issues: List[str] = Field(default_factory=list)
    corrective_actions_taken: List[str] = Field(default_factory=list)
    iteration_count: int = 1


class SurvivalPhrase(BaseModel):
    phrase: str
    phonetic: str
    meaning: str
    category: str  # Ticketing, Food, Transport, Courtesy


class SkillDefinition(BaseModel):
    id: str
    name: str
    purpose: str
    when_to_use: str
    inputs: List[str]
    process: List[str]
    tools: List[str]
    output: str


class TripPlan(BaseModel):
    trip_id: str
    profile: TravelerProfile
    days: List[DayPlan] = Field(default_factory=list)
    total_estimated_cost: float = 0.0
    cost_breakdown: Dict[str, float] = Field(default_factory=dict)
    validation: ValidationResult
    survival_kit: List[SurvivalPhrase] = Field(default_factory=list)
    emergency_contacts: Dict[str, str] = Field(default_factory=dict)
    active_skills: List[str] = Field(default_factory=list)
    group_satisfaction_score: float = 90.0
    created_at: str = ""
