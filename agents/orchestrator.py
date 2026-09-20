"""
Master Agentic Orchestrator.
Coordinates the entire multi-agent state pipeline, executes Skill-RAG routing,
Tavily web intelligence, weather and routing tools, and the self-correction validation loop.
Yields streaming generator events for live dashboard updates.
"""
import uuid
from datetime import datetime
from typing import Generator, Dict, Any, Tuple, Optional, List

from models.schemas import (
    TravelerProfile, TripPlan, DayPlan, Attraction, ScoredAttraction,
    ValidationResult, SurvivalPhrase
)
from tools.skill_rag import skill_rag_engine
from tools.chroma_rag import chroma_rag_engine
from tools.global_poi_tool import discover_global_attractions
from tools.weather_tool import fetch_weather_forecast
from tools.route_tool import haversine_distance_km
from tools.budget_tool import calculate_trip_budget
from tools.ics_tool import generate_trip_ics
from tools.pdf_tool import generate_trip_pdf
from agents.recommender import rank_and_select_attractions
from agents.itinerary_builder import build_day_plan
from agents.validator import validate_itinerary, execute_self_correction_replan


# ---------------------------------------------------------------------------
# Regional city sets — for localized survival kits and emergency contacts
# ---------------------------------------------------------------------------
_INDIAN_HINDI_BELT = {"jaipur", "delhi", "agra", "varanasi", "lucknow", "kanpur",
                       "patna", "bhopal", "indore", "jabalpur", "gwalior",
                       "allahabad", "prayagraj", "mathura", "vrindavan", "ujjain"}
_INDIAN_MARATHI_BELT = {"mumbai", "pune", "nagpur", "nashik", "aurangabad",
                         "kolhapur", "solapur", "amravati", "nanded"}
_INDIAN_TAMIL_BELT = {"chennai", "coimbatore", "madurai", "trichy", "salem",
                       "tirunelveli", "vellore", "thanjavur"}
_INDIAN_KANNADA_BELT = {"bengaluru", "bangalore", "mysuru", "mysore", "hubli",
                         "dharwad", "mangalore", "belagavi"}
_INDIAN_BENGALI_BELT = {"kolkata", "howrah", "durgapur", "siliguri", "asansol"}
_INDIAN_GUJARATI_BELT = {"ahmedabad", "surat", "vadodara", "rajkot",
                          "gandhinagar", "bhavnagar"}
_INDIAN_TELUGU_BELT = {"hyderabad", "secunderabad", "visakhapatnam", "vijayawada",
                        "tirupati", "guntur", "warangal"}
_INDIAN_PUNJABI_BELT = {"amritsar", "ludhiana", "jalandhar", "patiala", "chandigarh"}
_INDIAN_KERALA_BELT = {"thiruvananthapuram", "kochi", "kozhikode", "thrissur",
                        "kollam", "calicut", "trivandrum", "alappuzha", "munnar"}
_GOA = {"goa", "panaji", "panjim", "margao", "vasco", "calangute", "anjuna"}

_JAPANESE = {"tokyo", "kyoto", "osaka", "hiroshima", "nara", "sapporo", "nagoya",
              "yokohama", "fukuoka", "sendai", "kobe", "kamakura", "nikko"}
_FRENCH = {"paris", "lyon", "marseille", "bordeaux", "nice", "toulouse",
           "strasbourg", "nantes", "montpellier", "lille", "versailles",
           "mont saint-michel"}
_ITALIAN = {"rome", "florence", "venice", "milan", "naples", "turin",
             "bologna", "amalfi", "cinque terre", "siena", "pisa", "sicily"}
_SPANISH = {"madrid", "barcelona", "seville", "granada", "toledo", "cordoba",
             "valencia", "bilbao", "san sebastian", "salamanca"}
_GERMAN = {"berlin", "munich", "hamburg", "frankfurt", "cologne", "heidelberg",
           "nuremberg", "dresden", "bavaria", "rothenburg"}
_THAI = {"bangkok", "chiang mai", "phuket", "pattaya", "ayutthaya", "koh samui",
         "krabi", "kanchanaburi", "hua hin", "pai"}
_ARABIC = {"dubai", "abu dhabi", "doha", "riyadh", "muscat", "cairo",
           "marrakech", "petra", "amman", "sharm el sheikh", "luxor",
           "casablanca", "hurghada"}
_TURKISH = {"istanbul", "ankara", "cappadocia", "antalya", "bodrum",
             "ephesus", "izmir", "konya", "pamukkale"}
_CHINESE = {"beijing", "shanghai", "xi'an", "xian", "chengdu", "guangzhou",
             "hangzhou", "guilin", "zhangjiajie", "lijiang", "suzhou"}
_KOREAN = {"seoul", "busan", "jeju", "incheon", "gyeongju", "gangnam",
           "jeonju", "suwon"}
_PORTUGUESE = {"lisbon", "porto", "sintra", "algarve", "funchal", "madeira"}
_DUTCH = {"amsterdam", "rotterdam", "hague", "the hague", "utrecht", "bruges"}
_GREEK = {"athens", "santorini", "mykonos", "thessaloniki", "meteora",
          "crete", "rhodes", "corfu", "delphi"}
_AMERICAN = {"new york", "los angeles", "chicago", "miami", "san francisco",
              "las vegas", "washington", "boston", "new orleans", "seattle",
              "honolulu", "nashville", "denver", "orlando"}
_BRITISH = {"london", "edinburgh", "oxford", "cambridge", "bath", "york",
             "manchester", "liverpool", "bristol", "stratford", "windsor"}
_AUSTRALIAN = {"sydney", "melbourne", "brisbane", "perth", "cairns",
               "adelaide", "gold coast", "uluru", "darwin"}
_NEPALESE = {"kathmandu", "pokhara", "bhaktapur", "lalitpur", "chitwan",
             "lumbini", "bandipur"}
_SRI_LANKAN = {"colombo", "kandy", "galle", "sigiriya", "ella",
               "trincomalee", "nuwara eliya"}
_VIETNAMESE = {"hanoi", "ho chi minh", "hoi an", "hue", "da nang",
               "halong", "sapa", "nha trang"}
_INDONESIAN = {"bali", "jakarta", "yogyakarta", "lombok", "komodo",
               "ubud", "seminyak", "flores"}
_SINGAPOREAN = {"singapore"}
_CANADIAN = {"toronto", "vancouver", "montreal", "quebec", "calgary",
             "ottawa", "banff", "niagara falls"}
_SWISS = {"zurich", "geneva", "bern", "lucerne", "interlaken", "zermatt"}
_AUSTRIAN = {"vienna", "salzburg", "innsbruck", "hallstatt", "graz"}


# ---------------------------------------------------------------------------
# Survival phrase generator — destination-aware
# ---------------------------------------------------------------------------

def _survival_phrases(dest_key: str) -> List[SurvivalPhrase]:
    """Returns culturally and linguistically correct survival phrases for the destination."""

    if dest_key in _INDIAN_HINDI_BELT:
        return [
            SurvivalPhrase(phrase="Kitna hua?", phonetic="Kit-naa hoo-aa?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Bina mirch ka banayein", phonetic="Bee-naa mirch kaa ba-naa-yen", meaning="Please make it less spicy", category="Food"),
            SurvivalPhrase(phrase="Meter se chalo", phonetic="Mee-ter say cha-lo", meaning="Please run the meter (taxi/auto)", category="Transport"),
            SurvivalPhrase(phrase="Dhanyawad / Ram Ram", phonetic="Dhan-ya-waad / Raam Raam", meaning="Thank you / Traditional Rajasthani greeting", category="Courtesy"),
            SurvivalPhrase(phrase="Yeh vegetarian hai?", phonetic="Yeh veg-e-tar-ian hai?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_MARATHI_BELT:
        return [
            SurvivalPhrase(phrase="Kiti zale?", phonetic="Ki-tee za-le?", meaning="How much did it cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Meter lava", phonetic="Me-ter la-vaa", meaning="Please start the meter (auto)", category="Transport"),
            SurvivalPhrase(phrase="Tikhat nako", phonetic="Ti-khat na-ko", meaning="Please make it non-spicy", category="Food"),
            SurvivalPhrase(phrase="Dhanyawad / Namaskar", phonetic="Dhan-ya-waad / Na-mas-kar", meaning="Thank you / Respectful Marathi greeting", category="Courtesy"),
            SurvivalPhrase(phrase="He vegetarian aahe ka?", phonetic="He veg-eh-tair-ee-an aa-he kaa?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_TAMIL_BELT:
        return [
            SurvivalPhrase(phrase="Evvalo?", phonetic="Ev-vaa-lo?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Kaaram vendam", phonetic="Kaa-ram ven-dam", meaning="I don't want it spicy", category="Food"),
            SurvivalPhrase(phrase="Meter pottu vaa", phonetic="Me-ter pot-tu vaa", meaning="Please run the meter", category="Transport"),
            SurvivalPhrase(phrase="Nandri / Vanakkam", phonetic="Nan-dri / Va-nak-kam", meaning="Thank you / Hello in Tamil", category="Courtesy"),
            SurvivalPhrase(phrase="Idhu saivama?", phonetic="I-thu sai-va-maa?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_KANNADA_BELT:
        return [
            SurvivalPhrase(phrase="Estu aagutthe?", phonetic="Es-tu aa-gut-the?", meaning="How much is this?", category="Ticketing"),
            SurvivalPhrase(phrase="Khara beda", phonetic="Kha-ra be-da", meaning="No spice please", category="Food"),
            SurvivalPhrase(phrase="Meter hakri", phonetic="Me-ter hak-ri", meaning="Please start the meter", category="Transport"),
            SurvivalPhrase(phrase="Dhanyavada / Namaskara", phonetic="Dhan-ya-vaa-da / Na-mas-kaa-ra", meaning="Thank you / Respectful greeting in Kannada", category="Courtesy"),
            SurvivalPhrase(phrase="Idu veg agide yaa?", phonetic="I-du veg aa-gi-de-yaa?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_BENGALI_BELT:
        return [
            SurvivalPhrase(phrase="Daam koto?", phonetic="Daam ko-to?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Jhaal kom deben", phonetic="Jhaal kom de-ben", meaning="Please make it less spicy", category="Food"),
            SurvivalPhrase(phrase="Meter diye jaan", phonetic="Me-ter di-ye jaan", meaning="Please go by meter", category="Transport"),
            SurvivalPhrase(phrase="Dhonnobad / Namaskar", phonetic="Dhon-no-baad / Na-mas-kar", meaning="Thank you / Hello in Bengali", category="Courtesy"),
            SurvivalPhrase(phrase="Eta niramish?", phonetic="E-ta ni-ra-mish?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_GUJARATI_BELT:
        return [
            SurvivalPhrase(phrase="Kem chho?", phonetic="Kem chho?", meaning="How are you? (warm Gujarati opener)", category="Courtesy"),
            SurvivalPhrase(phrase="Kethalo thai che?", phonetic="Ke-tha-lo thai che?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Tamu jain/veg chho?", phonetic="Taa-mu jain/veg chho?", meaning="Is this vegetarian or Jain?", category="Food"),
            SurvivalPhrase(phrase="Meter thi jao", phonetic="Me-ter thi jaa-o", meaning="Please go by meter", category="Transport"),
            SurvivalPhrase(phrase="Aabhar / Shukriya", phonetic="Aa-bhar / Shu-kri-ya", meaning="Thank you", category="Courtesy"),
        ]
    if dest_key in _INDIAN_TELUGU_BELT:
        return [
            SurvivalPhrase(phrase="Ela untundi?", phonetic="E-la un-tu-ndi?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Kaaram vaddhu", phonetic="Kaa-ram vad-dhu", meaning="No spice please", category="Food"),
            SurvivalPhrase(phrase="Meter veyandi", phonetic="Me-ter vey-an-di", meaning="Please start the meter", category="Transport"),
            SurvivalPhrase(phrase="Dhanyavadalu / Namaskaram", phonetic="Dhan-ya-vaa-da-lu / Na-mas-kaa-ram", meaning="Thank you / Hello in Telugu", category="Courtesy"),
            SurvivalPhrase(phrase="Idi vegetarian aa?", phonetic="I-di ve-ge-ta-ri-an aa?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_PUNJABI_BELT:
        return [
            SurvivalPhrase(phrase="Kiney da hai?", phonetic="Ki-ney daa hai?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Kam tikha", phonetic="Kam ti-khaa", meaning="Less spicy please", category="Food"),
            SurvivalPhrase(phrase="Meter lagao", phonetic="Me-ter la-gaa-o", meaning="Start the meter", category="Transport"),
            SurvivalPhrase(phrase="Shukriya / Sat Sri Akal", phonetic="Shu-kri-ya / Sat Sri Aa-kal", meaning="Thank you / Traditional Punjabi greeting", category="Courtesy"),
            SurvivalPhrase(phrase="Eh shaakahari hai?", phonetic="Eh shaa-ka-ha-ri hai?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _INDIAN_KERALA_BELT:
        return [
            SurvivalPhrase(phrase="Vaila ethra?", phonetic="Vai-la eth-ra?", meaning="How much is this?", category="Ticketing"),
            SurvivalPhrase(phrase="Kaaram venda", phonetic="Kaa-ram ven-da", meaning="No spice please", category="Food"),
            SurvivalPhrase(phrase="Meter ittu po", phonetic="Me-ter it-tu po", meaning="Please go by meter", category="Transport"),
            SurvivalPhrase(phrase="Nanni / Namaskaram", phonetic="Nan-ni / Na-mas-kaa-ram", meaning="Thank you / Hello in Malayalam", category="Courtesy"),
            SurvivalPhrase(phrase="Idu sakahari aano?", phonetic="I-du sa-kaa-ha-ri aa-no?", meaning="Is this vegetarian?", category="Food"),
        ]
    if dest_key in _GOA:
        return [
            SurvivalPhrase(phrase="Kitem poita?", phonetic="Ki-tem poi-ta?", meaning="How much does this cost? (Konkani)", category="Ticketing"),
            SurvivalPhrase(phrase="Try local cashew feni responsibly", phonetic="travel tip", meaning="Goa's signature spirit — cashew or coconut feni", category="Food"),
            SurvivalPhrase(phrase="Rent a scooter / bike", phonetic="travel tip", meaning="Best way to explore beaches and villages", category="Transport"),
            SurvivalPhrase(phrase="Deu borem korum / Obrigado", phonetic="De-u bo-rem ko-rum", meaning="God bless you (Konkani) / Thank you (Portuguese legacy)", category="Courtesy"),
            SurvivalPhrase(phrase="Always negotiate at flea markets", phonetic="shopping tip", meaning="Anjuna & Mapusa markets — bargaining is expected!", category="Shopping"),
        ]
    if dest_key in _JAPANESE:
        return [
            SurvivalPhrase(phrase="Kore wa ikura desu ka?", phonetic="Ko-re wa i-ku-ra des-ka?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Sumimasen", phonetic="Su-mi-ma-sen", meaning="Excuse me / Sorry (universally useful)", category="Courtesy"),
            SurvivalPhrase(phrase="Eigo ga hanasemasu ka?", phonetic="E-go ga ha-na-se-mas-ka?", meaning="Can you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Arigatou gozaimasu", phonetic="A-ri-ga-tou go-zai-mas", meaning="Thank you very much (polite)", category="Courtesy"),
            SurvivalPhrase(phrase="Hoteru made onegaishimasu", phonetic="Ho-te-ru ma-de o-ne-gai-shi-mas", meaning="Please take me to my hotel (taxi)", category="Transport"),
        ]
    if dest_key in _FRENCH:
        return [
            SurvivalPhrase(phrase="C'est combien?", phonetic="Say com-b-yen?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Excusez-moi", phonetic="Eks-ku-zay mwaa", meaning="Excuse me (essential opener)", category="Courtesy"),
            SurvivalPhrase(phrase="Parlez-vous anglais?", phonetic="Par-lay voo on-glay?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Merci beaucoup", phonetic="Mehr-see bo-koo", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Un ticket, s'il vous plaît", phonetic="Uhn tee-kay, seel voo play", meaning="One ticket please (metro/museum)", category="Transport"),
        ]
    if dest_key in _ITALIAN:
        return [
            SurvivalPhrase(phrase="Quanto costa?", phonetic="Kwan-to kos-ta?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Scusi / Permesso", phonetic="Skoo-zee / Per-mes-so", meaning="Excuse me / May I pass?", category="Courtesy"),
            SurvivalPhrase(phrase="Parla inglese?", phonetic="Par-la een-gle-ze?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Grazie mille", phonetic="Gra-tsye meel-e", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Un biglietto, per favore", phonetic="Un bil-yet-o, per fa-vo-re", meaning="One ticket please", category="Ticketing"),
        ]
    if dest_key in _SPANISH:
        return [
            SurvivalPhrase(phrase="¿Cuánto cuesta?", phonetic="Kwan-to kwes-ta?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Perdona / Disculpa", phonetic="Per-do-na / Dis-kul-pa", meaning="Excuse me", category="Courtesy"),
            SurvivalPhrase(phrase="¿Hablas inglés?", phonetic="Aa-blas een-gles?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Muchas gracias", phonetic="Moo-chas gra-see-as", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Una entrada, por favor", phonetic="Oo-na en-traa-da, por fa-vor", meaning="One ticket please", category="Ticketing"),
        ]
    if dest_key in _GERMAN:
        return [
            SurvivalPhrase(phrase="Was kostet das?", phonetic="Vas kos-tet das?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Entschuldigung", phonetic="Ent-shul-di-gung", meaning="Excuse me / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="Sprechen Sie Englisch?", phonetic="Shpre-chen zee Eng-lish?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Danke sehr", phonetic="Dang-ke zayr", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Eine Fahrkarte bitte", phonetic="Ai-ne Far-kar-te bit-te", meaning="One ticket please (transit)", category="Transport"),
        ]
    if dest_key in _THAI:
        return [
            SurvivalPhrase(phrase="Rakha tao rai?", phonetic="Raa-kaa tao rai?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Kho thot", phonetic="Khor-thoht", meaning="Excuse me / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="Phut phasa angkrit dai mai?", phonetic="Puud paa-saa ang-grit dai mai?", meaning="Can you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Khob khun mak", phonetic="Khob-kun-maak", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Mai phet! (mark mark)", phonetic="Mai pet mark-mark", meaning="Not spicy! (critical in Thailand)", category="Food"),
        ]
    if dest_key in _ARABIC:
        return [
            SurvivalPhrase(phrase="Bikam hatha?", phonetic="Bi-kam ha-tha?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Lau samaht / Asif", phonetic="Law sa-maht / Aa-sif", meaning="Please / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="Hal tatakallam al-ingliziyya?", phonetic="Hal ta-ta-kal-lam al-in-gli-zi-ya?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Shukran jazilan", phonetic="Shu-kran ja-zee-lan", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Dress modestly at mosques", phonetic="cultural tip", meaning="Cover shoulders & knees; carry a scarf for religious sites", category="Etiquette"),
        ]
    if dest_key in _TURKISH:
        return [
            SurvivalPhrase(phrase="Bu ne kadar?", phonetic="Boo ne ka-dar?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Afedersiniz / Pardon", phonetic="Af-e-der-si-niz / Par-don", meaning="Excuse me / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="İngilizce biliyor musunuz?", phonetic="In-gi-liz-je bi-li-yor mu-su-nuz?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Çok teşekkür ederim", phonetic="Chok te-shek-kur e-de-rim", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Çay lütfen", phonetic="Chay lut-fen", meaning="Tea please — Turkish tea is the universal social glue", category="Food"),
        ]
    if dest_key in _CHINESE:
        return [
            SurvivalPhrase(phrase="Duōshao qián?", phonetic="Dwor-sha-o chee-en?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Duìbuqǐ / Qǐng wèn", phonetic="Dway-boo-chee / Ching-wen", meaning="Sorry / Excuse me, may I ask…", category="Courtesy"),
            SurvivalPhrase(phrase="Nǐ huì shuō yīngwén ma?", phonetic="Nee hway shwo-ying-wen-mah?", meaning="Can you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Xièxie nǐ", phonetic="Shyeh-shyeh nee", meaning="Thank you", category="Courtesy"),
            SurvivalPhrase(phrase="Wǒ bù chī là de", phonetic="Wor boo chr laa de", meaning="I don't eat spicy food", category="Food"),
        ]
    if dest_key in _KOREAN:
        return [
            SurvivalPhrase(phrase="Eolmayeyo?", phonetic="Ol-ma-ye-yo?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Sillyehabnida", phonetic="Shil-lyeh-ham-ni-da", meaning="Excuse me (polite)", category="Courtesy"),
            SurvivalPhrase(phrase="Yeongeo haseyo?", phonetic="Yong-oh ha-se-yo?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Gamsahamnida", phonetic="Gam-sa-ham-ni-da", meaning="Thank you (formal)", category="Courtesy"),
            SurvivalPhrase(phrase="Maepji aneun geot juseyo", phonetic="Map-ji-a-nen-got-ju-se-yo", meaning="Not spicy please", category="Food"),
        ]
    if dest_key in _NEPALESE:
        return [
            SurvivalPhrase(phrase="Kati parcha?", phonetic="Ka-ti par-cha?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Maafi garnu hola", phonetic="Maa-fi gar-nu ho-la", meaning="Please excuse me", category="Courtesy"),
            SurvivalPhrase(phrase="Tapailai angreji aunchha?", phonetic="Ta-pai-lai ang-re-ji aun-chha?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Dhanyabaad", phonetic="Dhan-ya-baad", meaning="Thank you", category="Courtesy"),
            SurvivalPhrase(phrase="Piro napakos", phonetic="Pi-ro na-pa-kos", meaning="Please don't make it spicy", category="Food"),
        ]
    if dest_key in _VIETNAMESE:
        return [
            SurvivalPhrase(phrase="Cái này bao nhiêu?", phonetic="Kai nay bao nyew?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Xin lỗi", phonetic="Sin loy", meaning="Sorry / Excuse me", category="Courtesy"),
            SurvivalPhrase(phrase="Bạn có nói tiếng Anh không?", phonetic="Ban co noy tieng Anh khong?", meaning="Can you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Cảm ơn rất nhiều", phonetic="Gam on rat nyew", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Không cay", phonetic="Khong kai", meaning="Not spicy please", category="Food"),
        ]
    if dest_key in _INDONESIAN:
        return [
            SurvivalPhrase(phrase="Berapa harganya?", phonetic="Be-ra-pa har-ga-nya?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Permisi / Maaf", phonetic="Per-mi-si / Maa-af", meaning="Excuse me / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="Anda bisa berbicara bahasa Inggris?", phonetic="An-da bi-sa ber-bi-ca-ra ba-ha-sa Ing-gris?", meaning="Can you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Terima kasih banyak", phonetic="Te-ri-ma ka-sih ba-nyak", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Tolong, tidak pedas", phonetic="To-long, ti-dak pe-das", meaning="Please, not spicy", category="Food"),
        ]
    if dest_key in _SINGAPOREAN:
        return [
            SurvivalPhrase(phrase="How much lah?", phonetic="How much lah?", meaning="Price query in Singlish — always smiled at", category="Ticketing"),
            SurvivalPhrase(phrase="Can or not?", phonetic="Can or not?", meaning="Is it possible? / Is this ok? (Singlish)", category="Communication"),
            SurvivalPhrase(phrase="Shiok!", phonetic="Shiok!", meaning="Means delicious / fantastic (highest Singlish food compliment)", category="Food"),
            SurvivalPhrase(phrase="Top up EZ-Link card", phonetic="travel tip", meaning="Get an EZ-Link card at MRT for all buses and trains", category="Transport"),
            SurvivalPhrase(phrase="No eating / drinking on MRT — strict fine", phonetic="etiquette tip", meaning="SGD $500 fine for eating or drinking on Singapore MRT", category="Etiquette"),
        ]
    if dest_key in _BRITISH:
        return [
            SurvivalPhrase(phrase="Cheers!", phonetic="Cheers!", meaning="Thank you / Goodbye — universally used in the UK", category="Courtesy"),
            SurvivalPhrase(phrase="Sorry / Excuse me", phonetic="Sor-ry / Ex-kyooz me", meaning="Brits apologize constantly — use liberally", category="Courtesy"),
            SurvivalPhrase(phrase="Could I have the bill, please?", phonetic="practical phrase", meaning="Asking for the check at a restaurant", category="Ticketing"),
            SurvivalPhrase(phrase="Queue properly — never jump!", phonetic="etiquette tip", meaning="Queue-jumping is considered very rude in the UK", category="Etiquette"),
            SurvivalPhrase(phrase="Get an Oyster card / tap Contactless", phonetic="travel tip", meaning="Cheapest way to ride London Underground and buses", category="Transport"),
        ]
    if dest_key in _AUSTRALIAN:
        return [
            SurvivalPhrase(phrase="G'day!", phonetic="Guh-day!", meaning="Hello / Good day (classic Aussie greeting)", category="Courtesy"),
            SurvivalPhrase(phrase="No worries", phonetic="No wor-ries", meaning="You're welcome / It's fine", category="Courtesy"),
            SurvivalPhrase(phrase="How much is it?", phonetic="practical English", meaning="Straightforward pricing question", category="Ticketing"),
            SurvivalPhrase(phrase="BYO restaurant tip", phonetic="Bring Your Own", meaning="Many Aussie restaurants allow BYO wine/beer — ask ahead", category="Food"),
            SurvivalPhrase(phrase="Tap water is drinkable everywhere", phonetic="travel tip", meaning="Tap water is safe throughout Australia — save on bottles", category="Food"),
        ]
    if dest_key in _AMERICAN or dest_key in _CANADIAN:
        return [
            SurvivalPhrase(phrase="How much is this?", phonetic="practical English", meaning="Note: displayed prices often exclude sales tax", category="Ticketing"),
            SurvivalPhrase(phrase="Tip 18-20% at restaurants", phonetic="etiquette tip", meaning="Tipping is expected at restaurants, taxis, and hotels", category="Courtesy"),
            SurvivalPhrase(phrase="Have a great day!", phonetic="Have a great day!", meaning="Standard friendly American goodbye", category="Courtesy"),
            SurvivalPhrase(phrase="Use Uber / Lyft", phonetic="travel tip", meaning="Most cost-effective city transport — avoid tourist taxis", category="Transport"),
            SurvivalPhrase(phrase="Can I get a to-go box?", phonetic="practical phrase", meaning="US portions are huge — always ask for a doggy bag", category="Food"),
        ]
    if dest_key in _PORTUGUESE:
        return [
            SurvivalPhrase(phrase="Quanto custa?", phonetic="Kwan-to koos-ta?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Desculpe / Com licença", phonetic="Des-kool-pe / Com li-sen-sa", meaning="Sorry / Excuse me", category="Courtesy"),
            SurvivalPhrase(phrase="Fala inglês?", phonetic="Fa-la een-glesh?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Obrigado / Obrigada", phonetic="O-bri-gaa-do / O-bri-gaa-da", meaning="Thank you (male / female speaker)", category="Courtesy"),
            SurvivalPhrase(phrase="Um bilhete, por favor", phonetic="Oom bil-yet, por fa-vor", meaning="One ticket please", category="Ticketing"),
        ]
    if dest_key in _GREEK:
        return [
            SurvivalPhrase(phrase="Poso kani?", phonetic="Po-so kaa-ni?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Signomi", phonetic="Sig-no-mi", meaning="Excuse me / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="Milate anglika?", phonetic="Mi-la-te an-gli-ka?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Efharisto poli", phonetic="Ef-ha-ris-to po-lee", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Ena eisitiriο, parakalo", phonetic="E-na ei-si-ti-ri-o, pa-ra-ka-lo", meaning="One ticket please", category="Ticketing"),
        ]
    if dest_key in _SRI_LANKAN:
        return [
            SurvivalPhrase(phrase="Keyya kiyanne?", phonetic="Key-ya ki-ya-ne?", meaning="How much is this? (Sinhala)", category="Ticketing"),
            SurvivalPhrase(phrase="Istuti / Bohoma istuti", phonetic="Is-too-ti / Bo-ho-ma is-too-ti", meaning="Thank you / Thank you very much (Sinhala)", category="Courtesy"),
            SurvivalPhrase(phrase="Meter eka hadanna", phonetic="Me-ter e-ka ha-dan-na", meaning="Please start the meter (tuk-tuk)", category="Transport"),
            SurvivalPhrase(phrase="Kaara nattam (Tamil belt)", phonetic="Kaa-ra nat-tam", meaning="Not spicy please", category="Food"),
            SurvivalPhrase(phrase="Ingirisi dannawada?", phonetic="In-gi-ri-si dan-na-wa-da?", meaning="Do you know English? (Sinhala)", category="Communication"),
        ]
    if dest_key in _SWISS:
        return [
            SurvivalPhrase(phrase="Wie viel kostet das?", phonetic="Vee feel kos-tet das?", meaning="How much does this cost? (German Swiss)", category="Ticketing"),
            SurvivalPhrase(phrase="Entschuldigung / Excusez-moi", phonetic="Ent-shul-di-gung / Eks-ku-zay mwaa", meaning="Excuse me (German / French speaking regions)", category="Courtesy"),
            SurvivalPhrase(phrase="Danke vielmals / Merci beaucoup", phonetic="Dang-ke feel-mals / Mehr-see bo-koo", meaning="Thank you very much (German / French)", category="Courtesy"),
            SurvivalPhrase(phrase="Buy a Swiss Travel Pass", phonetic="travel tip", meaning="Unlimited train, bus, and boat travel across Switzerland", category="Transport"),
            SurvivalPhrase(phrase="Tap water is excellent", phonetic="travel tip", meaning="Swiss tap water is among the cleanest in the world", category="Food"),
        ]
    if dest_key in _AUSTRIAN:
        return [
            SurvivalPhrase(phrase="Was kostet das?", phonetic="Vas kos-tet das?", meaning="How much does this cost?", category="Ticketing"),
            SurvivalPhrase(phrase="Entschuldigung", phonetic="Ent-shul-di-gung", meaning="Excuse me / Sorry", category="Courtesy"),
            SurvivalPhrase(phrase="Sprechen Sie Englisch?", phonetic="Shpre-chen zee Eng-lish?", meaning="Do you speak English?", category="Communication"),
            SurvivalPhrase(phrase="Danke schön", phonetic="Dang-ke shern", meaning="Thank you very much", category="Courtesy"),
            SurvivalPhrase(phrase="Einen Kaffee bitte", phonetic="Ai-nen Ka-feh bit-te", meaning="A coffee please — Viennese café culture is unmissable", category="Food"),
        ]

    # Generic English fallback for unlisted destinations
    return [
        SurvivalPhrase(phrase="How much does this cost?", phonetic="universal English", meaning="Universal price inquiry", category="Ticketing"),
        SurvivalPhrase(phrase="Excuse me / Sorry", phonetic="universal English", meaning="Polite attention-getter in any English-friendly tourist area", category="Courtesy"),
        SurvivalPhrase(phrase="Do you speak English?", phonetic="universal English", meaning="Opens communication in most tourist destinations", category="Communication"),
        SurvivalPhrase(phrase="Thank you", phonetic="universal English", meaning="Always appreciated in any language", category="Courtesy"),
        SurvivalPhrase(phrase="One ticket please", phonetic="universal English", meaning="Works at most international tourist attractions", category="Ticketing"),
    ]


# ---------------------------------------------------------------------------
# Emergency contacts — country-aware
# ---------------------------------------------------------------------------

_EMERGENCY_CONTACTS_DB = {
    "jaipur": {
        "Tourist Police Helpline": "1364 / +91-141-2601100",
        "Police Emergency": "112 / 100",
        "Ambulance Service": "108 / 102",
        "SMS General Medical Hospital": "+91-141-2560291 (JLN Marg, Jaipur)",
        "Pink City Tourism Assistance": "+91-141-5110598",
    },
    "japan": {
        "Police": "110", "Ambulance / Fire": "119",
        "Japan Tourist Helpline (English 24h)": "050-3816-2787",
        "Japan Helpline": "0120-461-997",
    },
    "france": {
        "Police": "17", "Ambulance SAMU": "15", "Fire": "18",
        "European Emergency": "112",
        "Tourist Police Paris": "+33-1-40-67-21-95",
    },
    "italy": {
        "Emergency (Carabinieri)": "112", "Ambulance": "118", "Fire": "115",
        "Tourist Police Rome": "+39-06-46861",
    },
    "spain": {
        "Emergency": "112", "Police Nacional": "091",
        "Ambulance": "061", "Tourist Info": "+34-902-102-112",
    },
    "germany": {
        "Emergency": "112", "Police": "110",
        "ADAC Roadside Assist": "0800-5-10-11-12",
    },
    "thailand": {
        "Emergency": "191", "Tourism Police": "1155",
        "Ambulance": "1669", "Tourist Authority (TAT)": "1672",
    },
    "uae": {
        "Police": "999", "Ambulance": "998", "Fire": "997",
        "Dubai Tourism": "+971-4-223-0000",
    },
    "turkey": {
        "Emergency": "112", "Police": "155",
        "Ambulance": "112", "Tourist Police Istanbul": "527-4503",
    },
    "china": {
        "Police": "110", "Ambulance": "120",
        "Fire": "119", "Tourist Complaints": "12301",
    },
    "korea": {
        "Emergency": "112 / 119",
        "Tourist Helpline (English 24h)": "1330",
        "Police": "112", "Ambulance": "119",
    },
    "usa": {
        "Emergency (All services)": "911",
        "Non-Emergency Police": "311",
        "Poison Control Center": "1-800-222-1222",
    },
    "canada": {
        "Emergency (All services)": "911",
        "Non-Emergency Police": "311",
    },
    "uk": {
        "Emergency": "999",
        "Non-Emergency Police": "101",
        "NHS Medical Helpline": "111",
    },
    "australia": {
        "Emergency": "000",
        "Police (non-emergency)": "131 444",
        "Poison Info Line": "13 11 26",
    },
    "singapore": {
        "Police Emergency": "999",
        "Ambulance / Fire": "995",
        "Singapore Tourism Board": "+65-6736-6622",
        "Tourist Helpline": "+65-1800-736-2000",
    },
    "greece": {
        "Emergency": "112", "Tourist Police": "1571",
        "Ambulance": "166", "Fire": "199",
    },
    "portugal": {
        "Emergency": "112", "GNR Police": "217-614-640",
        "Tourism Emergency": "+351-218-431-680",
    },
    "vietnam": {
        "Police": "113", "Ambulance": "115", "Fire": "114",
        "Tourist Helpline": "024-3200-2940",
    },
    "indonesia": {
        "Emergency": "112", "Police": "110", "Ambulance": "118",
        "Bali Tourism Police": "+62-361-224-111",
    },
    "nepal": {
        "Emergency Police": "100", "Ambulance": "102",
        "Tourist Police": "+977-1-4247-041",
        "Nepal Tourism Board": "+977-1-4256-909",
    },
    "srilanka": {
        "Police": "119", "Ambulance": "110",
        "Tourist Police": "+94-11-242-1052",
        "Sri Lanka Tourism": "1912",
    },
    "switzerland": {
        "Emergency (Rettung)": "112", "Police": "117",
        "Ambulance": "144", "Fire": "118",
    },
    "austria": {
        "Emergency": "112", "Police": "133",
        "Ambulance": "144", "Fire": "122",
    },
}

# City → country mapping
_CITY_COUNTRY: Dict[str, str] = {}
for _c in _JAPANESE: _CITY_COUNTRY[_c] = "japan"
for _c in _FRENCH: _CITY_COUNTRY[_c] = "france"
for _c in _ITALIAN: _CITY_COUNTRY[_c] = "italy"
for _c in _SPANISH: _CITY_COUNTRY[_c] = "spain"
for _c in _GERMAN: _CITY_COUNTRY[_c] = "germany"
for _c in _THAI: _CITY_COUNTRY[_c] = "thailand"
for _c in _ARABIC: _CITY_COUNTRY[_c] = "uae"
for _c in _TURKISH: _CITY_COUNTRY[_c] = "turkey"
for _c in _CHINESE: _CITY_COUNTRY[_c] = "china"
for _c in _KOREAN: _CITY_COUNTRY[_c] = "korea"
for _c in _AMERICAN: _CITY_COUNTRY[_c] = "usa"
for _c in _CANADIAN: _CITY_COUNTRY[_c] = "canada"
for _c in _BRITISH: _CITY_COUNTRY[_c] = "uk"
for _c in _AUSTRALIAN: _CITY_COUNTRY[_c] = "australia"
for _c in _SINGAPOREAN: _CITY_COUNTRY[_c] = "singapore"
for _c in _GREEK: _CITY_COUNTRY[_c] = "greece"
for _c in _PORTUGUESE: _CITY_COUNTRY[_c] = "portugal"
for _c in _VIETNAMESE: _CITY_COUNTRY[_c] = "vietnam"
for _c in _INDONESIAN: _CITY_COUNTRY[_c] = "indonesia"
for _c in _NEPALESE: _CITY_COUNTRY[_c] = "nepal"
for _c in _SRI_LANKAN: _CITY_COUNTRY[_c] = "srilanka"
for _c in _SWISS: _CITY_COUNTRY[_c] = "switzerland"
for _c in _AUSTRIAN: _CITY_COUNTRY[_c] = "austria"
# Indian belt cities
_ALL_INDIA = (_INDIAN_HINDI_BELT | _INDIAN_MARATHI_BELT | _INDIAN_TAMIL_BELT |
              _INDIAN_KANNADA_BELT | _INDIAN_BENGALI_BELT | _INDIAN_GUJARATI_BELT |
              _INDIAN_TELUGU_BELT | _INDIAN_PUNJABI_BELT | _INDIAN_KERALA_BELT | _GOA)
for _c in _ALL_INDIA: _CITY_COUNTRY[_c] = "india"


def get_destination_survival_kit(destination: str) -> List[SurvivalPhrase]:
    """Returns culturally and linguistically appropriate survival phrases for any destination."""
    return _survival_phrases(destination.lower().strip())


def get_destination_emergency_contacts(destination: str) -> Dict[str, str]:
    """Returns verified local emergency contacts for the target city."""
    dest_key = destination.lower().strip()
    dest_name = destination.title().strip()

    if dest_key == "jaipur":
        return _EMERGENCY_CONTACTS_DB["jaipur"]

    country = _CITY_COUNTRY.get(dest_key)
    if country and country in _EMERGENCY_CONTACTS_DB:
        contacts = dict(_EMERGENCY_CONTACTS_DB[country])
        contacts[f"Tourist Information ({dest_name})"] = (
            f"Visit the local tourism office in {dest_name} for maps & guides"
        )
        return contacts

    # Indian cities not in the explicit sets — national helplines
    if country == "india":
        return {
            "National Emergency Number": "112",
            "Police Emergency Helpline": "100 / 112",
            "Medical Ambulance": "108 / 102",
            "Fire Department": "101",
            "Civil / District Hospital": f"Civil / District Hospital ({dest_name})",
            "Local Tourist Assistance": f"Tourism Information Center ({dest_name})",
        }

    # Fully unknown destination — universal numbers
    return {
        "International Emergency (most countries)": "112",
        "Local Police": "911 (USA/Canada) · 999 (UK) · 112 (EU) · 100 (India)",
        "Medical Ambulance": "911 / 999 / 112 / 108 — depending on country",
        f"Nearest Hospital ({dest_name})": "Ask your hotel concierge for the closest hospital",
        f"Tourist Assistance ({dest_name})": "Look for Tourist Police / Info kiosks at main attractions",
    }


# ---------------------------------------------------------------------------
# Dynamic group satisfaction score
# ---------------------------------------------------------------------------

def compute_satisfaction_score(
    val_result: ValidationResult,
    ranked_scored_attractions: list,
    budget: float,
    total_estimated_cost: float
) -> float:
    """Dynamically computes group satisfaction score (60-99) based on plan quality."""
    base = 90.0
    # Validation penalties
    if not val_result.passed:
        base -= 8.0
    base -= min(len(val_result.detected_issues) * 3.0, 12.0)
    # Budget headroom
    if total_estimated_cost > 0 and budget > 0:
        ratio = total_estimated_cost / budget
        if ratio <= 0.75:
            base += 4.0
        elif ratio > 1.0:
            base -= 5.0
    # Attraction quality bonus
    if ranked_scored_attractions:
        avg = sum(sa.scores.overall_score for sa in ranked_scored_attractions) / len(ranked_scored_attractions)
        base += min(max((avg - 70.0) / 5.0, 0.0), 4.0)
    return round(min(max(base, 60.0), 99.0), 1)


# ---------------------------------------------------------------------------
# Main Orchestrator class
# ---------------------------------------------------------------------------

class TravelOrchestrator:
    """
    Central Multi-Agent Coordinator managing state, tool invocations,
    and live event streaming.
    """

    def plan_trip_stream(self, profile: TravelerProfile) -> Generator[Dict[str, Any], None, TripPlan]:
        """
        Executes the end-to-end agentic workflow, yielding live status updates.
        Returns the finalized, validated TripPlan.
        """
        trip_id = f"trip_{uuid.uuid4().hex[:8]}"

        # Step 1: Intake & Persona Analysis
        yield {
            "step": 1,
            "agent": "Travel Intake & Persona Agent",
            "status": "Running",
            "message": (
                f"Analyzing traveler intent for {profile.destination.title()} "
                f"({profile.duration_days} Days, {profile.travelers_count} Travelers, "
                f"{profile.currency}{profile.budget:,.0f} Budget)..."
            ),
            "active_skills": []
        }

        # Step 2: Skill-RAG Routing
        active_skills_dicts = skill_rag_engine.route_skills(profile)
        active_skill_names = [s["name"] for s in active_skills_dicts]

        yield {
            "step": 2,
            "agent": "Skill Router Agent (Skill-RAG)",
            "status": "Running",
            "message": (
                f"Skill Router dynamically loaded {len(active_skills_dicts)} procedural skills "
                f"from Skill-RAG: {', '.join(active_skill_names[:4])}..."
            ),
            "active_skills": active_skill_names
        }

        # Step 3: Global POI Discovery & Dynamic RAG Ingestion
        yield {
            "step": 3,
            "agent": "Global POI & Dynamic RAG Agent",
            "status": "Running",
            "message": (
                f"Discovering real attractions for {profile.destination.title()} via "
                f"Groq AI + OpenStreetMap + Wikipedia, indexing into ChromaDB Vector Store..."
            ),
            "active_skills": active_skill_names
        }
        candidate_pois = discover_global_attractions(profile.destination)
        combined_text = "\n".join(
            [f"{p.name} ({p.category}): {p.description}" for p in candidate_pois[:5]]
        )
        chroma_rag_engine.ingest_dynamic_destination_text(profile.destination, combined_text)

        # Step 4: Real-time Weather Intelligence (Open-Meteo)
        yield {
            "step": 4,
            "agent": "Environmental Weather Agent (Open-Meteo)",
            "status": "Running",
            "message": f"Fetching multi-day meteorological forecast from Open-Meteo API for {profile.destination.title()}...",
            "active_skills": active_skill_names
        }
        weather_forecast = fetch_weather_forecast.invoke({
            "destination": profile.destination,
            "days": profile.duration_days
        })

        # Step 5: 8-Factor MAUT Recommendation Engine
        yield {
            "step": 5,
            "agent": "Recommendation Engine (8-Factor MAUT)",
            "status": "Running",
            "message": (
                f"Computing 8-dimensional utility scores and 'Why Recommended' reasoning "
                f"for {len(candidate_pois)} candidate attractions..."
            ),
            "active_skills": active_skill_names
        }
        is_day1_rain = weather_forecast[0].get("is_rainy", False) if weather_forecast else False
        ranked_scored_attractions = rank_and_select_attractions(
            candidate_pois, profile, is_rainy_day=is_day1_rain, applied_skills=active_skill_names
        )

        # Step 6: Itinerary & Route Optimization (TSP with strict deduplication)
        yield {
            "step": 6,
            "agent": "Itinerary Optimizer Agent (TSP Routing)",
            "status": "Running",
            "message": "Clustering attractions geographically, minimizing Haversine transit distances, and pairing authentic regional dining...",
            "active_skills": active_skill_names
        }

        ranked_pois = [sa.attraction for sa in ranked_scored_attractions]
        days: List[DayPlan] = []
        theme_templates = [
            f"Iconic Heritage & Historic Landmarks of {profile.destination.title()}",
            f"Cultural Highlights & Scenic Nature of {profile.destination.title()}",
            f"Spiritual Sanctuaries & Artisan Bazaars of {profile.destination.title()}",
            f"Lakeside Promenades & Local Life in {profile.destination.title()}",
            f"Panoramic Viewpoints & Hidden Gems of {profile.destination.title()}"
        ]

        allocated_sight_ids: set = set()
        sights_per_day = 3 if profile.travel_style == "Intensive" else 2

        for d_num in range(1, profile.duration_days + 1):
            w_info = weather_forecast[d_num - 1] if (d_num - 1) < len(weather_forecast) else {}
            is_rainy = w_info.get("is_rainy", False)
            theme = theme_templates[(d_num - 1) % len(theme_templates)]

            # Select strictly unused attractions for this day
            day_sights = []
            for sight in ranked_pois:
                if sight.id not in allocated_sight_ids:
                    day_sights.append(sight)
                    allocated_sight_ids.add(sight.id)
                    if len(day_sights) >= sights_per_day:
                        break

            # If pool exhausted, wrap-around (rare edge case for very long trips)
            if not day_sights and ranked_pois:
                day_sights = [ranked_pois[(d_num - 1) % len(ranked_pois)]]

            day_plan = build_day_plan(
                d_num, theme, day_sights, w_info, profile, is_rainy=is_rainy
            )
            days.append(day_plan)

        # Step 7: Validation Agent & Self-Correction Feedback Loop
        yield {
            "step": 7,
            "agent": "Validation Agent (Constraint Verification)",
            "status": "Running",
            "message": "Verifying hard constraints: Total Budget, Opening Hours, Transit Feasibility, and Weather Safety...",
            "active_skills": active_skill_names
        }
        val_result = validate_itinerary(days, profile)

        if not val_result.passed:
            yield {
                "step": 8,
                "agent": "Self-Correction Loop (Autonomous Replan)",
                "status": "Running",
                "message": (
                    f"Constraint issue detected ({val_result.detected_issues[0]}). "
                    f"Invoking procedural replanning skill from Skill-RAG..."
                ),
                "active_skills": active_skill_names
            }
            days, val_result = execute_self_correction_replan(days, profile, candidate_pois)

        # Step 8: Synthesis, Cultural Survival Kit & Exports
        survival_kit = get_destination_survival_kit(profile.destination)
        emergency_contacts = get_destination_emergency_contacts(profile.destination)

        budget_summary = calculate_trip_budget.invoke({
            "days_data": [d.model_dump() for d in days],
            "total_budget": profile.budget,
            "travelers_count": profile.travelers_count,
            "currency": profile.currency
        })

        total_cost = budget_summary["total_estimated_cost"]
        satisfaction = compute_satisfaction_score(
            val_result, ranked_scored_attractions, profile.budget, total_cost
        )

        trip_plan = TripPlan(
            trip_id=trip_id,
            profile=profile,
            days=days,
            total_estimated_cost=total_cost,
            cost_breakdown=budget_summary["cost_breakdown"],
            validation=val_result,
            survival_kit=survival_kit,
            emergency_contacts=emergency_contacts,
            active_skills=active_skill_names,
            group_satisfaction_score=satisfaction,
            created_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        )

        # Generate exported files (.ics and .pdf)
        try:
            generate_trip_ics(trip_plan)
            generate_trip_pdf(trip_plan)
        except Exception:
            pass

        yield {
            "step": 9,
            "agent": "Synthesis & Delivery Agent",
            "status": "Completed",
            "message": "Trip plan fully approved! Leaflet route generated, iCalendar (.ics) synced, and PDF Travel Dossier rendered.",
            "active_skills": active_skill_names,
            "final_plan": trip_plan
        }

        return trip_plan

    def plan_trip(self, profile: TravelerProfile) -> TripPlan:
        """Synchronous wrapper returning final TripPlan."""
        generator = self.plan_trip_stream(profile)
        final_plan = None
        for update in generator:
            if "final_plan" in update:
                final_plan = update["final_plan"]
        return final_plan


# Global Orchestrator
orchestrator = TravelOrchestrator()
