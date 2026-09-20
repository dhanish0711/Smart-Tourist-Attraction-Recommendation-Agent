"""
Itinerary Builder Agent.
Synthesizes ranked attractions into structured, time-slotted day plans,
pairs destination-authentic local dining, and computes leg-by-leg transit metrics.
"""
from typing import List, Dict, Any, Optional
from models.schemas import Attraction, TravelerProfile, DayPlan, TimeSlot, ScoredAttraction
from tools.route_tool import haversine_distance_km, estimate_transit_leg, LOCAL_FOOD_STOPS


# ---------------------------------------------------------------------------
# Destination-aware cuisine data
# ---------------------------------------------------------------------------

# Category → representative Unsplash image (varied per category, not all the same fort)
CATEGORY_IMAGES = {
    "Historical": [
        "https://images.unsplash.com/photo-1599661046289-e31897846e41?w=800&q=80",  # Indian fort
        "https://images.unsplash.com/photo-1526711657229-e7e080ed7aa1?w=800&q=80",  # ruins
        "https://images.unsplash.com/photo-1534430480872-3498386e7856?w=800&q=80",  # arch ruins
    ],
    "Cultural": [
        "https://images.unsplash.com/photo-1545569341-9eb8b30979d9?w=800&q=80",  # temple
        "https://images.unsplash.com/photo-1512917774080-9991f1c4c750?w=800&q=80",  # museum
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",  # cultural
    ],
    "Nature": [
        "https://images.unsplash.com/photo-1501854140801-50d01698950b?w=800&q=80",  # lake
        "https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=800&q=80",  # forest
        "https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80",  # mountains
    ],
    "Shopping": [
        "https://images.unsplash.com/photo-1555529669-e69e7aa0ba9a?w=800&q=80",  # market
        "https://images.unsplash.com/photo-1558618666-fcd25c85cd64?w=800&q=80",  # bazaar
        "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800&q=80",  # shopping
    ],
}

DEFAULT_IMAGE = "https://images.unsplash.com/photo-1488646953014-85cb44e25828?w=800&q=80"


def get_attraction_image(category: str, attraction_id: str) -> str:
    """Returns a varied category-appropriate image URL, rotated by attraction ID hash."""
    pool = CATEGORY_IMAGES.get(category, [DEFAULT_IMAGE])
    idx = hash(attraction_id) % len(pool)
    return pool[idx]


# ---------------------------------------------------------------------------
# Destination cuisine profiles
# ---------------------------------------------------------------------------

# Cuisine profiles keyed by broad region/country
_CUISINE_PROFILES: Dict[str, Dict[str, Any]] = {
    # India – generic (used as fallback for unlisted Indian cities)
    "india": {
        "lunch_name": "Local Heritage Dhaba",
        "lunch_type": "Authentic Regional Thali",
        "lunch_specialty": "Dal, Rice, Sabzi & Roti Thali",
        "lunch_cost": 350.0,
        "dinner_name": "Regional Courtyard Restaurant",
        "dinner_specialty": "Traditional local cuisine & sweets",
        "dinner_cost": 450.0,
        "currency_note": "",
    },
    # Rajasthan / Jaipur
    "rajasthan": {
        "lunch_name": "Heritage Courtyard Thali House",
        "lunch_type": "Authentic Rajasthani Royal Lunch",
        "lunch_specialty": "Laal Maas, Dal Baati Churma & Bajre ki Roti",
        "lunch_cost": 600.0,
        "dinner_name": "Chokhi Dhani / Rajasthani Haveli Courtyard",
        "dinner_specialty": "Rajasthani Thali, Ghevar & Kulfi",
        "dinner_cost": 700.0,
        "currency_note": "",
    },
    # Maharashtra / Nagpur / Pune / Mumbai
    "maharashtra": {
        "lunch_name": "Vaishnavi Upahaar / Local Marathi Thali",
        "lunch_type": "Marathi Vegetarian Thali",
        "lunch_specialty": "Varan-Bhat, Zunka Bhakri, Puran Poli & Sol Kadhi",
        "lunch_cost": 350.0,
        "dinner_name": "Misal Pav & Street Food Corner",
        "dinner_specialty": "Misal Pav, Sabudana Khichdi & Modak",
        "dinner_cost": 300.0,
        "currency_note": "",
    },
    # Tamil Nadu
    "tamil_nadu": {
        "lunch_name": "Murugan Idli Shop / Saravana Bhavan",
        "lunch_type": "South Indian Vegetarian Meals",
        "lunch_specialty": "Full Meals on Banana Leaf — Rice, Sambar, Rasam, Poriyal & Papad",
        "lunch_cost": 250.0,
        "dinner_name": "Chettinad Cuisine Restaurant",
        "dinner_specialty": "Chettinad Chicken Curry, Idiyappam & Filter Coffee",
        "dinner_cost": 400.0,
        "currency_note": "",
    },
    # Karnataka / Bangalore / Mysore
    "karnataka": {
        "lunch_name": "MTR / Darshini Restaurant",
        "lunch_type": "Kannadiga Lunch Meals",
        "lunch_specialty": "Bisi Bele Bath, Ragi Mudde, Kosambari & Payasam",
        "lunch_cost": 300.0,
        "dinner_name": "Local Darshini / Udupi Restaurant",
        "dinner_specialty": "Set Dosa, Pulao, Coconut Chutney & Buttermilk",
        "dinner_cost": 350.0,
        "currency_note": "",
    },
    # Bengal / Kolkata
    "bengal": {
        "lunch_name": "Kewpie's Kitchen / Suruchi Restaurant",
        "lunch_type": "Authentic Bengali Lunch",
        "lunch_specialty": "Macher Jhol (Fish Curry), Shukto, Rice & Mishti Doi",
        "lunch_cost": 450.0,
        "dinner_name": "Nizams / Park Street Restaurant",
        "dinner_specialty": "Kati Roll, Kosha Mangsho & Rosogolla",
        "dinner_cost": 500.0,
        "currency_note": "",
    },
    # Gujarat / Ahmedabad / Surat
    "gujarat": {
        "lunch_name": "Gordhan Thal / Agashiye",
        "lunch_type": "Gujarati Unlimited Thali",
        "lunch_specialty": "Dal Dhokli, Undhiyu, Kadhi, Rotli & Chutney Farsan",
        "lunch_cost": 400.0,
        "dinner_name": "Locho & Fafda Street Corner",
        "dinner_specialty": "Locho, Dabeli, Fafda-Jalebi & Aam Ras",
        "dinner_cost": 300.0,
        "currency_note": "",
    },
    # Andhra / Telangana / Hyderabad
    "andhra": {
        "lunch_name": "Chutneys / Rayalaseema Ruchulu",
        "lunch_type": "Andhra Meals on Banana Leaf",
        "lunch_specialty": "Pesarattu, Pappu Chaaru, Gongura Pickle & Rice",
        "lunch_cost": 350.0,
        "dinner_name": "Shadab / Paradise Biryani",
        "dinner_specialty": "Hyderabadi Dum Biryani, Haleem & Double Ka Meetha",
        "dinner_cost": 500.0,
        "currency_note": "",
    },
    # Punjab / Amritsar / Chandigarh
    "punjab": {
        "lunch_name": "Kesar Da Dhaba / Bharawan Da Dhaba",
        "lunch_type": "Authentic Punjabi Dhaba Lunch",
        "lunch_specialty": "Makki di Roti, Sarson da Saag, Dal Makhani & Lassi",
        "lunch_cost": 400.0,
        "dinner_name": "Dhaba Style Punjabi Courtyard",
        "dinner_specialty": "Amritsari Kulcha, Chole & Jalebi",
        "dinner_cost": 450.0,
        "currency_note": "",
    },
    # Kerala / Kochi / Thiruvananthapuram
    "kerala": {
        "lunch_name": "Paragon Restaurant / Kerala Meals",
        "lunch_type": "Kerala Sadya (Banana Leaf Meal)",
        "lunch_specialty": "Avial, Olan, Thoran, Fish Curry, Rice & Payasam",
        "lunch_cost": 350.0,
        "dinner_name": "Seafood Shack / Toddy Shop",
        "dinner_specialty": "Karimeen Pollichathu, Appam & Stew",
        "dinner_cost": 550.0,
        "currency_note": "",
    },
    # Goa
    "goa": {
        "lunch_name": "Beach Shack / Venite / Souza Lobo",
        "lunch_type": "Goan-Portuguese Seafood Lunch",
        "lunch_specialty": "Fish Curry Rice, Prawn Balchao, Bebinca & Feni",
        "lunch_cost": 700.0,
        "dinner_name": "Beachside Sunset Shack",
        "dinner_specialty": "Whole Fish Tandoor, Kingfish Recheado & Coconut Sorbet",
        "dinner_cost": 900.0,
        "currency_note": "",
    },
    # Japan
    "japan": {
        "lunch_name": "Ramen-ya / Yoshinoya / Local Teishoku Set",
        "lunch_type": "Japanese Set Lunch (Teishoku)",
        "lunch_specialty": "Ramen, Gyoza, Katsu Curry, Miso Soup & Pickles",
        "lunch_cost": 1200.0,
        "dinner_name": "Izakaya / Sushi Bar",
        "dinner_specialty": "Omakase Sushi, Yakitori Skewers & Sake",
        "dinner_cost": 3000.0,
        "currency_note": "(JPY)",
    },
    # France
    "france": {
        "lunch_name": "Brasserie / Café de Flore",
        "lunch_type": "Classic French Brasserie Lunch",
        "lunch_specialty": "Croque Monsieur, French Onion Soup, Crème Brûlée & Bordeaux",
        "lunch_cost": 25.0,
        "dinner_name": "Bistro Parisien",
        "dinner_specialty": "Boeuf Bourguignon, Coq au Vin & Tarte Tatin",
        "dinner_cost": 45.0,
        "currency_note": "(EUR)",
    },
    # Italy
    "italy": {
        "lunch_name": "Trattoria / Local Osteria",
        "lunch_type": "Italian Trattoria Lunch",
        "lunch_specialty": "Pasta Cacio e Pepe, Bruschetta, Tiramisu & House Chianti",
        "lunch_cost": 20.0,
        "dinner_name": "Ristorante Locale",
        "dinner_specialty": "Risotto, Osso Buco, Gelato & Espresso",
        "dinner_cost": 40.0,
        "currency_note": "(EUR)",
    },
    # Spain
    "spain": {
        "lunch_name": "Tapas Bar / Mercado Central",
        "lunch_type": "Spanish Tapas & Pintxos Lunch",
        "lunch_specialty": "Patatas Bravas, Gambas al Ajillo, Gazpacho & Sangria",
        "lunch_cost": 18.0,
        "dinner_name": "Restaurante Español",
        "dinner_specialty": "Paella Valenciana, Churros con Chocolate & Rioja Wine",
        "dinner_cost": 35.0,
        "currency_note": "(EUR)",
    },
    # Germany
    "germany": {
        "lunch_name": "Biergarten / Markthalle",
        "lunch_type": "German Biergarten Lunch",
        "lunch_specialty": "Bratwurst, Pretzels, Sauerbraten & Weissbier",
        "lunch_cost": 18.0,
        "dinner_name": "Traditional Gasthaus",
        "dinner_specialty": "Schweinshaxe, Schnitzel, Red Cabbage & Dunkel Bier",
        "dinner_cost": 30.0,
        "currency_note": "(EUR)",
    },
    # Thailand
    "thailand": {
        "lunch_name": "Street Food Market / Or Tor Kor Market",
        "lunch_type": "Thai Street Food Lunch",
        "lunch_specialty": "Pad Thai, Som Tum, Tom Yum Soup & Mango Sticky Rice",
        "lunch_cost": 200.0,
        "dinner_name": "Night Market / Riverside Restaurant",
        "dinner_specialty": "Green Curry, Massaman Lamb & Coconut Ice Cream",
        "dinner_cost": 400.0,
        "currency_note": "(THB)",
    },
    # UAE / Dubai
    "uae": {
        "lunch_name": "Al Mallah / Sheikh Mohammed Centre",
        "lunch_type": "Arabic-Lebanese Lunch",
        "lunch_specialty": "Shawarma, Hummus, Fattoush Salad & Mint Lemonade",
        "lunch_cost": 60.0,
        "dinner_name": "Rooftop Arabic Restaurant",
        "dinner_specialty": "Lamb Ouzi, Arabic Mezze, Baklava & Karak Tea",
        "dinner_cost": 180.0,
        "currency_note": "(AED)",
    },
    # Turkey
    "turkey": {
        "lunch_name": "Lokantas / Meyhane",
        "lunch_type": "Turkish Meyhane Lunch",
        "lunch_specialty": "Döner Kebab, Mercimek Çorbası, Baklava & Ayran",
        "lunch_cost": 250.0,
        "dinner_name": "Rooftop Bosphorus Restaurant",
        "dinner_specialty": "Lamb Iskender, Turkish Meze, Raki & Kunefe",
        "dinner_cost": 600.0,
        "currency_note": "(TRY)",
    },
    # China
    "china": {
        "lunch_name": "Local Noodle Shop / Din Tai Fung",
        "lunch_type": "Chinese Regional Lunch",
        "lunch_specialty": "Xiaolongbao (Soup Dumplings), Beef Noodles & Mapo Tofu",
        "lunch_cost": 80.0,
        "dinner_name": "Hotpot Restaurant",
        "dinner_specialty": "Sichuan Mala Hotpot, Peking Duck & Jasmine Tea",
        "dinner_cost": 200.0,
        "currency_note": "(CNY)",
    },
    # South Korea
    "korea": {
        "lunch_name": "Gwangjang Market / Myeongdong Food Stalls",
        "lunch_type": "Korean Street Food Lunch",
        "lunch_specialty": "Bibimbap, Tteokbokki, Sundubu Jjigae & Makgeolli",
        "lunch_cost": 15000.0,
        "dinner_name": "Korean BBQ Restaurant",
        "dinner_specialty": "Samgyeopsal (Grilled Pork Belly), Kimchi Jjigae & Soju",
        "dinner_cost": 35000.0,
        "currency_note": "(KRW)",
    },
    # USA
    "usa": {
        "lunch_name": "Local Food Hall / Deli",
        "lunch_type": "American Casual Lunch",
        "lunch_specialty": "Gourmet Burger, Clam Chowder or BBQ Brisket & Iced Tea",
        "lunch_cost": 18.0,
        "dinner_name": "American Bistro / Steakhouse",
        "dinner_specialty": "New York Strip, Mac & Cheese, NY Cheesecake & Craft Beer",
        "dinner_cost": 45.0,
        "currency_note": "(USD)",
    },
    # UK
    "uk": {
        "lunch_name": "Traditional Pub / Borough Market",
        "lunch_type": "British Pub Lunch",
        "lunch_specialty": "Fish & Chips, Ploughman's Lunch, Scotch Egg & Ale",
        "lunch_cost": 15.0,
        "dinner_name": "Modern British Restaurant",
        "dinner_specialty": "Sunday Roast, Beef Wellington, Sticky Toffee Pudding & Claret",
        "dinner_cost": 40.0,
        "currency_note": "(GBP)",
    },
    # Australia
    "australia": {
        "lunch_name": "Café / Brunch Spot",
        "lunch_type": "Australian Café Brunch",
        "lunch_specialty": "Avocado Toast, Flat White, Meat Pie & Tim Tams",
        "lunch_cost": 22.0,
        "dinner_name": "Seafood Restaurant / BBQ",
        "dinner_specialty": "Barramundi, Prawns on the Barbie, Pavlova & Shiraz",
        "dinner_cost": 55.0,
        "currency_note": "(AUD)",
    },
    # Singapore
    "singapore": {
        "lunch_name": "Hawker Centre (Maxwell / Lau Pa Sat)",
        "lunch_type": "Singaporean Hawker Food",
        "lunch_specialty": "Hainanese Chicken Rice, Laksa, Char Kway Teow & Teh Tarik",
        "lunch_cost": 8.0,
        "dinner_name": "Singapore Seafood Restaurant",
        "dinner_specialty": "Chili Crab, Black Pepper Crab, Fried Hokkien Mee & Tiger Beer",
        "dinner_cost": 60.0,
        "currency_note": "(SGD)",
    },
    # Greece
    "greece": {
        "lunch_name": "Taverna / Ouzeri",
        "lunch_type": "Greek Mezze Lunch",
        "lunch_specialty": "Tzatziki, Spanakopita, Grilled Octopus & Ouzo",
        "lunch_cost": 18.0,
        "dinner_name": "Seaside Taverna",
        "dinner_specialty": "Moussaka, Fresh Seabass, Loukoumades & Assyrtiko Wine",
        "dinner_cost": 35.0,
        "currency_note": "(EUR)",
    },
    # Portugal
    "portugal": {
        "lunch_name": "Tasca / Mercado da Ribeira",
        "lunch_type": "Portuguese Tasca Lunch",
        "lunch_specialty": "Bacalhau (Salted Cod), Bifanas, Pastéis de Nata & Vinho Verde",
        "lunch_cost": 15.0,
        "dinner_name": "Fado Restaurant",
        "dinner_specialty": "Caldo Verde, Grilled Sardines, Arroz de Pato & Port Wine",
        "dinner_cost": 35.0,
        "currency_note": "(EUR)",
    },
    # Vietnam
    "vietnam": {
        "lunch_name": "Pho Bo Restaurant / Bánh Mì Stall",
        "lunch_type": "Vietnamese Street Food Lunch",
        "lunch_specialty": "Phở Bò, Bánh Mì, Gỏi Cuốn & Cà Phê Đá",
        "lunch_cost": 80000.0,
        "dinner_name": "Vietnamese Restaurant / Night Market",
        "dinner_specialty": "Bún Chả, Cơm Tấm, Chả Giò & Bia Hơi",
        "dinner_cost": 150000.0,
        "currency_note": "(VND)",
    },
    # Indonesia / Bali
    "indonesia": {
        "lunch_name": "Warung Makan / Nasi Padang",
        "lunch_type": "Indonesian Warung Lunch",
        "lunch_specialty": "Nasi Goreng, Rendang, Gado-Gado & Es Teh Manis",
        "lunch_cost": 50000.0,
        "dinner_name": "Bali Sunset Restaurant",
        "dinner_specialty": "Babi Guling, Bebek Betutu, Tempeh & Bintang Beer",
        "dinner_cost": 120000.0,
        "currency_note": "(IDR)",
    },
    # Nepal
    "nepal": {
        "lunch_name": "Local Dal Bhat House",
        "lunch_type": "Nepali Dal Bhat Lunch",
        "lunch_specialty": "Dal Bhat (Lentil Rice), Achar, Gundruk Soup & Chai",
        "lunch_cost": 500.0,
        "dinner_name": "Thamel Restaurant",
        "dinner_specialty": "Momos, Thukpa Noodle Soup & Tongba Millet Beer",
        "dinner_cost": 800.0,
        "currency_note": "(NPR)",
    },
    # Sri Lanka
    "srilanka": {
        "lunch_name": "Local Rice & Curry House",
        "lunch_type": "Sri Lankan Rice & Curry Lunch",
        "lunch_specialty": "Rice & Curry with Dhal, Coconut Sambol & Hoppers",
        "lunch_cost": 1200.0,
        "dinner_name": "Seafood Restaurant / Kottu Stall",
        "dinner_specialty": "Kottu Roti, Crab Curry, String Hoppers & King Coconut",
        "dinner_cost": 2500.0,
        "currency_note": "(LKR)",
    },
}

# City → cuisine region key
_CITY_CUISINE_MAP: Dict[str, str] = {}
for _c in {"jaipur", "agra", "delhi", "varanasi", "lucknow", "kanpur",
           "bhopal", "indore", "mathura", "vrindavan", "gwalior"}:
    _CITY_CUISINE_MAP[_c] = "rajasthan"
for _c in {"mumbai", "pune", "nagpur", "nashik", "aurangabad",
           "kolhapur", "amravati", "nanded", "solapur"}:
    _CITY_CUISINE_MAP[_c] = "maharashtra"
for _c in {"chennai", "coimbatore", "madurai", "trichy", "salem",
           "tirunelveli", "thanjavur", "vellore"}:
    _CITY_CUISINE_MAP[_c] = "tamil_nadu"
for _c in {"bengaluru", "bangalore", "mysuru", "mysore", "hubli",
           "dharwad", "mangalore", "belagavi"}:
    _CITY_CUISINE_MAP[_c] = "karnataka"
for _c in {"kolkata", "howrah", "durgapur", "siliguri", "asansol"}:
    _CITY_CUISINE_MAP[_c] = "bengal"
for _c in {"ahmedabad", "surat", "vadodara", "rajkot", "gandhinagar", "bhavnagar"}:
    _CITY_CUISINE_MAP[_c] = "gujarat"
for _c in {"hyderabad", "secunderabad", "visakhapatnam", "vijayawada",
           "tirupati", "guntur", "warangal"}:
    _CITY_CUISINE_MAP[_c] = "andhra"
for _c in {"amritsar", "ludhiana", "jalandhar", "patiala", "chandigarh"}:
    _CITY_CUISINE_MAP[_c] = "punjab"
for _c in {"thiruvananthapuram", "kochi", "kozhikode", "thrissur",
           "kollam", "calicut", "trivandrum", "alappuzha", "munnar"}:
    _CITY_CUISINE_MAP[_c] = "kerala"
for _c in {"goa", "panaji", "panjim", "margao", "vasco", "calangute", "anjuna"}:
    _CITY_CUISINE_MAP[_c] = "goa"
# International
for _c in {"tokyo", "kyoto", "osaka", "hiroshima", "nara", "sapporo",
           "nagoya", "yokohama", "fukuoka", "kobe", "kamakura"}:
    _CITY_CUISINE_MAP[_c] = "japan"
for _c in {"paris", "lyon", "marseille", "bordeaux", "nice", "toulouse",
           "strasbourg", "nantes", "versailles"}:
    _CITY_CUISINE_MAP[_c] = "france"
for _c in {"rome", "florence", "venice", "milan", "naples", "turin",
           "bologna", "amalfi", "siena", "pisa"}:
    _CITY_CUISINE_MAP[_c] = "italy"
for _c in {"madrid", "barcelona", "seville", "granada", "toledo",
           "cordoba", "valencia", "bilbao"}:
    _CITY_CUISINE_MAP[_c] = "spain"
for _c in {"berlin", "munich", "hamburg", "frankfurt", "cologne",
           "heidelberg", "nuremberg", "dresden"}:
    _CITY_CUISINE_MAP[_c] = "germany"
for _c in {"bangkok", "chiang mai", "phuket", "pattaya", "ayutthaya",
           "koh samui", "krabi", "hua hin"}:
    _CITY_CUISINE_MAP[_c] = "thailand"
for _c in {"dubai", "abu dhabi", "doha", "muscat", "cairo", "marrakech",
           "petra", "amman", "riyadh"}:
    _CITY_CUISINE_MAP[_c] = "uae"
for _c in {"istanbul", "ankara", "cappadocia", "antalya", "bodrum",
           "izmir", "pamukkale"}:
    _CITY_CUISINE_MAP[_c] = "turkey"
for _c in {"beijing", "shanghai", "xian", "xi'an", "chengdu", "guangzhou",
           "hangzhou", "guilin", "lijiang"}:
    _CITY_CUISINE_MAP[_c] = "china"
for _c in {"seoul", "busan", "jeju", "incheon", "gyeongju"}:
    _CITY_CUISINE_MAP[_c] = "korea"
for _c in {"new york", "los angeles", "chicago", "miami", "san francisco",
           "las vegas", "washington", "boston", "new orleans", "seattle",
           "honolulu", "nashville", "orlando"}:
    _CITY_CUISINE_MAP[_c] = "usa"
for _c in {"london", "edinburgh", "oxford", "cambridge", "bath", "york",
           "manchester", "liverpool", "bristol"}:
    _CITY_CUISINE_MAP[_c] = "uk"
for _c in {"sydney", "melbourne", "brisbane", "perth", "cairns",
           "adelaide", "gold coast"}:
    _CITY_CUISINE_MAP[_c] = "australia"
for _c in {"singapore"}:
    _CITY_CUISINE_MAP[_c] = "singapore"
for _c in {"athens", "santorini", "mykonos", "thessaloniki", "meteora",
           "crete", "rhodes"}:
    _CITY_CUISINE_MAP[_c] = "greece"
for _c in {"lisbon", "porto", "sintra", "algarve"}:
    _CITY_CUISINE_MAP[_c] = "portugal"
for _c in {"hanoi", "ho chi minh", "hoi an", "hue", "da nang", "halong", "sapa"}:
    _CITY_CUISINE_MAP[_c] = "vietnam"
for _c in {"bali", "jakarta", "yogyakarta", "ubud", "lombok"}:
    _CITY_CUISINE_MAP[_c] = "indonesia"
for _c in {"kathmandu", "pokhara", "bhaktapur", "lalitpur", "chitwan"}:
    _CITY_CUISINE_MAP[_c] = "nepal"
for _c in {"colombo", "kandy", "galle", "sigiriya", "ella", "trincomalee"}:
    _CITY_CUISINE_MAP[_c] = "srilanka"


def get_cuisine_profile(destination: str) -> Dict[str, Any]:
    """Returns cuisine data for the destination, falling back to generic India profile."""
    dest_key = destination.lower().strip()
    cuisine_key = _CITY_CUISINE_MAP.get(dest_key, "india")
    return _CUISINE_PROFILES.get(cuisine_key, _CUISINE_PROFILES["india"])


# ---------------------------------------------------------------------------
# Main itinerary builder
# ---------------------------------------------------------------------------

def build_day_plan(
    day_number: int,
    theme: str,
    sights: List[Attraction],
    weather_info: Dict[str, Any],
    profile: TravelerProfile,
    is_rainy: bool = False
) -> DayPlan:
    """
    Builds a single day's time-slotted schedule with destination-authentic food pairing
    and transit calculations.
    """
    cuisine = get_cuisine_profile(profile.destination)
    slots: List[TimeSlot] = []
    total_km = 0.0
    day_cost = 0.0

    morning_sight = sights[0] if len(sights) > 0 else None
    afternoon_sight = sights[1] if len(sights) > 1 else None
    evening_sight = sights[2] if len(sights) > 2 else None

    # Determine regional transit context from coordinates
    is_south_asia = True
    ref_sight = morning_sight or afternoon_sight or evening_sight
    if ref_sight:
        if not (6.0 <= ref_sight.lat <= 38.0 and 68.0 <= ref_sight.lng <= 98.0):
            is_south_asia = False

    # Slot 1: Morning Anchor
    if morning_sight:
        crowd = "Low 🟢 (Early Arrival)" if "08:30" in morning_sight.best_time_to_visit else "Moderate 🟡"
        morning_mode = "Auto-Rickshaw 🛺" if is_south_asia else "Metro / City Tram 🚊"
        slots.append(TimeSlot(
            slot_type="Morning",
            start_time="09:00",
            end_time="12:00",
            attraction=morning_sight,
            activity_name=morning_sight.name,
            notes=f"{morning_sight.description[:110]}... Best: {morning_sight.best_time_to_visit}",
            cost=morning_sight.entry_fee,
            transit_mins=15,
            distance_km=2.5,
            transit_mode=morning_mode,
            estimated_fare=50.0,
            co2_kg=0.16,
            applied_skill_badge="Crowd Avoidance 🕒",
            crowd_forecast=crowd
        ))
        total_km += 2.5
        day_cost += morning_sight.entry_fee

    # Slot 2: Lunch (destination-authentic cuisine)
    # Check if we have a specific curated food stop for this sight, else use destination cuisine
    specific_stop = LOCAL_FOOD_STOPS.get(morning_sight.id if morning_sight else "", None)
    if specific_stop:
        lunch_name = specific_stop["name"]
        lunch_type = specific_stop["type"]
        lunch_specialty = specific_stop["specialty"]
        lunch_distance_m = specific_stop["distance_m"]
        lunch_cost = specific_stop["cost_per_person"]
    else:
        lunch_name = cuisine["lunch_name"]
        lunch_type = cuisine["lunch_type"]
        lunch_specialty = cuisine["lunch_specialty"]
        lunch_distance_m = 300
        lunch_cost = cuisine["lunch_cost"]

    slots.append(TimeSlot(
        slot_type="Lunch",
        start_time="12:30",
        end_time="14:00",
        activity_name=f"🍽️ Lunch: {lunch_name}",
        notes=f"{lunch_type} | Specialty: {lunch_specialty} (Located {lunch_distance_m}m from morning sight)",
        cost=lunch_cost,
        transit_mins=5,
        distance_km=round(lunch_distance_m / 1000.0, 2),
        transit_mode="Walking 🚶",
        estimated_fare=0.0,
        co2_kg=0.0,
        applied_skill_badge="Food Discovery 🍜",
        crowd_forecast="Moderate 🟡"
    ))
    day_cost += lunch_cost

    # Slot 3: Afternoon Sight
    if afternoon_sight:
        dist_from_morning = haversine_distance_km(
            morning_sight.lat, morning_sight.lng,
            afternoon_sight.lat, afternoon_sight.lng
        ) if morning_sight else 3.0

        transit_info = estimate_transit_leg(dist_from_morning, is_south_asia=is_south_asia)
        total_km += dist_from_morning
        day_cost += afternoon_sight.entry_fee

        crowd = "Low 🟢" if afternoon_sight.is_indoor else "Moderate 🟡"

        slots.append(TimeSlot(
            slot_type="Afternoon",
            start_time="14:30",
            end_time="17:00",
            attraction=afternoon_sight,
            activity_name=afternoon_sight.name,
            notes=f"{afternoon_sight.description[:110]}...",
            cost=afternoon_sight.entry_fee,
            transit_mins=transit_info["transit_mins"],
            distance_km=round(dist_from_morning, 2),
            transit_mode=transit_info["mode"],
            estimated_fare=transit_info["estimated_fare"],
            co2_kg=transit_info["co2_kg"],
            applied_skill_badge="Indoor Weather Shield 🛡️" if is_rainy and afternoon_sight.is_indoor else "Route Optimized 🗺️",
            crowd_forecast=crowd
        ))

    # Slot 4: Evening / Sunset / Bazaar
    if evening_sight:
        ref_lat = afternoon_sight.lat if afternoon_sight else (morning_sight.lat if morning_sight else 0)
        ref_lng = afternoon_sight.lng if afternoon_sight else (morning_sight.lng if morning_sight else 0)
        dist_evening = haversine_distance_km(ref_lat, ref_lng, evening_sight.lat, evening_sight.lng)
        transit_info = estimate_transit_leg(dist_evening, is_south_asia=is_south_asia)
        total_km += dist_evening
        day_cost += evening_sight.entry_fee

        slots.append(TimeSlot(
            slot_type="Evening",
            start_time="17:30",
            end_time="19:30",
            attraction=evening_sight,
            activity_name=evening_sight.name,
            notes=f"Golden hour stroll & photography. {evening_sight.description[:100]}...",
            cost=evening_sight.entry_fee,
            transit_mins=transit_info["transit_mins"],
            distance_km=round(dist_evening, 2),
            transit_mode=transit_info["mode"],
            estimated_fare=transit_info["estimated_fare"],
            co2_kg=transit_info["co2_kg"],
            applied_skill_badge="Golden Hour Sunset 🌅",
            crowd_forecast="Moderate 🟡"
        ))

    # Slot 5: Dinner (destination-authentic)
    currency_note = cuisine.get("currency_note", "")
    dinner_label = f"{cuisine['dinner_name']}"
    dinner_note = f"Relaxed dinner with {cuisine['dinner_specialty']}."

    slots.append(TimeSlot(
        slot_type="Dinner",
        start_time="19:30",
        end_time="21:00",
        activity_name=f"🍲 Dinner: {dinner_label}",
        notes=dinner_note,
        cost=cuisine["dinner_cost"],
        transit_mins=10,
        distance_km=1.2,
        transit_mode="Walking 🚶",
        estimated_fare=0.0,
        co2_kg=0.0,
        applied_skill_badge="Family Pacing 👨‍👩‍👧‍👦",
        crowd_forecast="Moderate 🟡"
    ))
    day_cost += cuisine["dinner_cost"]

    return DayPlan(
        day_number=day_number,
        date_str=weather_info.get("date", f"Day {day_number}"),
        theme=theme,
        weather_summary=weather_info.get("summary", "Sunny, 28°C"),
        rain_probability=weather_info.get("rain_probability", 10),
        max_temp_c=weather_info.get("max_temp_c", 28.0),
        time_slots=slots,
        day_cost=day_cost,
        total_travel_km=round(total_km, 1),
        transit_summary=f"{total_km:.1f} km transit | Efficient geographic clustering"
    )
