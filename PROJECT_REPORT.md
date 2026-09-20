# Project Report: Smart Tourist Attraction Recommendation Agent
## Skill-Augmented Agentic AI Travel Intelligence & Autonomous Planning System

---

## 1. Problem Statement & Motivation
Modern digital tourism platforms suffer from several fundamental limitations:
1. **Static, Non-Adaptive Chatbots**: Most travel assistants are simple conversational wrappers around general-purpose LLMs that lack domain methodologies, generate hallucinations, and cannot perform spatial or temporal constraint optimization.
2. **The RAG Cold-Start Barrier**: Storing hundreds of thousands of tourist attractions in static vector databases is unmaintainable, expensive, and quickly obsolete as operating hours, ticket fees, and temporary closures fluctuate.
3. **Lack of Autonomous Self-Correction**: When user constraints (e.g. strict budgets, sudden rainstorms, or closed monuments) conflict with a proposed itinerary, standard platforms fail to autonomously renegotiate or replan the schedule.
4. **Disjointed Routing & Meal Scheduling**: Traditional systems often suggest sights in random geographic order, causing travelers to waste hours in cross-town traffic without realistic lunch or resting intervals.

To address these challenges, this project introduces the **Smart Tourist Attraction Recommendation Agent**, a cognitive multi-agent architecture combining **Skill-Augmented RAG**, **Tavily AI Real-Time Web Research**, **Environmental & Routing APIs**, and a deterministic **Autonomous Self-Correction Feedback Loop**.

---

## 2. Project Objectives
- **Objective 1: Procedural Skill-Augmented RAG**: Develop a modular library of 15 actionable travel planning skills that provides the agent with procedural methodology rather than static place descriptions.
- **Objective 2: Dynamic Real-Time Web Intelligence**: Integrate Tavily AI Search to dynamically research 2026 entry fees, active event notices, and unexpected closures on demand.
- **Objective 3: 8-Factor Explainable Multi-Attribute Scoring**: Formulate a transparent utility scoring algorithm based on Multi-Attribute Utility Theory (MAUT) with explainable reasoning cards and confidence ratings.
- **Objective 4: Spatial-Temporal Route Optimization**: Solve the Traveling Salesperson Problem (TSP) using Haversine geodesic clustering to eliminate cross-city backtracking and dynamically pair local culinary institutions within walking distance.
- **Objective 5: Deterministic Autonomous Self-Correction Loop**: Implement hard-constraint verification (Budget $\le$ Cap, Opening Hours, Realistic Transit, Weather Safety) that automatically triggers replanning iterations until all constraints are satisfied.
- **Objective 6: Full-Stack Interactive Interface & Automation**: Deliver an interactive modern FastAPI web application (Zero Gradio) with embedded Leaflet.js maps, client-side 60s AI audio guides, interactive ChromaDB RAG explorer, disruption simulators, and automated n8n daily monitoring workflows.

---

## 3. System Architecture & Methodology

```text
                                  👤 USER REQUEST
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │   ORCHESTRATOR AGENT   │
                            │ (Skill Router Planner) │
                            └────────────┬───────────┘
                                         │
                     Determines Active Skill Set & Tools
                                         │
         ┌───────────────────────────────┼───────────────────────────────┐
         ▼                               ▼                               ▼
  ┌──────────────┐                ┌──────────────┐                ┌──────────────┐
  │  SKILL-RAG   │                │  TAVILY AI   │                │  LIVE APIS   │
  │ (Methodology)│                │ (Fresh Web)  │                │(Weather, OSM)│
  └──────┬───────┘                └──────┬───────┘                └──────┬───────┘
         │                               │                               │
         └───────────────────────────────┼───────────────────────────────┘
                                         ▼
                            ┌────────────────────────┐
                            │ RECOMMENDATION ENGINE  │
                            │  (8-Factor MAUT)       │
                            └────────────┬───────────┘
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │   ITINERARY OPTIMIZER  │
                            │  (TSP Routing & Food)  │
                            └────────────┬───────────┘
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │    VALIDATION AGENT    │
                            │ (Self-Correction Loop) │
                            └────────────┬───────────┘
                                         │
                                   ┌─────┴─────┐
                                   ▼           ▼
                              [FAIL: REPLAN] [PASS: APPROVED]
                                   │           │
                                   └─────►─────┘
                                         │
                                         ▼
                            ┌────────────────────────┐
                            │  FINAL TRAVEL DOSSIER  │
                            └────────────┬───────────┘
                                         │
                     ┌───────────────────┼───────────────────┐
                     ▼                   ▼                   ▼
            ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
            │  WEB DASHBOARD  │ │  n8n AUTOMATION │ │   EXPORT DOCK   │
            │  • Leaflet Map  │ │  • Morning Cron │ │  • .ics Calendar│
            │  • Skill Badges │ │  • Weather Alert│ │  • PDF Dossier  │
            │  • Audio Guides │ │  • Replan Hook  │ │  • JSON Data    │
            └─────────────────┘ └─────────────────┘ └─────────────────┘
```

### Architectural Division of Labor:
- **Langflow**: Visual drag-and-drop orchestration, node inspection, and presentation/viva demonstration.
- **LangChain & LangGraph**: Programmatic intelligence, `@tool` decorators, stateful conditional loops, and structured output parsing.
- **Skill-RAG**: Vector store holding procedural operational skills.
- **Tavily**: Live web research tool.
- **Open-Meteo & OpenStreetMap**: Zero-cost, zero-key external environmental and coordinate providers.

---

## 4. Mathematical Formulations

### 4.1 8-Dimensional Multi-Attribute Utility Theory (MAUT)
Each candidate attraction $A_i$ is scored across 8 normalized utility dimensions $U_j(A_i) \in [0, 100]$:

$$\text{Overall Score}(A_i) = \sum_{j=1}^{8} w_j \cdot U_j(A_i)$$

Where the weights $\sum w_j = 1.0$ are assigned as:
- $w_1 = 0.30$: **Preference Match** (semantic overlap between attraction tags/category and traveler interests).
- $w_2 = 0.15$: **Rating & Quality** ($U_2 = \min(\max(R \times 20, 50), 100)$ where $R \in [1, 5]$).
- $w_3 = 0.15$: **Budget Fit** (normalized ratio of admission fee to daily per-person budget cap).
- $w_4 = 0.10$: **Distance Efficiency** (centrality and proximity to geographic cluster).
- $w_5 = 0.10$: **Time Compatibility** (alignment of typical dwell time with pacing style).
- $w_6 = 0.10$: **Weather Suitability** ($100\%$ on sunny days; $98\%$ indoor vs. $35\%$ outdoor during rain).
- $w_7 = 0.05$: **Crowd Level Fit** (suitability for traveler's tolerance for dense crowds).
- $w_8 = 0.05$: **Uniqueness & Heritage** (bonus for UNESCO World Heritage and iconic landmarks).

### 4.2 Haversine Geodesic Distance Matrix
For any two attractions $A_1(\phi_1, \lambda_1)$ and $A_2(\phi_2, \lambda_2)$:

$$\Delta \phi = \phi_2 - \phi_1, \quad \Delta \lambda = \lambda_2 - \lambda_1$$

$$a = \sin^2\left(\frac{\Delta \phi}{2}\right) + \cos(\phi_1)\cos(\phi_2)\sin^2\left(\frac{\Delta \lambda}{2}\right)$$

$$c = 2 \cdot \text{atan2}\left(\sqrt{a}, \sqrt{1-a}\right)$$

$$d = R_{\text{earth}} \cdot c \quad (R_{\text{earth}} = 6371.0\text{ km})$$

### 4.3 Traveling Salesperson Problem (TSP) Optimization
To eliminate zig-zag travel across the city, the daily route is ordered using a greedy nearest-neighbor heuristic:

$$\text{Route} = [A_{\text{start}}], \quad A_{k+1} = \arg\min_{A \in \text{Unvisited}} d(A_k, A)$$

---

## 5. Database Schema & Data Models

### Entity Relationship Models (SQL / Pydantic):

```text
Table: trips
├── id: VARCHAR(36) [PK]
├── user_id: VARCHAR(36)
├── destination: VARCHAR(100)
├── duration_days: INT
├── total_budget: FLOAT
├── currency: VARCHAR(10)
├── travelers_count: INT
├── age_group: VARCHAR(50)
├── walking_tolerance: VARCHAR(20)
├── travel_style: VARCHAR(20)
├── total_estimated_cost: FLOAT
├── validation_status: VARCHAR(20)
└── created_at: TIMESTAMP

Table: attractions
├── id: VARCHAR(50) [PK]
├── name: VARCHAR(200)
├── category: VARCHAR(50)
├── lat: FLOAT
├── lng: FLOAT
├── entry_fee: FLOAT
├── typical_duration_hours: FLOAT
├── opening_time: VARCHAR(10)
├── closing_time: VARCHAR(10)
├── is_indoor: BOOLEAN
├── rating: FLOAT
├── review_count: INT
├── crowd_level: VARCHAR(20)
└── verified_source: VARCHAR(255)

Table: itinerary_time_slots
├── id: VARCHAR(36) [PK]
├── trip_id: VARCHAR(36) [FK -> trips.id]
├── day_number: INT
├── slot_type: VARCHAR(20)  -- Morning, Lunch, Afternoon, Evening, Dinner
├── start_time: VARCHAR(10)
├── end_time: VARCHAR(10)
├── attraction_id: VARCHAR(50) [FK -> attractions.id]
├── transit_mode: VARCHAR(50)
├── transit_mins: INT
├── distance_km: FLOAT
├── estimated_fare: FLOAT
└── applied_skill: VARCHAR(100)
```

---

## 6. Viva Examination Questions & Model Answers

### Q1: Why is storing tourist places in RAG considered a weak architecture?
**Answer:** Tourist attractions change constantly—ticket prices fluctuate, monuments undergo maintenance, and opening hours shift seasonally. Furthermore, no database can store all 500,000+ tourist spots globally without massive maintenance overhead. Our solution implements **Skill-Augmented RAG**: we store *procedural planning methodologies* in RAG, use **Tavily AI Search** for fresh real-time web discovery, and query **Open-Meteo** and **OpenStreetMap** for live environmental and spatial constraints.

### Q2: What makes your system truly "Agentic" rather than a standard LLM chatbot?
**Answer:** A standard chatbot simply predicts next-token text in a single pass without verification. Our system implements a **closed-loop cognitive architecture**:
1. **Dynamic Tool Selection**: The Skill Router Agent selects only relevant skills and tools for the user's persona.
2. **Deterministic Constraint Checks**: The Validation Agent verifies hard numerical constraints (Budget $\le$ Cap, Opening Hours, Travel Times, Weather).
3. **Autonomous Self-Correction**: If any constraint fails, the agent autonomously retrieves a replanning skill from Skill-RAG, re-balances the plan, and iterates until the plan is proven valid.

### Q3: How do you handle group trips where different family members want different things?
**Answer:** We implement **Group Preference Optimization**. When a family profile is submitted (e.g. Dad wants History, Mom wants Local Food, Kids want Interactive Sights), the recommendation engine calculates a joint satisfaction function that balances diversity across the schedule while enforcing family pacing constraints (max 3 stops/day, low walking fatigue, and mandatory 90-minute meal buffers).

---

## 7. Conclusion
The Smart Tourist Attraction Recommendation Agent demonstrates that modern agentic AI systems excel when cognitive procedural knowledge (Skill-RAG), live web discovery (Tavily), deterministic algorithms (TSP & Haversine), and autonomous feedback loops work in harmony. The project provides an extensible, industry-grade template for intelligent autonomous travel planning.
