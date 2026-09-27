import os
import requests
import json
import re
import unicodedata
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user

ai_bp = Blueprint('ai', __name__)

# --- OPENROUTER CONFIG ---
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
# Change this to any model available on OpenRouter.
# Good options: "openai/gpt-4o-mini", "anthropic/claude-3.5-sonnet",
#               "meta-llama/llama-3.1-70b-instruct", "google/gemini-flash-1.5"
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "openai/gpt-4o-mini")
# Optional but recommended by OpenRouter:
OPENROUTER_SITE_URL = os.environ.get("OPENROUTER_SITE_URL", "http://localhost")
OPENROUTER_SITE_NAME = os.environ.get("OPENROUTER_SITE_NAME", "SmartTrip AI")


# --- WEATHER HELPER (OPEN-METEO REAL-TIME) ---
# NOTE: Weather is fetched from an external API, NOT from the database.

WEATHER_CODES = {
    0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
    45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
    55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
    80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
    95: "Thunderstorm"
}


def get_realtime_weather(lat, lon):
    """Fetches real-time weather using Open-Meteo API by coordinates."""
    if lat is None or lon is None:
        return None
    try:
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        res = requests.get(url, timeout=3)
        if res.status_code == 200:
            weather_data = res.json().get('current_weather', {})
            temp = weather_data.get('temperature')
            code = weather_data.get('weathercode', 0)
            desc = WEATHER_CODES.get(code, "Clear")
            return f"{temp}°C, {desc}"
    except Exception as e:
        print("--> Real-time Weather Fetch Error:", str(e))
    return None


# --- SESSION & HELPER FUNCTIONS ---

def get_conversation_history():
    return session.get('chat_history', [])


def save_message(role, content):
    history = session.get('chat_history', [])
    history.append({'role': role, 'content': content[:300]})
    session['chat_history'] = history[-6:]
    session.modified = True


def detect_intent(text):
    """Intent detection with Burmese + English keywords.
    NOTE: Intent is used only to shape the AI prompt, not to query the DB.
    """
    text_lower = text.lower().strip()

    casual_keywords = [
        'hello', 'hi', 'hey', 'how are you', 'good morning', 'good evening',
        'thanks', 'thank you', 'bye', 'mingalaba',
        'မင်္ဂလာပါ', 'ဟယ်လို', 'ကျေးဇူးတင်ပါတယ်', 'ဘိုင်ဘိုင်', 'နေကောင်းလား'
    ]

    top_rated_keywords = [
        'top rated', 'highest rated', 'best rating', '5 star', 'best rated',
        'highest rating', 'rating', 'အဆင့်အမြင့်ဆုံး', 'အကောင်းဆုံး rating', 'အမြင့်ဆုံးအဆင့်'
    ]

    most_liked_keywords = [
        'most liked', 'popular', 'favorite', 'likes', 'most popular', 'liked',
        'လူကြိုက်အများဆုံး', 'အနှစ်သက်ဆုံး', 'အနှစ်သက်ဆုံးနေရာ'
    ]

    most_viewed_keywords = [
        'most viewed', 'most visited', 'views', 'trending', 'viewed',
        'ကြည့်အများဆုံး', 'လာရောက်အများဆုံး'
    ]

    restaurant_keywords = [
        'restaurant', 'food', 'eat', 'dinner', 'lunch', 'breakfast', 'cafe',
        'စားသောက်ဆိုင်', 'အစားအစာ', 'ထမင်းစား', 'ကော်ဖီဆိုင်', 'စားရမယ့်နေရာ'
    ]

    recommendation_keywords = [
        'recommend', 'recommendation', 'suggest', 'best', 'where should',
        'what should', 'which place', 'အကြံပြု', 'ဘယ်နေရာသွားရမလဲ', 'ဘာလုပ်ရမလဲ',
        'သွားသင့်တဲ့နေရာ'
    ]

    comparison_keywords = [
        ' or ', 'compare', 'difference', 'better', 'နှိုင်းယှဉ်', 'ပိုကောင်း'
    ]

    follow_up_keywords = [
        'how much', 'price', 'cost', 'is it', 'what about', 'tell me more',
        'more about', 'how long', 'when', 'there', 'it', 'that place',
        'ဘယ်လောက်လဲ', 'ဈေးနှုန်း', 'ထပ်ပြောပါ', 'အဲ့ဒါ', 'အဲဒီနေရာ'
    ]

    place_keywords = [
        'place', 'places', 'visit', 'destination', 'travel', 'go', 'trip',
        'tourist', 'attraction', 'hotel', 'weather', 'temp', 'temperature',
        'နေရာ', 'သွားရမယ့်နေရာ', 'ခရီးသွား', 'ရာသီဥတု', 'ဟိုတယ်', 'ခရီးစဉ်'
    ]

    if any(x in text_lower for x in casual_keywords):
        return 'casual'
    if any(x in text_lower for x in top_rated_keywords):
        return 'top_rated'
    if any(x in text_lower for x in most_liked_keywords):
        return 'most_liked'
    if any(x in text_lower for x in most_viewed_keywords):
        return 'most_viewed'
    if any(x in text_lower for x in comparison_keywords):
        return 'comparison'
    if any(x in text_lower for x in restaurant_keywords):
        return 'restaurant_search'
    if any(x in text_lower for x in recommendation_keywords):
        return 'recommendation'
    if any(x in text_lower for x in follow_up_keywords):
        return 'follow_up'
    if any(x in text_lower for x in place_keywords):
        return 'place_search'

    return 'general'


def build_system_prompt(user_message, intent):
    """System prompt for pure OpenRouter API usage (no database context).

    Emphasizes:
      - Logical, well-reasoned answers (ကျိုးကြောင်းဆီလျော်မှု)
      - Correct spelling and grammar (စာလုံးပေါင်းသတ်ပုံမှန်ကန်မှု)
    """
    comparison_note = ""
    if intent == 'comparison':
        comparison_note = (
            "\n10. The user is asking for a COMPARISON. Compare the top 2 options "
            "side by side with clear pros and cons, and give a reasoned conclusion."
        )

    analytical_note = ""
    if intent in ['top_rated', 'most_liked', 'most_viewed']:
        analytical_note = (
            "\n11. The user is asking for a ranked list. Since no live database is available, "
            "provide a well-reasoned general recommendation list from your knowledge. "
            "Explain WHY each item is recommended (e.g., historical significance, natural beauty, "
            "local reputation). Clearly state these are general suggestions, not live rankings."
        )

    return f"""You are 'SmartTrip AI', a helpful, polite, and LOGICAL travel assistant for Myanmar.

USER MESSAGE: "{user_message}"
DETECTED INTENT: {intent}

IMPORTANT: You do NOT have access to any live database. Do NOT invent specific numbers
such as likes, ratings, or view counts. If the user asks for rankings or statistics,
explain that you can only give general recommendations from your knowledge.

=== CRITICAL RULES (MUST FOLLOW) ===

A. LOGICAL REASONING (ကျိုးကြောင်းဆီလျော်မှု):
   1. Every claim you make MUST be supported by a reason (e.g., "X is famous because ...").
   2. When recommending, explain WHY — mention history, culture, nature, food, accessibility, etc.
   3. If you are uncertain, say so honestly instead of guessing.
   4. Structure answers logically: (1) direct answer, (2) reasons, (3) conclusion/advice.
   5. Do NOT give random or unrelated information. Stay on topic.

B. SPELLING & GRAMMAR (စာလုံးပေါင်းသတ်ပုံ):
   6. Use PROPER Burmese spelling and grammar (မြန်မာစာ သတ်ပုံမှန်ရမယ်). Do NOT use Zawgyi-style
      broken text. Use standard Unicode Burmese (NFC form).
   7. Use PROPER English spelling and grammar. No typos, no SMS-style abbreviations.
   8. Use correct punctuation. End sentences properly.
   9. If you are unsure of a word's spelling, choose a simpler word you are sure about.
   10. Do NOT mix broken characters or random diacritics.

C. LANGUAGE MATCHING:
   11. Respond in the SAME language as the user's message. If the user writes in Burmese,
       reply in Burmese. If in English, reply in English.

D. HONESTY:
   12. If the context has no relevant data, say so honestly instead of inventing facts.
   13. Do NOT invent specific numbers (likes, ratings, views). You have no database access.
   14. For real-time weather, say you cannot fetch live weather without a specific location,
       and give a seasonal estimate instead — clearly labeled as an estimate.

E. STYLE:
   15. Be warm and welcoming. Use "မင်္ဂလာပါ" when appropriate.
   16. Keep answers concise and under 5 sentences (except for comparisons).{comparison_note}{analytical_note}
"""


def normalize_text(text):
    """Normalize Unicode so Burmese text renders correctly (NFC form)."""
    try:
        return unicodedata.normalize('NFC', text)
    except Exception:
        return text


def has_zawgyi_or_broken_burmese(text):
    """Detect likely Zawgyi or broken Burmese encoding.

    Zawgyi text often contains characters in the range U+1050–U+109F in ways
    that do not combine properly, or uses U+1039 (virama) incorrectly.
    This is a lightweight heuristic — not perfect, but catches common cases.
    """
    if not text:
        return False
    # Common Zawgyi-only code points that should not appear in standard Unicode Burmese.
    zawgyi_markers = ['\u1050', '\u1051', '\u1052', '\u1053', '\u1054', '\u1055',
                      '\u1056', '\u1057', '\u1058', '\u1059', '\u105A', '\u105B',
                      '\u105C', '\u105D', '\u105E', '\u105F', '\u1060', '\u1061',
                      '\u1062', '\u1063', '\u1064', '\u1065', '\u1066', '\u1067',
                      '\u1068', '\u1069', '\u106A', '\u106B', '\u106C', '\u106D',
                      '\u106E', '\u106F', '\u1070', '\u1071', '\u1072', '\u1073',
                      '\u1074', '\u1075', '\u1076', '\u1077', '\u1078', '\u1079',
                      '\u107A', '\u107B', '\u107C', '\u107D', '\u107E', '\u107F',
                      '\u1080', '\u1081', '\u1082', '\u1083', '\u1084', '\u1085',
                      '\u1086', '\u1087', '\u1088', '\u1089', '\u108A', '\u108B',
                      '\u108C', '\u108D', '\u108E', '\u108F']
    # If many of these appear, it's likely Zawgyi.
    count = sum(1 for ch in text if ch in zawgyi_markers)
    return count > 3


def call_openrouter(system_prompt, user_message, chat_history, require_json=False):
    """Call OpenRouter API. Uses low temperature to reduce spelling/grammar errors."""
    api_key = os.environ.get('OPENROUTER_API_KEY')
    if not api_key:
        return "AI service is currently unconfigured. (Missing OpenRouter API Key)"

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"][:250]})
    messages.append({"role": "user", "content": user_message[:300]})

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": 0.2,   # Low temp = fewer spelling/grammar mistakes
        "max_tokens": 800
    }

    if require_json:
        # OpenRouter passes response_format through to providers that support it.
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        # Optional but recommended by OpenRouter:
        "HTTP-Referer": OPENROUTER_SITE_URL,
        "X-Title": OPENROUTER_SITE_NAME,
    }

    try:
        response = requests.post(
            OPENROUTER_API_URL,
            headers=headers,
            json=payload,
            timeout=30  # OpenRouter can be slower than direct providers; give it more time
        )
        res_json = response.json()

        # OpenRouter returns errors in a few possible shapes
        if 'error' in res_json:
            err = res_json['error']
            err_msg = err.get('message') if isinstance(err, dict) else str(err)
            return f"AI Error: {err_msg or 'Unknown error'}"

        # OpenRouter sometimes returns 200 with an empty choices array
        choices = res_json.get('choices') or []
        if not choices:
            return "Sorry, the AI provider returned an empty response."

        return choices[0]['message']['content']

    except Exception as e:
        print("--> OpenRouter Request Exception:", str(e))
        return "Sorry, I am having trouble connecting to the AI provider right now."


def call_openrouter_with_validation(system_prompt, user_message, chat_history, require_json=False):
    """Call OpenRouter, then validate spelling/encoding. If broken, retry once with a repair prompt."""
    reply = call_openrouter(system_prompt, user_message, chat_history, require_json=require_json)
    reply = normalize_text(reply)

    # If the reply looks like Zawgyi/broken Burmese, ask the model to repair it.
    if has_zawgyi_or_broken_burmese(reply) and not require_json:
        repair_prompt = (
            "The following text may contain Zawgyi or broken Burmese encoding, "
            "or spelling/grammar mistakes. Please rewrite it in correct standard "
            "Unicode Burmese (or correct English if it is English), with proper "
            "spelling, grammar, and punctuation. Keep the same meaning and structure. "
            "Output ONLY the corrected text."
        )
        repaired = call_openrouter(
            "You are a strict Burmese and English proofreader. "
            "You fix spelling, grammar, and encoding issues. "
            "You never change the meaning. You output only the corrected text.",
            f"{repair_prompt}\n\n---\n{reply}",
            chat_history=[],
            require_json=False
        )
        repaired = normalize_text(repaired)
        # Use the repaired version if it looks better.
        if repaired and not has_zawgyi_or_broken_burmese(repaired):
            return repaired
        return repaired if repaired else reply

    return reply


# --- MAIN AI ROUTE (PURE OPENROUTER, NO DATABASE) ---

@ai_bp.route('/api/chat', methods=['POST'])
@login_required
def api_chat():
    data = request.get_json() or {}
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({'error': 'Message is required'}), 400

    intent = detect_intent(user_message)
    save_message('user', user_message)

    # Build a prompt that does NOT include any database context.
    system_prompt = build_system_prompt(user_message, intent)

    reply = call_openrouter_with_validation(
        system_prompt, user_message, get_conversation_history()
    )
    reply = normalize_text(reply)
    save_message('assistant', reply)

    # No database entities to suggest.
    return jsonify({
        'reply': reply,
        'intent': intent,
        'suggested_entities': []
    })


# --- AI TRIP SUGGEST ROUTE (PURE OPENROUTER, NO DATABASE) ---

@ai_bp.route('/api/trip/ai-suggest', methods=['POST'])
@login_required
def ai_suggest_trip():
    try:
        # No database access. Ask OpenRouter to generate a trip from general knowledge.
        system_prompt = """You are an analytical travel strategist for Myanmar.
        You do NOT have access to any live database. Generate a trip plan using your general
        knowledge of Myanmar destinations.

        CRITICAL RULES:
        - Use PROPER Burmese and English spelling and grammar.
        - Do NOT use Zawgyi-style broken Burmese. Use standard Unicode Burmese.
        - Be logical: each waypoint should make sense as part of a coherent day trip
          (e.g., nearby locations, logical travel order).
        - You must output in valid JSON."""

        user_prompt = """
        Create a sample 1-day trip plan for a traveler in Myanmar.
        Choose one main destination and up to 4 logical waypoints (places or restaurants).
        Make sure the waypoints are logically connected (nearby, sensible travel order).

        Respond ONLY with a valid JSON object matching this exact structure:
        {
            "title": "A catchy, relevant trip title",
            "dest_place_id": 0,
            "waypoints": [
                {"id": "place_0", "name": "Place Name"},
                {"id": "restaurant_0", "name": "Restaurant Name"}
            ]
        }
        Note: Since there is no database, use 0 for dest_place_id and generic IDs for waypoints.
        """

        reply = call_openrouter(system_prompt, user_prompt, chat_history=[], require_json=True)
        reply = normalize_text(reply)

        try:
            json_match = re.search(r'\{.*\}', reply, re.DOTALL)
            clean_json_str = json_match.group() if json_match else reply
            trip_data = json.loads(clean_json_str)

            # Minimal validation
            if not trip_data.get("title"):
                trip_data["title"] = "Explore Myanmar"
            if not isinstance(trip_data.get("waypoints"), list):
                trip_data["waypoints"] = []
            if "dest_place_id" not in trip_data:
                trip_data["dest_place_id"] = 0

            return jsonify({"success": True, "trip": trip_data})

        except Exception as parse_err:
            print("--> JSON Parsing/Healing Fallback Triggered:", str(parse_err))
            print("--> Raw AI Output was:", reply)
            fallback_trip = {
                "title": "Explore Myanmar",
                "dest_place_id": 0,
                "waypoints": []
            }
            return jsonify({"success": True, "trip": fallback_trip})

    except Exception as e:
        print("--> AI Trip Generation Error:", str(e))
        return jsonify({"success": False, "error": str(e)}), 500