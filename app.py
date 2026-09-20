"""
Main Gradio Application for Smart Tourist Attraction Recommendation Agent.
Integrates Python multi-agent core, HTML5, CSS3, JavaScript (Leaflet.js),
Skill-RAG, Tavily web search, Open-Meteo weather, and autonomous replanning simulation.
"""
import os
from pathlib import Path
import gradio as gr

from config import settings
from models.schemas import TravelerProfile, TripPlan
from agents.orchestrator import orchestrator
from tools.ics_tool import generate_trip_ics
from tools.pdf_tool import generate_trip_pdf
from ui.components import render_agent_radar, render_trip_dossier_html, render_survival_kit_html
from ui.map_generator import generate_leaflet_html

# Read custom CSS
css_file = Path(__file__).resolve().parent / "ui" / "styles.css"
custom_css = ""
if css_file.exists():
    with open(css_file, "r", encoding="utf-8") as f:
        custom_css = f.read()

# In-memory session store for current active plan
CURRENT_PLAN: TripPlan = None


def run_agentic_pipeline(
    destination: str,
    duration: int,
    budget: float,
    currency: str,
    travelers_count: int,
    age_group: str,
    interests: list,
    walking_tolerance: str,
    travel_style: str,
    hidden_gems: bool
):
    """
    Generator function streaming live agent steps to the Gradio UI.
    """
    global CURRENT_PLAN
    profile = TravelerProfile(
        destination=destination or "Jaipur",
        duration_days=int(duration),
        budget=float(budget),
        currency=currency,
        travelers_count=int(travelers_count),
        age_group=age_group,
        interests=interests or ["History", "Food"],
        walking_tolerance=walking_tolerance,
        travel_style=travel_style,
        hidden_gems_preference=hidden_gems
    )

    stream = orchestrator.plan_trip_stream(profile)

    for update in stream:
        radar_html = render_agent_radar(update)
        
        if "final_plan" in update:
            plan: TripPlan = update["final_plan"]
            CURRENT_PLAN = plan

            timeline_html = render_trip_dossier_html(plan)
            map_html = generate_leaflet_html(plan.days)
            survival_html = render_survival_kit_html(plan)

            # Export files
            ics_path = generate_trip_ics(plan)
            pdf_path = generate_trip_pdf(plan)

            yield (
                radar_html,
                timeline_html,
                map_html,
                survival_html,
                str(ics_path),
                str(pdf_path),
                gr.update(visible=True)
            )
        else:
            yield (
                radar_html,
                "<div style='text-align: center; padding: 40px; color: #64748B;'>⏳ Agentic AI reasoning in progress...</div>",
                "<div style='text-align: center; padding: 40px; color: #64748B;'>🗺️ Generating route map...</div>",
                "<div style='text-align: center; padding: 40px; color: #64748B;'>🧭 Compiling survival kit...</div>",
                None,
                None,
                gr.update(visible=False)
            )


def simulate_rain_replan():
    """Simulates rain on Day 2 and executes autonomous replanning."""
    global CURRENT_PLAN
    if not CURRENT_PLAN:
        return (
            "<div class='agent-radar-box'>⚠️ Please generate a trip first before simulating disruptions.</div>",
            "", "", "", None, None
        )

    from agents.validator import execute_self_correction_replan
    from tools.tavily_tool import get_destination_pois

    candidate_pois = get_destination_pois(CURRENT_PLAN.profile.destination)
    new_days, val = execute_self_correction_replan(
        CURRENT_PLAN.days, CURRENT_PLAN.profile, candidate_pois, weather_alert_day=2
    )

    CURRENT_PLAN.days = new_days
    CURRENT_PLAN.validation = val

    ics_path = generate_trip_ics(CURRENT_PLAN)
    pdf_path = generate_trip_pdf(CURRENT_PLAN)

    radar_html = render_agent_radar({
        "agent": "Weather Adaptation Skill (Autonomous Replan)",
        "step": 8,
        "message": "🌧️ Simulated heavy rain on Day 2! Autonomous Agent swapped outdoor forts/gardens with indoor cultural museums and re-verified schedule.",
        "active_skills": ["Weather Adaptation Skill 🌦️", "Route Optimization Skill 🗺️"]
    })

    return (
        radar_html,
        render_trip_dossier_html(CURRENT_PLAN),
        generate_leaflet_html(CURRENT_PLAN.days),
        render_survival_kit_html(CURRENT_PLAN),
        str(ics_path),
        str(pdf_path)
    )


def simulate_budget_replan():
    """Simulates an explicit budget cut and triggers the budget optimization loop."""
    global CURRENT_PLAN
    if not CURRENT_PLAN:
        return (
            "<div class='agent-radar-box'>⚠️ Please generate a trip first before simulating disruptions.</div>",
            "", "", "", None, None
        )

    from agents.validator import execute_self_correction_replan
    from tools.tavily_tool import get_destination_pois

    # Cut budget by 25% to force over-budget condition
    CURRENT_PLAN.profile.budget = round(CURRENT_PLAN.total_estimated_cost * 0.75, 0)

    candidate_pois = get_destination_pois(CURRENT_PLAN.profile.destination)
    new_days, val = execute_self_correction_replan(
        CURRENT_PLAN.days, CURRENT_PLAN.profile, candidate_pois
    )

    CURRENT_PLAN.days = new_days
    CURRENT_PLAN.validation = val

    ics_path = generate_trip_ics(CURRENT_PLAN)
    pdf_path = generate_trip_pdf(CURRENT_PLAN)

    radar_html = render_agent_radar({
        "agent": "Budget Optimization Skill (Autonomous Replan)",
        "step": 8,
        "message": f"💰 Budget lowered to {CURRENT_PLAN.profile.currency}{CURRENT_PLAN.profile.budget:,.0f}! Agent autonomously substituted paid monuments with top-rated free public landmarks and heritage promenades.",
        "active_skills": ["Budget Optimization Skill 💰", "Route Optimization Skill 🗺️"]
    })

    return (
        radar_html,
        render_trip_dossier_html(CURRENT_PLAN),
        generate_leaflet_html(CURRENT_PLAN.days),
        render_survival_kit_html(CURRENT_PLAN),
        str(ics_path),
        str(pdf_path)
    )


# Build Gradio UI Blocks
with gr.Blocks(title=settings.APP_NAME) as demo:
    gr.HTML("""
    <div class="travel-header">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;">
        <div>
          <h1>🌍 Smart Tourist Attraction Recommendation Agent</h1>
          <p>Skill-Augmented Agentic AI • LangChain & Langflow • Tavily Web Intel • Autonomous Replanning</p>
        </div>
        <div style="background: rgba(255,255,255,0.15); padding: 6px 14px; border-radius: 9999px; font-size: 12px; font-weight: 600;">
          🟢 100% Free APIs Active (Open-Meteo + OSM)
        </div>
      </div>
    </div>
    """)

    with gr.Row():
        # Left Panel: Trip Intake Studio
        with gr.Column(scale=4):
            with gr.Accordion("🎯 Traveler Intake & Profile Settings", open=True):
                destination_input = gr.Dropdown(
                    label="📍 Target Destination / City",
                    choices=["Jaipur", "Mumbai", "Delhi", "Paris", "Tokyo", "New York", "Rome"],
                    value="Jaipur",
                    allow_custom_value=True
                )

                with gr.Row():
                    duration_input = gr.Slider(minimum=1, maximum=7, value=3, step=1, label="📅 Duration (Days)")
                    travelers_input = gr.Slider(minimum=1, maximum=10, value=4, step=1, label="👥 Travelers Count")

                with gr.Row():
                    budget_input = gr.Number(value=15000, label="💰 Total Budget Cap")
                    currency_input = gr.Dropdown(choices=["₹", "$", "€", "£"], value="₹", label="Currency")

                age_group_input = gr.Radio(
                    label="👨‍👩‍👧‍👦 Group Profile & Archetype",
                    choices=["Family (Kids/Seniors)", "Couple", "Solo", "Friends"],
                    value="Family (Kids/Seniors)"
                )

                interests_input = gr.CheckboxGroup(
                    label="❤️ Key Interests",
                    choices=["History", "Food", "Palaces", "Shopping", "Nature", "Hidden Gems", "Architecture"],
                    value=["History", "Food", "Palaces"]
                )

                with gr.Row():
                    walking_input = gr.Radio(
                        label="🚶 Walking Tolerance",
                        choices=["Low", "Medium", "High"],
                        value="Medium"
                    )
                    style_input = gr.Radio(
                        label="⏱️ Travel Style / Pace",
                        choices=["Relaxed", "Moderate", "Intensive"],
                        value="Relaxed"
                    )

                hidden_gems_input = gr.Checkbox(
                    label="💎 Prioritize Hidden Gems & Offbeat Spots",
                    value=False
                )

                plan_btn = gr.Button(
                    "🚀 Launch Autonomous Travel Agent",
                    variant="primary",
                    size="lg"
                )

        # Right Panel: Results, Timeline & Simulation
        with gr.Column(scale=7):
            radar_display = gr.HTML(
                render_agent_radar({
                    "agent": "Orchestrator Agent",
                    "step": 0,
                    "message": "System idle. Click 'Launch Autonomous Travel Agent' to start multi-agent planning.",
                    "active_skills": []
                })
            )

            with gr.Tabs() as tabs:
                with gr.TabItem("📅 Daily Itinerary Timeline"):
                    timeline_display = gr.HTML(
                        "<div style='text-align: center; padding: 60px 20px; color: #94A3B8; font-size: 15px;'>Your personalized, weather-verified day-by-day travel plan will appear here.</div>"
                    )

                with gr.TabItem("🗺️ Interactive Leaflet Route Map"):
                    map_display = gr.HTML(
                        "<div style='height: 450px; display: flex; align-items: center; justify-content: center; background: #F1F5F9; border-radius: 12px; color: #94A3B8;'>Interactive route map with day-colored markers and connecting paths will render here.</div>"
                    )

                with gr.TabItem("🧭 Cultural Survival Kit & Emergency"):
                    survival_display = gr.HTML(
                        "<div style='text-align: center; padding: 60px 20px; color: #94A3B8;'>Local language phonetic survival cards and emergency contacts will generate here.</div>"
                    )

                with gr.TabItem("⚠️ Autonomous Disruption Simulator"):
                    gr.Markdown("""
                    ### 🤖 Test the Agent's Autonomous Self-Correction Loop
                    Click any simulation button to trigger a live environmental or financial disruption. Watch the **Validation & Replan Agents** adapt the itinerary automatically!
                    """)
                    with gr.Row():
                        rain_sim_btn = gr.Button("🌧️ Simulate Heavy Rain on Day 2", variant="secondary")
                        budget_sim_btn = gr.Button("💰 Simulate 25% Budget Cut", variant="secondary")

                with gr.TabItem("📥 1-Click Export Dock"):
                    gr.Markdown("### 📲 Download Offline Travel Dossier")
                    with gr.Row():
                        ics_download = gr.File(label="📅 iCalendar (.ics) Sync File")
                        pdf_download = gr.File(label="📄 Printable PDF Travel Dossier")

    # Wire Event Handlers
    plan_btn.click(
        fn=run_agentic_pipeline,
        inputs=[
            destination_input,
            duration_input,
            budget_input,
            currency_input,
            travelers_input,
            age_group_input,
            interests_input,
            walking_input,
            style_input,
            hidden_gems_input
        ],
        outputs=[
            radar_display,
            timeline_display,
            map_display,
            survival_display,
            ics_download,
            pdf_download,
            radar_display  # dummy update
        ]
    )

    rain_sim_btn.click(
        fn=simulate_rain_replan,
        inputs=[],
        outputs=[
            radar_display,
            timeline_display,
            map_display,
            survival_display,
            ics_download,
            pdf_download
        ]
    )

    budget_sim_btn.click(
        fn=simulate_budget_replan,
        inputs=[],
        outputs=[
            radar_display,
            timeline_display,
            map_display,
            survival_display,
            ics_download,
            pdf_download
        ]
    )


if __name__ == "__main__":
    demo.launch(
        server_name=settings.HOST,
        server_port=settings.PORT,
        css=custom_css,
        theme=gr.themes.Soft(),
        share=False
    )
