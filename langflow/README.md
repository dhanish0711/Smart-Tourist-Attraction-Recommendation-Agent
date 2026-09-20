# 🌊 Langflow Visual Orchestration Guide

This directory contains the visual flow definition for the **Smart Tourist Attraction Recommendation Agent**.

## 📁 File Contents
- `smart_tourist_flow.json`: Ready-to-import Langflow JSON export file containing the complete 6-stage visual pipeline:
  1. **Traveler Intake & Profile Node**
  2. **Skill Router Node (Skill-RAG)**
  3. **Tavily AI Search Node**
  4. **Open-Meteo Weather Node**
  5. **8-Factor MAUT Recommendation Engine Node**
  6. **TSP Itinerary & Food Pairing Node**
  7. **Validation & Self-Correction Feedback Loop Node**

---

## 🚀 How to Import into Langflow

1. **Install and Launch Langflow**:
   ```bash
   pip install langflow
   langflow run
   ```
2. Open your web browser at `http://127.0.0.1:7860`.
3. In Langflow, click **"New Flow"** $\rightarrow$ **"Import from JSON"**.
4. Select `langflow/smart_tourist_flow.json`.
5. The full visual agent architecture with all connected nodes, tools, and feedback loops will instantly appear on your canvas!

---

## 🎓 Why Use Langflow for Your Project Defense (Viva)
- **Visual Proof of Multi-Agent Architecture**: Rather than showing raw code, examiners can inspect the visual graph showing how the Skill Router dynamically retrieves skills, queries Tavily, fetches Open-Meteo weather, and feeds the validation loop.
- **Interactive Node Inspection**: Click on any node on the canvas to inspect its parameters, inputs, and outputs in real time.
