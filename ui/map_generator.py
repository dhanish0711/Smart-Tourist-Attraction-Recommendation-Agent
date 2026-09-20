"""
Interactive Leaflet.js Map Generator.
Renders OpenStreetMap tiles, color-coded day markers, connecting route polylines,
and interactive popups with audio guide triggers.
"""
import json
from typing import List
from models.schemas import DayPlan, Attraction

DAY_COLORS = [
    "#2563EB",  # Day 1: Royal Blue
    "#10B981",  # Day 2: Emerald Green
    "#8B5CF6",  # Day 3: Purple
    "#F59E0B",  # Day 4: Amber
    "#EC4899"   # Day 5: Pink
]


def generate_leaflet_html(days: List[DayPlan], center_lat: float = 26.9124, center_lng: float = 75.7873) -> str:
    """
    Builds a standalone HTML document embedding a Leaflet.js map with
    markers, polylines, and audio guide triggers.
    """
    # Collect coordinates per day
    routes_json = []
    markers_json = []

    for day_idx, day in enumerate(days):
        color = DAY_COLORS[day_idx % len(DAY_COLORS)]
        day_coords = []

        for slot in day.time_slots:
            if slot.attraction and slot.attraction.lat and slot.attraction.lng:
                lat = slot.attraction.lat
                lng = slot.attraction.lng
                day_coords.append([lat, lng])

                audio_clean = (slot.attraction.audio_guide_text or "").replace("'", "\\'").replace('"', '&quot;')
                markers_json.append({
                    "lat": lat,
                    "lng": lng,
                    "name": slot.attraction.name,
                    "day": day.day_number,
                    "slot": slot.slot_type,
                    "color": color,
                    "image": slot.attraction.image_url,
                    "category": slot.attraction.category,
                    "audio": audio_clean
                })

        if len(day_coords) >= 2:
            routes_json.append({
                "day": day.day_number,
                "color": color,
                "coords": day_coords
            })

    markers_js_str = json.dumps(markers_json)
    routes_js_str = json.dumps(routes_json)

    html = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8" />
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body, html {{ margin: 0; padding: 0; height: 100%; width: 100%; font-family: system-ui, sans-serif; }}
    #map {{ height: 100%; width: 100%; border-radius: 12px; }}
    .leaflet-popup-content-wrapper {{ border-radius: 10px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
    .popup-card {{ width: 220px; }}
    .popup-img {{ width: 100%; height: 110px; object-fit: cover; border-radius: 6px; margin-bottom: 6px; }}
    .popup-title {{ font-size: 13px; font-weight: 700; color: #1E293B; margin-bottom: 2px; }}
    .popup-badge {{ font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; color: white; display: inline-block; margin-bottom: 6px; }}
    .audio-btn {{ background: #2563EB; color: white; border: none; padding: 5px 10px; font-size: 11px; border-radius: 5px; cursor: pointer; display: flex; align-items: center; gap: 4px; width: 100%; justify-content: center; }}
    .audio-btn:hover {{ background: #1D4ED8; }}
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map').setView([{center_lat}, {center_lng}], 12);
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18
    }}).addTo(map);

    var markers = {markers_js_str};
    var routes = {routes_js_str};
    var bounds = [];

    // Add Route Polylines
    routes.forEach(function(route) {{
      var polyline = L.polyline(route.coords, {{
        color: route.color,
        weight: 4,
        opacity: 0.85,
        dashArray: '8, 8'
      }}).addTo(map);
    }});

    // Add Markers
    markers.forEach(function(m) {{
      bounds.push([m.lat, m.lng]);
      var markerHtml = '<div style="background-color:' + m.color + '; width:26px; height:26px; border-radius:50%; border:3px solid white; box-shadow:0 2px 5px rgba(0,0,0,0.3); display:flex; align-items:center; justify-content:center; color:white; font-size:11px; font-weight:bold;">' + m.day + '</div>';
      var customIcon = L.divIcon({{
        className: 'custom-pin',
        html: markerHtml,
        iconSize: [26, 26],
        iconAnchor: [13, 13]
      }});

      var popupContent = '<div class="popup-card">';
      if (m.image) {{
        popupContent += '<img class="popup-img" src="' + m.image + '" alt="' + m.name + '"/>';
      }}
      popupContent += '<div class="popup-badge" style="background-color:' + m.color + '">Day ' + m.day + ' • ' + m.slot + '</div>';
      popupContent += '<div class="popup-title">' + m.name + '</div>';
      popupContent += '<div style="font-size:11px; color:#64748B; margin-bottom:8px;">' + m.category + '</div>';
      if (m.audio) {{
        popupContent += '<button class="audio-btn" onclick="playAudio(\\\'' + m.audio + '\\\')">🎧 60s Audio Guide</button>';
      }}
      popupContent += '</div>';

      L.marker([m.lat, m.lng], {{ icon: customIcon }}).addTo(map).bindPopup(popupContent);
    }});

    if (bounds.length > 0) {{
      map.fitBounds(bounds, {{ padding: [30, 30] }});
    }}

    function playAudio(text) {{
      if ('speechSynthesis' in window) {{
        window.speechSynthesis.cancel();
        var utterance = new SpeechSynthesisUtterance(text);
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        window.speechSynthesis.speak(utterance);
      }} else {{
        alert('Audio guide not supported in this browser.');
      }}
    }}
  </script>
</body>
</html>"""
    return html
