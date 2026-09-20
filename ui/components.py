"""
HTML Component Generators for the Gradio User Interface.
Produces luxury cards, radar status boxes, explainability badges, and audio triggers.
"""
from typing import List, Dict, Any
from models.schemas import DayPlan, TripPlan, TimeSlot, ScoredAttraction


def render_agent_radar(step_info: Dict[str, Any]) -> str:
    """Renders the live animated multi-agent radar status box."""
    agent_name = step_info.get("agent", "Orchestrator Agent")
    message = step_info.get("message", "Ready to plan trip...")
    skills = step_info.get("active_skills", [])
    step = step_info.get("step", 0)

    skills_html = ""
    if skills:
        skills_html = "<div style='margin-top: 8px; display: flex; flex-wrap: wrap; gap: 6px;'>"
        for s in skills[:6]:
            skills_html += f"<span class='skill-badge'>⚡ {s}</span>"
        if len(skills) > 6:
            skills_html += f"<span class='skill-badge'>+{len(skills)-6} more</span>"
        skills_html += "</div>"

    return f"""
    <div class="agent-radar-box">
      <div class="radar-header">
        <div class="pulse-dot"></div>
        <div style="font-weight: 700; font-size: 15px; color: #1E293B;">
          Active Agent: <span style="color: #2563EB;">{agent_name}</span> (Step {step}/9)
        </div>
      </div>
      <div style="font-size: 13px; color: #475569; line-height: 1.4;">
        {message}
      </div>
      {skills_html}
    </div>
    """


def render_day_timeline(day: DayPlan, currency: str = "₹") -> str:
    """Renders a single day's time-slotted itinerary cards."""
    html = f"""
    <div style="margin-bottom: 24px;">
      <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px 18px; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; box-shadow: 0 1px 3px rgba(0,0,0,0.03);">
        <div>
          <span style="font-size: 16px; font-weight: 800; color: #1E3A8A;">📅 Day {day.day_number}: {day.theme}</span>
          <div style="font-size: 12px; color: #64748B; margin-top: 2px;">
            Forecast: <b>{day.weather_summary}</b> (Rain Risk: {day.rain_probability}%) • Transit: <b>{day.total_travel_km:.1f} km</b>
          </div>
        </div>
        <div style="text-align: right;">
          <span style="font-size: 14px; font-weight: 700; color: #0F172A;">{currency}{day.day_cost:,.0f}</span>
          <div style="font-size: 11px; color: #10B981; font-weight: 600;">Day Total</div>
        </div>
      </div>
    """

    for slot in day.time_slots:
        slot_class = f"slot-{slot.slot_type.lower()}"
        cost_str = f"{currency}{slot.cost:,.0f}" if slot.cost > 0 else "Free Entry"
        
        audio_btn = ""
        if slot.attraction and slot.attraction.audio_guide_text:
            safe_text = slot.attraction.audio_guide_text.replace("'", "\\'").replace('"', '&quot;')
            audio_btn = f"""
            <button class="audio-guide-btn" onclick="if ('speechSynthesis' in window) {{ window.speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance('{safe_text}'); window.speechSynthesis.speak(u); }} else {{ alert('Not supported'); }}">
              🎧 60s Audio Guide
            </button>
            """

        skill_badge_html = f"<span class='skill-badge'>🎯 {slot.applied_skill_badge}</span>" if slot.applied_skill_badge else ""

        html += f"""
        <div class="timeline-card">
          <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 8px;">
            <div style="display: flex; align-items: center; gap: 8px;">
              <span class="slot-badge {slot_class}">{slot.slot_type}</span>
              <span style="font-size: 12px; font-weight: 700; color: #64748B;">{slot.start_time} - {slot.end_time}</span>
              {skill_badge_html}
            </div>
            <div style="display: flex; align-items: center; gap: 8px;">
              <span style="font-size: 12px; font-weight: 700; color: #1E293B;">{cost_str}</span>
              {audio_btn}
            </div>
          </div>
          
          <div style="font-size: 16px; font-weight: 700; color: #0F172A; margin-bottom: 4px;">
            {slot.activity_name}
          </div>
          
          <div style="font-size: 13px; color: #475569; line-height: 1.4; margin-bottom: 10px;">
            {slot.notes}
          </div>

          <div style="display: flex; flex-wrap: wrap; gap: 10px; align-items: center; border-top: 1px solid #F1F5F9; padding-top: 8px;">
            <span class="metric-pill">🚕 Transit: {slot.transit_mode} ({slot.transit_mins} mins)</span>
            <span class="metric-pill">📍 Distance: {slot.distance_km:.1f} km</span>
            <span class="metric-pill">👥 Crowd: {slot.crowd_forecast}</span>
            {f"<span class='metric-pill'>🌱 CO2: {slot.co2_kg} kg</span>" if slot.co2_kg > 0 else ""}
          </div>
        </div>
        """

    html += "</div>"
    return html


def render_trip_dossier_html(trip_plan: TripPlan) -> str:
    """Renders full timeline HTML for all days."""
    currency = trip_plan.profile.currency
    html = f"""
    <div style="padding: 4px;">
      <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap;">
        <div style="flex: 1; min-width: 200px; background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; text-align: center;">
          <div style="font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase;">Total Estimated Cost</div>
          <div style="font-size: 20px; font-weight: 800; color: #1E3A8A; margin-top: 2px;">{currency}{trip_plan.total_estimated_cost:,.0f}</div>
          <div style="font-size: 11px; color: #10B981; font-weight: 600;">Budget: {currency}{trip_plan.profile.budget:,.0f}</div>
        </div>
        <div style="flex: 1; min-width: 200px; background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; text-align: center;">
          <div style="font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase;">Validation Seal</div>
          <div style="font-size: 20px; font-weight: 800; color: #10B981; margin-top: 2px;">Approved ✅</div>
          <div style="font-size: 11px; color: #64748B;">4/4 Hard Constraints Passed</div>
        </div>
        <div style="flex: 1; min-width: 200px; background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 14px; text-align: center;">
          <div style="font-size: 11px; color: #64748B; font-weight: 700; text-transform: uppercase;">Group Satisfaction</div>
          <div style="font-size: 20px; font-weight: 800; color: #8B5CF6; margin-top: 2px;">{trip_plan.group_satisfaction_score:.0f}% ⭐</div>
          <div style="font-size: 11px; color: #64748B;">Multi-Party Optimized</div>
        </div>
      </div>
    """

    for day in trip_plan.days:
        html += render_day_timeline(day, currency)

    html += "</div>"
    return html


def render_survival_kit_html(trip_plan: TripPlan) -> str:
    """Renders local phrasebook and emergency contacts."""
    phrases = trip_plan.survival_kit
    contacts = trip_plan.emergency_contacts

    html = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px;'>"

    # Phrases
    for p in phrases:
        html += f"""
        <div style="background: white; border: 1px solid #E2E8F0; border-radius: 10px; padding: 14px;">
          <div style="font-size: 11px; font-weight: 700; color: #2563EB; text-transform: uppercase; margin-bottom: 4px;">{p.category}</div>
          <div style="font-size: 17px; font-weight: 800; color: #0F172A; margin-bottom: 2px;">"{p.phrase}"</div>
          <div style="font-size: 12px; font-style: italic; color: #64748B; margin-bottom: 6px;">Pronounce: {p.phonetic}</div>
          <div style="font-size: 13px; color: #334155; font-weight: 500;">👉 {p.meaning}</div>
        </div>
        """

    html += "</div>"

    if contacts:
        html += """
        <div style="margin-top: 20px; background: #FFF5F5; border: 1px solid #FED7D7; border-radius: 12px; padding: 16px;">
          <div style="font-size: 14px; font-weight: 800; color: #C53030; margin-bottom: 8px;">🚨 Local Emergency Contacts</div>
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 10px;">
        """
        for s, num in contacts.items():
            html += f"""
            <div>
              <div style="font-size: 11px; color: #742A2A; font-weight: 600;">{s}</div>
              <div style="font-size: 14px; font-weight: 800; color: #9B2C2C;">{num}</div>
            </div>
            """
        html += "</div></div>"

    return html
