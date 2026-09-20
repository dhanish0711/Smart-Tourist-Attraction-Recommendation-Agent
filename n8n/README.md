# ⚡ n8n Travel Monitoring & Automation Workflow

This directory contains the automated monitoring workflow for the **Smart Tourist Attraction Recommendation Agent**.

## 📁 File Contents
- `travel_agent_workflow.json`: Ready-to-import n8n workflow file.

---

## 🔄 How the Enterprise Automation Works

```text
[ ⏰ 7:00 AM Cron ]    [ ⚡ On-Demand Webhook Trigger ]
         │                         │
         └────────────┬────────────┘
                      ▼
        Initialize Trip Context
       (destination, email, trip_id)
                      │
                      ▼
     Geocode Destination Coordinates
     (Open-Meteo Global Geocoding API)
                      │
                      ▼
     Fetch Live Destination Weather
     (Open-Meteo High-Resolution Forecast)
                      │
                      ▼
       Rain Risk Detected? (≥ 50%)
              /               \
           [YES]             [NO]
            │                 │
            ▼                 ▼
   Trigger AI Replan   Send Gmail Sunny Day
     Webhook API           Confirmation
   (POST /api/replan)   (Clear sky briefing)
            │
            ▼
    Send Gmail Rain Alert
   (HTML Email with Swapped
    Indoor Attractions & Links
    to Updated ICS & PDF Dossier)
```

---

## 🧩 The 9 Visual Nodes

1. **`Every Morning 7:00 AM Trigger`**: Daily automated cron check (`0 7 * * *`).
2. **`On-Demand Webhook Trigger`**: Allows triggering anytime via HTTP POST (`/webhook/trip-monitor`).
3. **`Initialize Trip Context`**: Dynamically sets traveler email, destination, and trip ID.
4. **`Geocode Destination Coordinates`**: Resolves ANY global destination (Kyoto, Paris, Khatoo, Ujjain, etc.) to exact coordinates via Open-Meteo Geocoding.
5. **`Fetch Live Weather (Open-Meteo)`**: Retrieves daily precipitation probability, rain sum, and temperature extremes.
6. **`Rain Alert Detected? (>=50%)`**: Conditional gate checking rain probability.
7. **`Trigger Agent Replan Webhook`**: Calls the FastAPI engine (`POST /api/replan`) to swap outdoor sights for indoor cultural museums.
8. **`Send Gmail Rain Alert`**: Dispatches a responsive HTML email with the revised schedule and 1-click links to download the new `.ics` calendar and PDF dossier.
9. **`Send Gmail Sunny Day Confirmation`**: Dispatches a sunny morning confirmation email informing the traveler that all scheduled outdoor sights are proceeding as planned.

---

## 🚀 How to Import into n8n Web

1. Open **[n8n Web](https://app.n8n.cloud)** (or local n8n on `http://localhost:5678`).
2. Click **"Workflows"** $\rightarrow$ **"Import from File"** (or open `travel_agent_workflow.json`, copy all text, and press `Ctrl + V` on the canvas).
3. Connect your Gmail account in the Gmail nodes using 1-click OAuth.
4. In terminal, expose your local agent port if using n8n Cloud:
   ```bash
   npx --yes localtunnel --port 8000
   # or: npx ngrok http 8000
   ```
5. Click **"Test workflow"** to run a test execution!

