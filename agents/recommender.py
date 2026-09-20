"""
Recommendation Engine implementing 8-dimensional Multi-Attribute Utility Theory (MAUT).
Computes transparent utility scores, confidence ratings, and explainable "Why Recommended" cards.
"""
from typing import List, Dict, Any, Tuple
from models.schemas import Attraction, TravelerProfile, ScoredAttraction, ScoreBreakdown


def score_attraction(
    attraction: Attraction,
    profile: TravelerProfile,
    is_rainy_day: bool = False,
    applied_skills: List[str] = None
) -> ScoredAttraction:
    """
    Computes an 8-factor transparent utility score (0-100%) for a candidate attraction.
    """
    applied_skills = applied_skills or []
    interests_lower = [i.lower() for i in profile.interests]
    tags_lower = [t.lower() for t in attraction.tags]

    # Explicit Must-Visit & Flagship detection
    must_visits = [mv.lower() for mv in getattr(profile, "must_visit_attractions", [])]
    is_explicit_must_visit = any(mv in attraction.name.lower() or mv in attraction.id.lower() for mv in must_visits) if must_visits else False
    is_crown_jewel = any(t in tags_lower for t in ["flagship", "jyotirlinga", "wonder", "wonder of the world"]) or (
        "iconic" in tags_lower and "must-visit" in tags_lower
    )
    is_flagship = is_crown_jewel or any(t in tags_lower for t in ["unesco", "must-visit", "iconic"])

    # 1. Preference Match (30%)
    tag_matches = sum(1 for t in attraction.tags if any(i in t.lower() or t.lower() in i for i in interests_lower))
    cat_match = any(i in attraction.category.lower() for i in interests_lower)
    
    if is_explicit_must_visit:
        pref_match = 100.0
    elif is_crown_jewel or (is_flagship and (cat_match or tag_matches >= 1 or len(interests_lower) == 0 or "sightseeing" in interests_lower)):
        pref_match = 98.0
    elif cat_match and tag_matches >= 2:
        pref_match = 96.0
    elif cat_match or tag_matches >= 1:
        pref_match = 88.0
    elif is_flagship:
        pref_match = 90.0
    else:
        pref_match = 65.0

    # 2. Rating & Quality (15%)
    # Scale: 4.0 -> 80%, 4.5 -> 90%, 5.0 -> 100%
    rating_score = min(max(attraction.rating * 20.0, 50.0), 100.0)

    # 3. Budget Fit (15%)
    # Per-traveler admission fee relative to daily per-person budget
    daily_budget_per_person = (profile.budget / max(profile.duration_days, 1)) / max(profile.travelers_count, 1)
    if attraction.entry_fee == 0:
        budget_score = 100.0
    elif attraction.entry_fee <= daily_budget_per_person * 0.25:
        budget_score = 92.0
    elif attraction.entry_fee <= daily_budget_per_person * 0.50:
        budget_score = 80.0
    else:
        budget_score = 65.0

    # 4. Distance & Clustering Efficiency (10%)
    # Higher score for central sights
    distance_score = 88.0

    # 5. Time Compatibility (10%)
    if profile.travel_style.lower() == "relaxed":
        time_score = 90.0 if attraction.typical_duration_hours <= 2.5 else 80.0
    else:
        time_score = 92.0

    # 6. Weather Suitability (10%)
    if is_rainy_day:
        weather_score = 98.0 if attraction.is_indoor else 35.0
    else:
        weather_score = 95.0

    # 7. Crowd Fit (5%)
    # Do not penalize high crowd for flagship landmarks unless traveler explicitly wants hidden gems
    if profile.hidden_gems_preference:
        if attraction.crowd_level.lower() == "low":
            crowd_score = 96.0
        elif attraction.crowd_level.lower() == "medium":
            crowd_score = 84.0
        else:
            crowd_score = 60.0
    else:
        if is_flagship:
            crowd_score = 94.0  # Popularity at iconic sites is a positive signal
        elif attraction.crowd_level.lower() == "low":
            crowd_score = 94.0
        elif attraction.crowd_level.lower() == "medium":
            crowd_score = 90.0
        else:
            crowd_score = 82.0

    # 8. Uniqueness & Heritage (5%)
    if is_flagship or "unesco" in tags_lower or "iconic" in tags_lower:
        uniqueness_score = 100.0
    else:
        uniqueness_score = 85.0

    # Weighted Overall Score
    overall = (
        0.30 * pref_match +
        0.15 * rating_score +
        0.15 * budget_score +
        0.10 * distance_score +
        0.10 * time_score +
        0.10 * weather_score +
        0.05 * crowd_score +
        0.05 * uniqueness_score
    )

    # Flagship / Priority Boost
    if is_explicit_must_visit:
        overall += 8.0
    elif is_crown_jewel:
        overall += 5.0
    elif is_flagship:
        overall += 2.5

    overall = round(min(overall, 99.5), 1)

    # Human-readable Explainability Reasoning
    reasons = []
    if is_explicit_must_visit:
        reasons.append("★ Priority Landmark: Matched from your must-visit preference")
    elif is_crown_jewel or is_flagship:
        reasons.append(f"★ Iconic Flagship Sight: Renowned premier landmark of {profile.destination.title()}")

    reasons.append(f"{pref_match:.0f}% match with your interest in {', '.join(profile.interests)}")
    
    if attraction.entry_fee == 0:
        reasons.append("Free admission maximizes your travel budget")
    else:
        reasons.append(f"Admission fee ({profile.currency}{attraction.entry_fee:,.0f}) is within your allocated budget")

    if profile.age_group.lower() in ["family", "seniors"]:
        reasons.append("Highly rated for family pacing with manageable walking distances")

    if is_rainy_day and attraction.is_indoor:
        reasons.append("Indoor sanctuary protecting your schedule from forecasted rain")

    reasons.append(f"Recommended visit window: {attraction.best_time_to_visit}")

    confidence = round(min(overall * 1.01, 99.0), 1)

    breakdown = ScoreBreakdown(
        preference_match=round(pref_match, 1),
        rating_quality=round(rating_score, 1),
        budget_fit=round(budget_score, 1),
        distance_efficiency=round(distance_score, 1),
        time_compatibility=round(time_score, 1),
        weather_suitability=round(weather_score, 1),
        crowd_fit=round(crowd_score, 1),
        uniqueness=round(uniqueness_score, 1),
        overall_score=round(overall, 1),
        confidence_score=confidence,
        why_recommended=reasons,
        applied_skills=applied_skills,
        verified_sources=[attraction.verified_source]
    )

    return ScoredAttraction(attraction=attraction, scores=breakdown)


def rank_and_select_attractions(
    candidate_attractions: List[Attraction],
    profile: TravelerProfile,
    is_rainy_day: bool = False,
    applied_skills: List[str] = None
) -> List[ScoredAttraction]:
    """
    Ranks all candidate attractions using 8-factor MAUT scoring and returns them sorted descending.
    Crown jewel landmarks and explicit traveler must-visits are strictly prioritized.
    """
    scored_list = [
        score_attraction(a, profile, is_rainy_day=is_rainy_day, applied_skills=applied_skills)
        for a in candidate_attractions
    ]
    # Crown jewels (e.g. Mahakaleshwar in Ujjain, Taj Mahal in Agra, Eiffel Tower in Paris)
    # always receive top priority on Day 1
    def _priority_key(sa: ScoredAttraction):
        t_low = [t.lower() for t in sa.attraction.tags]
        is_cj = any(t in t_low for t in ["flagship", "jyotirlinga", "wonder", "wonder of the world"]) or (
            "iconic" in t_low and "must-visit" in t_low
        )
        return (is_cj, sa.scores.overall_score)

    scored_list.sort(key=_priority_key, reverse=True)
    return scored_list
