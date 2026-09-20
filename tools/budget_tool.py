"""
Budget Tracking, Itemization, and Variance Calculator Tool using LangChain @tool decorator.
Enforces hard financial caps, computes itemized breakdowns, and identifies cost-saving substitutions.
"""
from typing import Dict, List, Any
from langchain_core.tools import tool
from models.schemas import DayPlan, Attraction


@tool
def calculate_trip_budget(
    days_data: List[Dict[str, Any]],
    total_budget: float,
    travelers_count: int = 4,
    currency: str = "₹"
) -> Dict[str, Any]:
    """
    Itemizes total trip expenses across admission fees, local transit, meals, and contingency.
    Computes variance against total budget cap.
    """
    total_entry_fees = 0.0
    total_transit = 0.0
    total_meals = 0.0

    for day in days_data:
        for slot in day.get("time_slots", []):
            cost = slot.get("cost", 0.0)
            fare = slot.get("estimated_fare", 0.0)
            slot_type = slot.get("slot_type", "")

            if slot_type in ["Lunch", "Dinner"]:
                total_meals += cost * travelers_count
            else:
                total_entry_fees += cost * travelers_count
                total_transit += fare

    contingency = round((total_entry_fees + total_transit + total_meals) * 0.08, 0)
    total_estimated = round(total_entry_fees + total_transit + total_meals + contingency, 0)
    variance = round(total_estimated - total_budget, 0)

    is_within_budget = variance <= 0

    cost_breakdown = {
        "Entry Fees": round(total_entry_fees, 0),
        "Local Transit": round(total_transit, 0),
        "Meals & Dining": round(total_meals, 0),
        "Contingency Buffer (8%)": contingency,
        "Total Estimated Cost": total_estimated
    }

    status_message = (
        f"✅ Within Budget! Total estimated cost {currency}{total_estimated:,.0f} leaves {currency}{abs(variance):,.0f} cushion."
        if is_within_budget else
        f"⚠️ Exceeds Budget! Estimated cost {currency}{total_estimated:,.0f} exceeds budget of {currency}{total_budget:,.0f} by {currency}{variance:,.0f}."
    )

    return {
        "is_within_budget": is_within_budget,
        "total_estimated_cost": total_estimated,
        "variance": variance,
        "cost_breakdown": cost_breakdown,
        "status_message": status_message
    }
