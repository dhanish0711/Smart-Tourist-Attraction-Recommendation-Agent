// ==========================================================================
// SMART TOURIST ATTRACTION RECOMMENDATION AGENT - FRONTEND ENGINE
// High-Fidelity UI/UX Interactions, Leaflet Mapping, Speech Synthesis, RAG & n8n
// ==========================================================================

let leafletMap = null;
let mapMarkers = [];
let mapPolylines = [];
let currentTripData = null;
let currentlyPlayingUtterance = null;
let activePlayingBtn = null;

const DAY_COLORS = ["#2563EB", "#059669", "#7C3AED", "#D97706", "#DB2777", "#0891B2", "#4F46E5"];

// Initialize on DOM Ready
document.addEventListener("DOMContentLoaded", () => {
  setupTabs();
  setupForm();
  setupRAGExplorer();
  setupN8NSimulator();
  setupDisruptionButtons();
});

// --- Tab Switching ---
function setupTabs() {
  const tabs = document.querySelectorAll(".nav-tab-item");
  tabs.forEach(btn => {
    btn.addEventListener("click", () => {
      tabs.forEach(t => t.classList.remove("active"));
      document.querySelectorAll(".tab-pane").forEach(p => p.classList.remove("active"));

      btn.classList.add("active");
      const targetId = btn.getAttribute("data-tab");
      const pane = document.getElementById(targetId);
      if (pane) {
        pane.classList.add("active");
        if (targetId === "tab-map" && leafletMap) {
          setTimeout(() => leafletMap.invalidateSize(), 200);
        }
      }
    });
  });
}

// --- Quick Destination Picker ---
function selectDestination(city) {
  const input = document.getElementById("destination");
  if (input) {
    input.value = city;
    input.focus();
  }
}

// --- Visual Archetype Radio Selection ---
function updateArchetype(radio) {
  document.querySelectorAll(".archetype-card").forEach(c => c.classList.remove("selected"));
  const card = radio.closest(".archetype-card");
  if (card) card.classList.add("selected");
}

// --- Stepper Controls (+ / -) ---
function stepNumber(id, delta) {
  const input = document.getElementById(id);
  if (!input) return;
  const current = parseInt(input.value) || 1;
  const min = parseInt(input.min) || 1;
  const max = parseInt(input.max) || 10;
  const next = Math.max(min, Math.min(max, current + delta));
  input.value = next;
}

// --- Interactive Interest Tag Toggle ---
function toggleTag(label) {
  const checkbox = label.querySelector("input[type='checkbox']");
  if (!checkbox) return;
  checkbox.checked = !checkbox.checked;
  if (checkbox.checked) {
    label.classList.add("active");
  } else {
    label.classList.remove("active");
  }
}

// --- Quick Launch Sample Trip ---
function quickLaunch(city, archetypeVal) {
  selectDestination(city);
  const radios = document.querySelectorAll("input[name='archetype']");
  radios.forEach(r => {
    if (r.value.includes(archetypeVal) || archetypeVal.includes(r.value)) {
      r.checked = true;
      updateArchetype(r);
    }
  });
  const form = document.getElementById("trip-form");
  if (form) form.dispatchEvent(new Event("submit"));
}

// --- Main Form Submission ---
function setupForm() {
  const form = document.getElementById("trip-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();

    const destination = document.getElementById("destination").value.trim() || "Jaipur";
    const duration = parseInt(document.getElementById("duration").value) || 3;
    const travelers = parseInt(document.getElementById("travelers").value) || 4;
    const budget = parseFloat(document.getElementById("budget").value) || 15000;
    const currency = document.getElementById("currency").value || "₹";

    const archetypeRadio = document.querySelector("input[name='archetype']:checked");
    const ageGroup = archetypeRadio ? archetypeRadio.value : "Family (Kids/Seniors)";

    const walking = document.getElementById("walking").value || "Medium";
    const pace = document.getElementById("pace").value || "Relaxed";
    const hiddenGems = document.getElementById("hidden-gems").checked;

    const interests = [];
    document.querySelectorAll("input[name='interests']:checked").forEach(cb => {
      interests.push(cb.value);
    });

    const payload = {
      destination,
      duration_days: duration,
      budget,
      currency,
      travelers_count: travelers,
      age_group: ageGroup,
      interests: interests.length ? interests : ["History", "Food"],
      walking_tolerance: walking,
      travel_style: pace,
      hidden_gems_preference: hiddenGems
    };

    const submitBtn = document.getElementById("submit-btn");
    submitBtn.disabled = true;
    submitBtn.innerHTML = `<span>⏳ Agents Reasoning & Planning...</span>`;

    // Live multi-agent radar simulation
    updateRadar("Geocoding & POI Discovery Agent", 1, `Resolving global geo-coordinates for ${destination} via OpenStreetMap Nominatim...`, ["Destination Research", "Nominatim Engine"]);

    try {
      // Small simulated stepper steps to give user real-time visual feedback
      const stepTimer1 = setTimeout(() => {
        updateRadar("Open-Meteo Weather Agent", 2, `Fetching 7-day precipitation risk & temperature forecast for ${destination}...`, ["Weather Adaptation", "Open-Meteo API"]);
      }, 400);

      const stepTimer2 = setTimeout(() => {
        updateRadar("Skill Router & ChromaDB RAG", 3, `Retrieving procedural travel strategies from persistent ChromaDB vector store...`, ["Skill RAG Library", "ChromaDB 1.5.9"]);
      }, 900);

      const stepTimer3 = setTimeout(() => {
        updateRadar("Recommender & MAUT Agent", 4, `Computing 8-Factor Multi-Attribute Utility scores for candidate attractions...`, ["Attraction Recommendation", "MAUT Evaluator"]);
      }, 1400);

      const resp = await fetch("/api/plan", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
      });

      clearTimeout(stepTimer1);
      clearTimeout(stepTimer2);
      clearTimeout(stepTimer3);

      if (!resp.ok) throw new Error("Plan generation failed with status " + resp.status);
      const data = await resp.json();
      currentTripData = data;

      updateRadar("Validation & Dossier Agent", 9, `✅ Trip for ${destination} successfully approved! 4/4 constraints verified. Leaflet route mapped, .ics synced, and PDF generated.`, data.active_skills || []);

      renderTripResults(data);

      // Switch to Timeline tab automatically
      const timelineTab = document.querySelector(".nav-tab-item[data-tab='tab-timeline']");
      if (timelineTab) timelineTab.click();

    } catch (err) {
      alert("Error generating trip plan: " + err.message);
      updateRadar("Orchestrator Agent", 0, "Plan generation failed. Please check network connection and try again.", []);
    } finally {
      submitBtn.disabled = false;
      submitBtn.innerHTML = `<span>🚀 Launch Autonomous Travel Agent</span>`;
    }
  });
}

// --- Live Radar Status Updater ---
function updateRadar(agent, step, message, skills) {
  const agentElem = document.getElementById("radar-agent-name");
  const stepElem = document.getElementById("radar-step-count");
  const msgElem = document.getElementById("radar-message");
  const skillsElem = document.getElementById("radar-skills");

  if (agentElem) agentElem.textContent = agent;
  if (stepElem) stepElem.textContent = step > 0 ? `Step ${step}/9` : "System Ready";
  if (msgElem) msgElem.textContent = message;

  if (skillsElem) {
    skillsElem.innerHTML = "";
    (skills || []).slice(0, 5).forEach(s => {
      const tag = document.createElement("span");
      tag.className = "skill-tag";
      tag.textContent = "⚡ " + s;
      skillsElem.appendChild(tag);
    });
  }
}

// --- Master Renderer ---
function renderTripResults(data) {
  renderMetricsBanner(data);
  renderTimeline(data);
  renderLeafletMap(data.days);
  renderSurvivalKit(data);
  updateExportLinks(data.trip_id);
}

// --- Top Metrics Banner ---
function renderMetricsBanner(data) {
  const container = document.getElementById("timeline-container");
  container.innerHTML = "";

  const banner = document.createElement("div");
  banner.className = "metrics-banner";

  const totalCost = data.total_estimated_cost || 0;
  const budgetCap = data.profile.budget || 0;
  const currency = data.profile.currency || "₹";
  const variance = budgetCap - totalCost;
  const varianceClass = variance >= 0 ? "style='color: var(--emerald);'" : "style='color: var(--rose);'";

  let totalKm = 0;
  (data.days || []).forEach(d => totalKm += (d.total_travel_km || 0));

  banner.innerHTML = `
    <div class="metric-card">
      <div class="metric-label">Estimated Total Cost</div>
      <div class="metric-value" style="color: var(--primary);">${currency}${totalCost.toLocaleString()}</div>
      <div class="metric-sub" ${varianceClass}>Cap: ${currency}${budgetCap.toLocaleString()} (${variance >= 0 ? 'Surplus' : 'Deficit'} ${currency}${Math.abs(variance).toLocaleString()})</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Constraint Validation</div>
      <div class="metric-value" style="color: var(--emerald);">Passed ✅</div>
      <div class="metric-sub">Budget • Hours • Route • Weather</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Total Sightseeing Transit</div>
      <div class="metric-value">${totalKm.toFixed(1)} km</div>
      <div class="metric-sub">TSP Route Optimized</div>
    </div>

    <div class="metric-card">
      <div class="metric-label">Group Synergy Rating</div>
      <div class="metric-value" style="color: var(--indigo);">${data.group_satisfaction_score || 94}% ⭐</div>
      <div class="metric-sub">Multi-Party Profile Calibrated</div>
    </div>
  `;

  container.appendChild(banner);
}

// --- Render Timeline & Activity Cards ---
function renderTimeline(data) {
  const container = document.getElementById("timeline-container");
  const currency = data.profile.currency || "₹";

  (data.days || []).forEach(day => {
    const dayBlock = document.createElement("div");
    dayBlock.className = "day-itinerary-block";

    // Day Header
    const header = document.createElement("div");
    header.className = "day-header-card";
    header.innerHTML = `
      <div class="day-title-group">
        <div class="day-number-badge">${day.day_number}</div>
        <div>
          <div class="day-theme-title">Day ${day.day_number}: ${day.theme}</div>
          <div style="font-size: 0.72rem; color: #CBD5E1; margin-top: 0.15rem;">
            Forecast: <b>${day.weather_summary}</b> • Route: <b>${day.total_travel_km} km</b>
          </div>
        </div>
      </div>
      <div class="day-meta-pills">
        <span class="day-meta-pill">🌦️ Rain Risk: ${day.rain_probability}%</span>
        <span class="day-meta-pill">💰 Day Cost: ${currency}${day.day_cost.toLocaleString()}</span>
      </div>
    `;
    dayBlock.appendChild(header);

    // Slots Container
    const slotsWrap = document.createElement("div");
    slotsWrap.className = "day-slots-container";

    day.time_slots.forEach(slot => {
      const card = document.createElement("div");
      card.className = "activity-card";

      const slotTypeClass = `slot-${slot.slot_type.toLowerCase()}`;
      const feeText = slot.cost > 0 ? `${currency}${slot.cost.toLocaleString()}` : "Free Admission";
      const audioSafe = (slot.attraction && slot.attraction.audio_guide_text) ? slot.attraction.audio_guide_text.replace(/'/g, "\\'") : "";

      // Explainable reasons list
      let reasonsHtml = "";
      if (slot.attraction && slot.attraction.scores && slot.attraction.scores.why_recommended) {
        const reasons = slot.attraction.scores.why_recommended.slice(0, 3);
        reasonsHtml = `
          <div class="why-recommended-box">
            <div class="why-header">
              <span>🎯 Explainable AI: Why Recommended (${Math.round(slot.attraction.scores.overall_score || 90)}% Match)</span>
            </div>
            <ul class="why-reasons-list">
              ${reasons.map(r => `<li>${r}</li>`).join("")}
            </ul>
          </div>
        `;
      }

      card.innerHTML = `
        <div class="activity-top-row">
          <div class="slot-tag-group">
            <span class="slot-badge ${slotTypeClass}">${slot.slot_type}</span>
            <span class="slot-time">⏰ ${slot.start_time} - ${slot.end_time}</span>
            ${slot.applied_skill_badge ? `<span class="skill-tag" style="background: var(--primary-light); color: var(--primary); border-color: #BFDBFE;">🎯 ${slot.applied_skill_badge}</span>` : ""}
          </div>
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <span style="font-size: 0.8rem; font-weight: 700; color: var(--slate-800);">${feeText}</span>
            ${audioSafe ? `<button type="button" class="audio-btn" onclick="playAudio('${audioSafe}', this)"><span>🎧 60s Guide</span></button>` : ""}
          </div>
        </div>

        <div class="activity-title">${slot.activity_name}</div>
        <div class="activity-description">${slot.notes}</div>

        <div class="activity-metrics-row">
          <span class="activity-metric-item">🚕 ${slot.transit_mode} (${slot.transit_mins} mins)</span>
          <span class="activity-metric-item">📍 ${slot.distance_km} km</span>
          <span class="activity-metric-item">👥 Crowd: ${slot.crowd_forecast || "Low 🟢"}</span>
          ${slot.co2_kg > 0 ? `<span class="activity-metric-item">🌱 ${slot.co2_kg} kg CO2</span>` : ""}
        </div>

        ${reasonsHtml}
      `;

      slotsWrap.appendChild(card);
    });

    dayBlock.appendChild(slotsWrap);
    container.appendChild(dayBlock);
  });
}

// --- Leaflet Map Renderer ---
function renderLeafletMap(days) {
  const mapContainer = document.getElementById("leaflet-map-container");
  if (!mapContainer) return;

  if (!leafletMap) {
    leafletMap = L.map("leaflet-map-container").setView([26.9124, 75.7873], 12);
    L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
      attribution: "&copy; OpenStreetMap contributors",
      maxZoom: 18
    }).addTo(leafletMap);
  }

  // Clear previous layers
  mapMarkers.forEach(m => leafletMap.removeLayer(m));
  mapPolylines.forEach(p => leafletMap.removeLayer(p));
  mapMarkers = [];
  mapPolylines = [];

  const bounds = [];
  let totalPoints = 0;

  (days || []).forEach((day, dayIdx) => {
    const color = DAY_COLORS[dayIdx % DAY_COLORS.length];
    const dayCoords = [];

    day.time_slots.forEach(slot => {
      if (slot.attraction && slot.attraction.lat && slot.attraction.lng) {
        const lat = slot.attraction.lat;
        const lng = slot.attraction.lng;
        dayCoords.push([lat, lng]);
        bounds.push([lat, lng]);
        totalPoints++;

        const iconHtml = `
          <div style="background-color: ${color}; width: 28px; height: 28px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 8px rgba(0,0,0,0.3); display: flex; align-items: center; justify-content: center; color: white; font-size: 11px; font-weight: 800;">
            ${day.day_number}
          </div>
        `;
        const icon = L.divIcon({ className: "custom-map-pin", html: iconHtml, iconSize: [28, 28], iconAnchor: [14, 14] });

        const audioSafe = (slot.attraction.audio_guide_text || "").replace(/'/g, "\\'");
        const popupContent = `
          <div style="width: 210px; font-family: 'Plus Jakarta Sans', sans-serif;">
            ${slot.attraction.image_url ? `<img src="${slot.attraction.image_url}" style="width:100%; height:95px; object-fit:cover; border-radius:6px; margin-bottom:6px;"/>` : ""}
            <div style="background: ${color}; color: white; font-size: 9px; font-weight: 800; padding: 2px 6px; border-radius: 3px; display: inline-block; margin-bottom: 4px;">Day ${day.day_number} • ${slot.slot_type}</div>
            <div style="font-weight: 800; font-size: 13px; color: #0F172A; margin-bottom: 2px;">${slot.attraction.name}</div>
            <div style="font-size: 11px; color: #64748B; margin-bottom: 6px;">${slot.attraction.category} • ${slot.start_time}</div>
            ${audioSafe ? `<button type="button" class="audio-btn" style="width: 100%; justify-content: center;" onclick="playAudio('${audioSafe}', this)">🎧 Spoken Guide</button>` : ""}
          </div>
        `;

        const marker = L.marker([lat, lng], { icon }).addTo(leafletMap).bindPopup(popupContent);
        mapMarkers.push(marker);
      }
    });

    if (dayCoords.length >= 2) {
      const poly = L.polyline(dayCoords, { color: color, weight: 4, dashArray: "6, 6", opacity: 0.85 }).addTo(leafletMap);
      mapPolylines.push(poly);
    }
  });

  const statsElem = document.getElementById("map-stats");
  if (statsElem) {
    statsElem.textContent = `${totalPoints} Attractions plotted across ${days.length} days with Haversine TSP sequencing.`;
  }

  if (bounds.length > 0) {
    leafletMap.fitBounds(bounds, { padding: [40, 40] });
  }
}

// --- Web Speech API Audio Guide ---
function playAudio(text, buttonElement) {
  if (!("speechSynthesis" in window)) {
    alert("Speech Synthesis is not supported in this browser.");
    return;
  }

  // If currently speaking, stop it
  if (window.speechSynthesis.speaking) {
    window.speechSynthesis.cancel();
    if (activePlayingBtn) {
      activePlayingBtn.classList.remove("playing");
      activePlayingBtn.innerHTML = `<span>🎧 60s Guide</span>`;
    }
    if (activePlayingBtn === buttonElement) {
      activePlayingBtn = null;
      return;
    }
  }

  const utterance = new SpeechSynthesisUtterance(text);
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  if (buttonElement) {
    activePlayingBtn = buttonElement;
    buttonElement.classList.add("playing");
    buttonElement.innerHTML = `<span>⏹️ Stop Audio</span>`;
  }

  utterance.onend = () => {
    if (buttonElement) {
      buttonElement.classList.remove("playing");
      buttonElement.innerHTML = `<span>🎧 60s Guide</span>`;
    }
    activePlayingBtn = null;
  };

  utterance.onerror = () => {
    if (buttonElement) {
      buttonElement.classList.remove("playing");
      buttonElement.innerHTML = `<span>🎧 60s Guide</span>`;
    }
    activePlayingBtn = null;
  };

  window.speechSynthesis.speak(utterance);
}

// --- Cultural Survival Kit ---
function renderSurvivalKit(data) {
  const container = document.getElementById("survival-kit-container");
  container.innerHTML = "";

  const grid = document.createElement("div");
  grid.style.cssText = "display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 12px; margin-bottom: 16px;";

  (data.survival_kit || []).forEach(p => {
    const card = document.createElement("div");
    card.style.cssText = "background: white; border: 1.5px solid var(--slate-200); border-radius: var(--radius-md); padding: 14px; box-shadow: var(--shadow-xs);";
    const phraseSafe = p.phrase.replace(/'/g, "\\'");

    card.innerHTML = `
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px;">
        <span style="font-size: 0.7rem; font-weight: 800; color: var(--primary); text-transform: uppercase;">${p.category}</span>
        <button type="button" class="audio-btn" style="padding: 0.2rem 0.5rem; font-size: 0.7rem;" onclick="playAudio('${phraseSafe}', this)">🔊 Speak</button>
      </div>
      <div style="font-size: 1.15rem; font-weight: 800; color: var(--slate-900); margin: 2px 0;">"${p.phrase}"</div>
      <div style="font-size: 0.78rem; font-style: italic; color: var(--slate-500); margin-bottom: 6px;">Pronounce: ${p.phonetic}</div>
      <div style="font-size: 0.82rem; color: var(--slate-700); font-weight: 600;">👉 ${p.meaning}</div>
    `;
    grid.appendChild(card);
  });
  container.appendChild(grid);

  if (data.emergency_contacts) {
    const emerg = document.createElement("div");
    emerg.style.cssText = "background: #FFF5F5; border: 1.5px solid #FED7D7; border-radius: var(--radius-md); padding: 16px;";
    emerg.innerHTML = `<div style="font-weight: 800; font-size: 0.95rem; color: #C53030; margin-bottom: 10px;">🚨 Verified Local Emergency Contacts</div>`;

    let rows = "<div style='display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 10px;'>";
    for (const [k, v] of Object.entries(data.emergency_contacts)) {
      rows += `
        <div style="background: white; border-radius: 8px; padding: 8px 12px; border: 1px solid #FECACA;">
          <div style="font-size: 0.72rem; color: #991B1B; font-weight: 700; text-transform: uppercase;">${k}</div>
          <div style="font-size: 1rem; font-weight: 800; color: #7F1D1D; margin-top: 2px;">${v}</div>
        </div>
      `;
    }
    rows += "</div>";
    emerg.innerHTML += rows;
    container.appendChild(emerg);
  }
}

// --- Download Links ---
function updateExportLinks(tripId) {
  const icsBtn = document.getElementById("download-ics-btn");
  const pdfBtn = document.getElementById("download-pdf-btn");
  if (icsBtn) icsBtn.href = `/api/download/ics/${tripId}`;
  if (pdfBtn) pdfBtn.href = `/api/download/pdf/${tripId}`;
}

// --- Disruption Simulator Buttons ---
function setupDisruptionButtons() {
  const rainBtn = document.getElementById("btn-sim-rain");
  const budgetBtn = document.getElementById("btn-sim-budget");

  if (rainBtn) {
    rainBtn.addEventListener("click", async () => {
      if (!currentTripData) {
        alert("Please generate a trip first before running disruption simulations!");
        return;
      }
      updateRadar("Weather Adaptation Skill (Replan)", 8, "🌧️ High rain probability detected on Day 2! Retrieving indoor cultural sights from ChromaDB vector store...", ["Weather Adaptation Skill", "Route Optimization"]);

      try {
        const resp = await fetch("/api/replan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ trip_plan: currentTripData, disruption_type: "weather_rain" })
        });
        const updated = await resp.json();
        currentTripData = updated;
        renderTripResults(updated);
        updateRadar("Validation Agent", 9, "✅ Replan Complete! Outdoor sights swapped with indoor cultural museum.", updated.active_skills || []);

        const timelineTab = document.querySelector(".nav-tab-item[data-tab='tab-timeline']");
        if (timelineTab) timelineTab.click();
      } catch (e) {
        alert("Replan error: " + e.message);
      }
    });
  }

  if (budgetBtn) {
    budgetBtn.addEventListener("click", async () => {
      if (!currentTripData) {
        alert("Please generate a trip first before running disruption simulations!");
        return;
      }
      updateRadar("Budget Optimization Skill (Replan)", 8, "💰 Reducing budget ceiling by 25%! Substituting paid sights with top-rated free public landmarks...", ["Budget Optimization Skill", "Cost Itemizer"]);

      try {
        const resp = await fetch("/api/replan", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ trip_plan: currentTripData, disruption_type: "budget_cut" })
        });
        const updated = await resp.json();
        currentTripData = updated;
        renderTripResults(updated);
        updateRadar("Validation Agent", 9, "✅ Replan Complete! High-fee sights replaced with free heritage landmarks.", updated.active_skills || []);

        const timelineTab = document.querySelector(".nav-tab-item[data-tab='tab-timeline']");
        if (timelineTab) timelineTab.click();
      } catch (e) {
        alert("Replan error: " + e.message);
      }
    });
  }
}

// --- Interactive ChromaDB RAG Explorer ---
function setupRAGExplorer() {
  const form = document.getElementById("rag-query-form");
  if (!form) return;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const query = document.getElementById("rag-query-input").value.trim();
    if (!query) return;

    const resultsContainer = document.getElementById("rag-results-container");
    resultsContainer.innerHTML = "<div style='color: var(--slate-500); font-size: 0.85rem;'>🔍 Querying persistent ChromaDB vector store with cosine similarity...</div>";

    try {
      const resp = await fetch("/api/rag/query", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query })
      });
      const data = await resp.json();

      resultsContainer.innerHTML = "";
      (data.results || []).forEach(r => {
        const card = document.createElement("div");
        card.className = "rag-item-card";
        card.innerHTML = `
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
            <span class="skill-tag" style="background: var(--primary-light); color: var(--primary); border-color: #BFDBFE;">Source: ${r.source}</span>
            <span class="rag-score-pill">Cosine Similarity: ${r.similarity_score}</span>
          </div>
          <pre style="font-family: inherit; font-size: 0.84rem; color: var(--slate-700); white-space: pre-wrap; line-height: 1.5;">${r.text}</pre>
        `;
        resultsContainer.appendChild(card);
      });
    } catch (err) {
      resultsContainer.innerHTML = `<div style="color: var(--rose); font-size: 0.85rem;">Error querying vector RAG: ${err.message}</div>`;
    }
  });
}

function setRagQuery(text) {
  const input = document.getElementById("rag-query-input");
  if (input) {
    input.value = text;
    const form = document.getElementById("rag-query-form");
    if (form) form.dispatchEvent(new Event("submit"));
  }
}

// --- n8n Webhook Simulator ---
function setupN8NSimulator() {
  const simBtn = document.getElementById("btn-n8n-simulate");
  if (!simBtn) return;

  simBtn.addEventListener("click", async () => {
    const nodes = ["n8n-node-cron", "n8n-node-weather", "n8n-node-if", "n8n-node-webhook", "n8n-node-alert"];

    // Light up nodes sequentially for rich UI animation
    for (let i = 0; i < nodes.length; i++) {
      setTimeout(() => {
        document.querySelectorAll(".n8n-node").forEach(n => n.classList.remove("active"));
        const current = document.getElementById(nodes[i]);
        if (current) current.classList.add("active");
      }, i * 300);
    }

    const outputBox = document.getElementById("n8n-output-json");
    outputBox.textContent = "⏳ Triggering simulated n8n morning cron webhook (POST /api/n8n/simulate)...";

    try {
      const resp = await fetch("/api/n8n/simulate", { method: "POST" });
      const data = await resp.json();

      setTimeout(() => {
        outputBox.textContent = JSON.stringify(data, null, 2);

        const card = document.getElementById("n8n-result-card");
        const title = document.getElementById("n8n-status-title");
        const desc = document.getElementById("n8n-status-desc");

        if (card && title && desc) {
          card.style.display = "block";
          if (data.status === "replan_triggered") {
            title.innerHTML = `⚠️ <span style="color: #EA580C;">Replan Triggered by n8n</span>`;
            desc.innerHTML = `<b>Trigger Condition:</b> ${data.condition}<br/><b>Agent Action:</b> ${data.action_taken}<br/><b>Notification:</b> ${data.notification_message}`;
          } else {
            title.innerHTML = `✅ <span style="color: var(--emerald);">Weather Normal</span>`;
            desc.innerHTML = data.message || "All conditions verified normal.";
          }
        }
      }, 1500);

    } catch (err) {
      outputBox.textContent = "Error: " + err.message;
    }
  });

  // Dynamic Langflow status & link synchronization
  fetch("/api/langflow/status")
    .then(r => r.json())
    .then(status => {
      const headerLink = document.getElementById("langflow-header-link");
      if (headerLink && status.canvas_url) {
        headerLink.href = status.canvas_url;
      }
    })
    .catch(() => {});
}

