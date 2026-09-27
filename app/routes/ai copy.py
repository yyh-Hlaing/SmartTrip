# import os
# import requests
# import json
# import re
# from flask import Blueprint, request, jsonify, session
# from flask_login import login_required, current_user
# from sqlalchemy import func
# from app.models import (
#     db, User, Place, Feedback, Rating, Comment, PlaceLike, 
#     Restaurant, RestaurantComment, RestaurantRating, Announcement, Ad, Role, TripPlan
# )

# ai_bp = Blueprint('ai', __name__)

# # --- WEATHER HELPER (OPEN-METEO REAL-TIME) ---

# WEATHER_CODES = {
#     0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
#     45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
#     55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
#     80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
#     95: "Thunderstorm"
# }

# def get_realtime_weather(lat, lon):
#     """Fetches real-time weather using Open-Meteo API by coordinates."""
#     if lat is None or lon is None:
#         return None
#     try:
#         url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
#         res = requests.get(url, timeout=3)
#         if res.status_code == 200:
#             weather_data = res.json().get('current_weather', {})
#             temp = weather_data.get('temperature')
#             code = weather_data.get('weathercode', 0)
#             desc = WEATHER_CODES.get(code, "Clear")
#             return f"{temp}°C, {desc}"
#     except Exception as e:
#         print("--> Real-time Weather Fetch Error:", str(e))
#     return None

# def get_fallback_weather_for_region(region_id):
#     fallback_map = {
#         12: "32°C, Sunny",        # Yangon
#         9:  "35°C, Hot & Sunny",  # Mandalay
#         13: "24°C, Cool & Clear", # Shan State
#         11: "28°C, Partly Cloudy",# Rakhine
#         1:  "22°C, Cool",         # Kachin
#         6:  "30°C, Humid & Sunny" # Tanintharyi
#     }
#     return fallback_map.get(region_id, "28°C, Clear")

# # --- SESSION & HELPER FUNCTIONS ---

# def get_conversation_history():
#     return session.get('chat_history', [])

# def save_message(role, content):
#     history = session.get('chat_history', [])
#     history.append({'role': role, 'content': content[:300]})
#     session['chat_history'] = history[-6:]
#     session.modified = True

# def get_last_entity():
#     return session.get('last_entity', None)

# def save_last_entity(entity_data):
#     if not entity_data or 'obj' not in entity_data:
#         return
#     obj = entity_data['obj']
#     session['last_entity'] = {
#         'id': obj.id,
#         'type': entity_data['type'],
#         'name': obj.name
#     }
#     session.modified = True

# def detect_intent(text):
#     text = text.lower().strip()

#     casual_keywords = ['hello', 'hi', 'hey', 'how are you', 'good morning', 'good evening', 'thanks', 'thank you', 'bye', 'mingalaba']
#     top_rated_keywords = ['top rated', 'highest rated', 'best rating', '5 star', 'best rated', 'highest rating', 'rating']
#     most_liked_keywords = ['most liked', 'popular', 'favorite', 'likes', 'most popular', 'liked']
#     most_viewed_keywords = ['most viewed', 'most visited', 'views', 'trending', 'viewed']
#     restaurant_keywords = ['restaurant', 'food', 'eat', 'dinner', 'lunch', 'breakfast', 'cafe']
#     recommendation_keywords = ['recommend', 'recommendation', 'suggest', 'best', 'where should', 'what should', 'which place']
#     comparison_keywords = [' or ', 'compare', 'difference', 'better']
#     follow_up_keywords = ['how much', 'price', 'cost', 'is it', 'what about', 'tell me more', 'more about', 'how long', 'when', 'there', 'it', 'that place']
#     place_keywords = ['place', 'places', 'visit', 'destination', 'travel', 'go', 'trip', 'tourist', 'attraction', 'hotel', 'weather', 'temp', 'temperature']

#     if any(x in text for x in casual_keywords):
#         return 'casual'
#     if any(x in text for x in top_rated_keywords):
#         return 'top_rated'
#     if any(x in text for x in most_liked_keywords):
#         return 'most_liked'
#     if any(x in text for x in most_viewed_keywords):
#         return 'most_viewed'
#     if any(x in text for x in comparison_keywords):
#         return 'comparison'
#     if any(x in text for x in restaurant_keywords):
#         return 'restaurant_search'
#     if any(x in text for x in recommendation_keywords):
#         return 'recommendation'
#     if any(x in text for x in follow_up_keywords):
#         return 'follow_up'
#     if any(x in text for x in place_keywords):
#         return 'place_search'

#     return 'general'

# def extract_region_from_text(text):
#     text = text.lower()
#     region_map = {
#         'kachin': 1, 'kayah': 2, 'kayin': 3, 'chin': 4,
#         'sagaing': 5, 'tanintharyi': 6, 'bago': 7, 'magway': 8,
#         'mandalay': 9, 'mon': 10, 'rakhine': 11, 'ngapali': 11,
#         'yangon': 12, 'shan': 13, 'inle': 13, 'taunggyi': 13,
#         'ayeyarwady': 14, 'naypyidaw': 15, 'nay pyi taw': 15
#     }
#     for name, r_id in region_map.items():
#         if name in text:
#             return r_id
#     return None

# def fetch_analytical_entities(intent, region_id=None):
#     """Queries DB directly using SQL aggregations for sorting by metrics."""
#     matches = []
    
#     if intent == 'most_liked':
#         query = db.session.query(Place, func.count(PlaceLike.id).label('like_count'))\
#             .outerjoin(PlaceLike)\
#             .group_by(Place.id)
#         if region_id:
#             query = query.filter(Place.region_id == region_id)
#         results = query.order_by(db.desc('like_count')).limit(5).all()
        
#         for place, count in results:
#             avg_stars = place.average_rating
#             total_comments = len(place.comments)
#             matches.append({
#                 'type': 'place',
#                 'obj': place,
#                 'desc_short': (place.description or 'N/A')[:150],
#                 'stats': f"{count} Likes, {avg_stars:.1f}/5 Rating, {total_comments} Comments, {place.view_count} Views"
#             })

#     elif intent == 'top_rated':
#         # Fetch Top Places
#         query_p = db.session.query(Place, func.coalesce(func.avg(Rating.stars), 0).label('avg_stars'))\
#             .outerjoin(Rating)\
#             .group_by(Place.id)
#         if region_id:
#             query_p = query_p.filter(Place.region_id == region_id)
#         places_res = query_p.order_by(db.desc('avg_stars')).limit(5).all()

#         for place, avg_s in places_res:
#             likes_count = len(place.likes)
#             total_comments = len(place.comments)
#             matches.append({
#                 'type': 'place',
#                 'obj': place,
#                 'desc_short': (place.description or 'N/A')[:150],
#                 'stats': f"{float(avg_s):.1f}/5 Rating, {likes_count} Likes, {total_comments} Comments"
#             })

#     elif intent == 'most_viewed':
#         query = Place.query
#         if region_id:
#             query = query.filter_by(region_id=region_id)
#         results = query.order_by(Place.view_count.desc()).limit(5).all()
        
#         for place in results:
#             likes_count = len(place.likes)
#             avg_stars = place.average_rating
#             matches.append({
#                 'type': 'place',
#                 'obj': place,
#                 'desc_short': (place.description or 'N/A')[:150],
#                 'stats': f"{place.view_count} Views, {likes_count} Likes, {avg_stars:.1f}/5 Rating"
#             })

#     # Hydrate matched entities with real-time weather
#     for match in matches:
#         obj = match['obj']
#         lat = getattr(obj, 'latitude', None)
#         lon = getattr(obj, 'longitude', None)
#         live_weather = get_realtime_weather(lat, lon) or get_fallback_weather_for_region(getattr(obj, 'region_id', 12))

#         match['context'] = (
#             f"Type: {match['type'].capitalize()}\n"
#             f"Name: {obj.name}\n"
#             f"Description: {match['desc_short']}\n"
#             f"Stats: {match['stats']}\n"
#             f"Real-Time Weather: {live_weather}"
#         )

#     return matches

# def find_relevant_entities(user_message, places, restaurants):
#     entity_features = []
#     entity_data_context = []

#     for place in places:
#         total_likes = len(place.likes) if hasattr(place, 'likes') else 0
#         total_comments = len(place.comments) if hasattr(place, 'comments') else 0
#         avg_rating = place.average_rating

#         desc_short = (place.description or 'N/A')[:150]
#         feature_string = f"{place.name} {getattr(place, 'package', '') or ''} {desc_short} place destination hotel"
#         entity_features.append(feature_string.lower())
        
#         entity_data_context.append({
#             "type": "place",
#             "obj": place,
#             "desc_short": desc_short,
#             "stats": f"{total_likes} Likes, {avg_rating:.1f}/5 Rating, {total_comments} Comments, {place.view_count} Views"
#         })

#     for restaurant in restaurants:
#         total_comments = len(restaurant.comments) if hasattr(restaurant, 'comments') else 0
#         avg_rating = (sum([r.stars for r in restaurant.ratings]) / len(restaurant.ratings)) if getattr(restaurant, 'ratings', None) else 0
        
#         desc_short = (restaurant.description or 'N/A')[:150]
#         feature_string = f"{restaurant.name} {desc_short} food restaurant dining"
#         entity_features.append(feature_string.lower())
        
#         entity_data_context.append({
#             "type": "restaurant",
#             "obj": restaurant,
#             "desc_short": desc_short,
#             "stats": f"{avg_rating:.1f}/5 Rating, {total_comments} Comments"
#         })

#     if not entity_data_context:
#         return []

#     try:
#         from sklearn.feature_extraction.text import TfidfVectorizer
#         from sklearn.neighbors import NearestNeighbors

#         vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
#         tfidf_matrix = vectorizer.fit_transform(entity_features)

#         knn = NearestNeighbors(n_neighbors=min(5, len(entity_features)), metric='cosine')
#         knn.fit(tfidf_matrix)

#         user_vec = vectorizer.transform([user_message.lower()])
#         distances, indices = knn.kneighbors(user_vec)

#         raw_matches = [entity_data_context[idx] for idx in indices[0]]

#         final_matches = []
#         for match in raw_matches:
#             obj = match['obj']
#             lat = getattr(obj, 'latitude', None)
#             lon = getattr(obj, 'longitude', None)

#             live_weather = get_realtime_weather(lat, lon) or get_fallback_weather_for_region(getattr(obj, 'region_id', 12))

#             match['context'] = (
#                 f"Type: {match['type'].capitalize()}\n"
#                 f"Name: {obj.name}\n"
#                 f"Description: {match['desc_short']}\n"
#                 f"Stats: {match['stats']}\n"
#                 f"Real-Time Weather: {live_weather}"
#             )
#             final_matches.append(match)

#         return final_matches
#     except Exception as e:
#         print("--> TF-IDF/KNN Match Warning:", str(e))
#         return [entity_data_context[0]]

# def build_context(matches):
#     if not matches:
#         return "No specific entity records matched."
#     context = []
#     for match in matches:
#         context.append(match.get('context', f"Name: {match['obj'].name}"))
#     return "\n---\n".join(context)

# def build_system_prompt(user_message, intent, context_text):
#     return f"""You are 'SmartTrip AI', a travel assistant for Myanmar.

# USER MESSAGE: "{user_message}"
# DETECTED INTENT: {intent}

# DATABASE & METRICS CONTEXT:
# {context_text}

# INSTRUCTIONS:
# 1. State numbers and facts (Likes, Ratings, Views) explicitly as provided in the context data.
# 2. If intent is 'top_rated', 'most_liked', or 'most_viewed', present the top matches in exact order from highest to lowest.
# 3. Keep answers concise and under 5 sentences.
# """

# def call_groq(system_prompt, user_message, chat_history, require_json=False):
#     groq_api_key = os.environ.get('GROQ_API_KEY')
#     if not groq_api_key:
#         return "AI service is currently unconfigured. (Missing API Key)"

#     messages = [{"role": "system", "content": system_prompt}]
#     for msg in chat_history[-4:]:
#         messages.append({"role": msg["role"], "content": msg["content"][:250]})
#     messages.append({"role": "user", "content": user_message[:300]})

#     payload = {
#         "model": "openai/gpt-oss-120b",
#         "messages": messages,
#         "temperature": 0.5,
#         "max_tokens": 800 
#     }
    
#     if require_json:
#         payload["response_format"] = {"type": "json_object"}

#     try:
#         response = requests.post(
#             "https://api.groq.com/openai/v1/chat/completions",
#             headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_api_key}"},
#             json=payload,
#             timeout=15
#         )
#         res_json = response.json()
#         if 'error' in res_json:
#             return f"AI Error: {res_json['error'].get('message', 'Unknown error')}"
#         return res_json['choices'][0]['message']['content']
#     except Exception as e:
#         print("--> Groq Request Exception:", str(e))
#         return "Sorry, I am having trouble connecting to the AI provider right now."

# # --- MAIN AI ROUTE ---

# @ai_bp.route('/api/chat', methods=['POST'])
# @login_required
# def api_chat():
#     data = request.get_json() or {}
#     user_message = data.get('message', '').strip()

#     if not user_message:
#         return jsonify({'error': 'Message is required'}), 400

#     intent = detect_intent(user_message)
#     save_message('user', user_message)

#     matches = []
#     target_region_id = extract_region_from_text(user_message)

#     # 1. Handle Analytical Intent Queries (Direct SQL Aggregation)
#     if intent in ['most_liked', 'top_rated', 'most_viewed']:
#         matches = fetch_analytical_entities(intent, region_id=target_region_id)

#     # 2. Handle Conversation Follow-ups
#     elif intent == 'follow_up':
#         last_entity = get_last_entity()
#         if last_entity:
#             entity_obj = None
#             if last_entity['type'] == 'place':
#                 entity_obj = Place.query.get(last_entity['id'])
#             elif last_entity['type'] == 'restaurant':
#                 entity_obj = Restaurant.query.get(last_entity['id'])

#             if entity_obj:
#                 lat = getattr(entity_obj, 'latitude', None)
#                 lon = getattr(entity_obj, 'longitude', None)
#                 live_weather = get_realtime_weather(lat, lon) or get_fallback_weather_for_region(getattr(entity_obj, 'region_id', 12))
                
#                 matches = [{
#                     'type': last_entity['type'],
#                     'obj': entity_obj,
#                     'context': f"Type: {last_entity['type'].capitalize()}\nName: {entity_obj.name}\nDescription: {(entity_obj.description or 'N/A')[:150]}\nReal-Time Weather: {live_weather}"
#                 }]

#     # 3. Fallback to Vector TF-IDF Search for text/location matching
#     if not matches and intent not in ['casual', 'general']:
#         if target_region_id:
#             places = Place.query.filter_by(region_id=target_region_id).all()
#             restaurants = Restaurant.query.filter_by(region_id=target_region_id).all()
#         else:
#             places = Place.query.all()
#             restaurants = Restaurant.query.all()

#         matches = find_relevant_entities(user_message, places, restaurants)

#     context_str = build_context(matches)
#     system_prompt = build_system_prompt(user_message, intent, context_str)
    
#     reply = call_groq(system_prompt, user_message, get_conversation_history())
#     save_message('assistant', reply)

#     suggested_entities = []
#     if matches and intent not in ['casual', 'general']:
#         for match in matches[:5]:
#             suggested_entities.append({
#                 'id': match['obj'].id,
#                 'name': match['obj'].name,
#                 'type': match['type']
#             })
#         save_last_entity(matches[0])

#     return jsonify({
#         'reply': reply,
#         'intent': intent,
#         'suggested_entities': suggested_entities
#     })


# @ai_bp.route('/api/trip/ai-suggest', methods=['POST'])
# @login_required
# def ai_suggest_trip():
#     try:
#         places = Place.query.limit(20).all()
#         restaurants = Restaurant.query.limit(20).all()
        
#         if not places:
#             return jsonify({
#                 "success": False, 
#                 "error": "No places found in the database. Please add some destinations first."
#             }), 400

#         valid_place_ids = [p.id for p in places]
        
#         fallback_trip = {
#             "title": f"Explore {places[0].name} & Surroundings",
#             "dest_place_id": places[0].id,
#             "waypoints": [{"id": f"place_{p.id}", "name": p.name} for p in places[1:3]]
#         }

#         user_favorites = [f.place.name for f in current_user.favorites if f.place] if hasattr(current_user, 'favorites') else []
#         user_likes = [l.place.name for l in current_user.likes if l.place] if hasattr(current_user, 'likes') else []
        
#         places_ctx = ", ".join([f"{p.name} (ID: {p.id})" for p in places])
#         rests_ctx = ", ".join([f"{r.name} (ID: {r.id})" for r in restaurants]) if restaurants else "None available"
        
#         system_prompt = """You are an analytical travel strategist. 
#         Analyze preferences and build a trip plan using the provided IDs. You must output in valid JSON."""
        
#         user_prompt = f"""
#         User's Favorited Places: {', '.join(user_favorites) if user_favorites else 'None'}
#         User's Liked Places: {', '.join(user_likes) if user_likes else 'None'}
        
#         Available Places: {places_ctx}
#         Available Restaurants: {rests_ctx}
        
#         Select 1 destination place ID and up to 4 logical waypoints using the exact IDs provided.
        
#         Respond ONLY with a valid JSON object matching this exact structure:
#         {{
#             "title": "A catchy, relevant trip title",
#             "dest_place_id": <integer_id_from_available_places>,
#             "waypoints": [
#                 {{"id": "place_<id>", "name": "Place Name"}},
#                 {{"id": "restaurant_<id>", "name": "Restaurant Name"}}
#             ]
#         }}
#         """
        
#         reply = call_groq(system_prompt, user_prompt, chat_history=[], require_json=True)
        
#         try:
#             json_match = re.search(r'\{.*\}', reply, re.DOTALL)
#             clean_json_str = json_match.group() if json_match else reply
            
#             trip_data = json.loads(clean_json_str)
            
#             if not trip_data.get("title"):
#                 trip_data["title"] = fallback_trip["title"]
                
#             dest_id = trip_data.get("dest_place_id")
#             if dest_id not in valid_place_ids:
#                 trip_data["dest_place_id"] = fallback_trip["dest_place_id"]
                
#             if not trip_data.get("waypoints") or not isinstance(trip_data["waypoints"], list):
#                 trip_data["waypoints"] = fallback_trip["waypoints"]
#             # -----------------------------

#             return jsonify({"success": True, "trip": trip_data})
            
#         except Exception as parse_err:
#             print("--> JSON Parsing/Healing Fallback Triggered:", str(parse_err))
#             print("--> Raw AI Output was:", reply)
#             return jsonify({"success": True, "trip": fallback_trip})
            
#     except Exception as e:
#         print("--> AI Trip Generation Error:", str(e))
#         return jsonify({"success": False, "error": str(e)}), 500

# import os
# import requests
# import json
# import re
# import unicodedata
# from flask import Blueprint, request, jsonify, session
# from flask_login import login_required, current_user
# from sqlalchemy import func
# from app.models import (
#     db, User, Place, Feedback, Rating, Comment, PlaceLike,
#     Restaurant, RestaurantComment, RestaurantRating, Announcement, Ad, Role, TripPlan
# )

# ai_bp = Blueprint('ai', __name__)

# # --- WEATHER HELPER (OPEN-METEO REAL-TIME) ---

# WEATHER_CODES = {
#     0: "Clear sky", 1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
#     45: "Foggy", 48: "Depositing rime fog", 51: "Light drizzle", 53: "Moderate drizzle",
#     55: "Dense drizzle", 61: "Slight rain", 63: "Moderate rain", 65: "Heavy rain",
#     80: "Slight rain showers", 81: "Moderate rain showers", 82: "Violent rain showers",
#     95: "Thunderstorm"
# }


# def get_realtime_weather(lat, lon):
#     """Fetches real-time weather using Open-Meteo API by coordinates."""
#     if lat is None or lon is None:
#         return None
#     try:
#         url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
#         res = requests.get(url, timeout=3)
#         if res.status_code == 200:
#             weather_data = res.json().get('current_weather', {})
#             temp = weather_data.get('temperature')
#             code = weather_data.get('weathercode', 0)
#             desc = WEATHER_CODES.get(code, "Clear")
#             return f"{temp}°C, {desc}"
#     except Exception as e:
#         print("--> Real-time Weather Fetch Error:", str(e))
#     return None


# def get_fallback_weather_for_region(region_id):
#     """Seasonal estimate when live weather is unavailable (clearly labeled)."""
#     fallback_map = {
#         12: "~32°C, typically sunny (seasonal estimate)",
#         9:  "~35°C, typically hot & sunny (seasonal estimate)",
#         13: "~24°C, typically cool & clear (seasonal estimate)",
#         11: "~28°C, typically partly cloudy (seasonal estimate)",
#         1:  "~22°C, typically cool (seasonal estimate)",
#         6:  "~30°C, typically humid & sunny (seasonal estimate)"
#     }
#     return fallback_map.get(region_id, "Seasonal estimate unavailable")


# # --- SESSION & HELPER FUNCTIONS ---

# def get_conversation_history():
#     return session.get('chat_history', [])


# def save_message(role, content):
#     history = session.get('chat_history', [])
#     history.append({'role': role, 'content': content[:300]})
#     session['chat_history'] = history[-6:]
#     session.modified = True


# def get_last_entity():
#     return session.get('last_entity', None)


# def save_last_entity(entity_data):
#     if not entity_data or 'obj' not in entity_data:
#         return
#     obj = entity_data['obj']
#     session['last_entity'] = {
#         'id': obj.id,
#         'type': entity_data['type'],
#         'name': obj.name
#     }
#     session.modified = True


# def detect_intent(text):
#     """Improved intent detection with Burmese + English keywords."""
#     text_lower = text.lower().strip()

#     casual_keywords = [
#         'hello', 'hi', 'hey', 'how are you', 'good morning', 'good evening',
#         'thanks', 'thank you', 'bye', 'mingalaba',
#         'မင်္ဂလာပါ', 'ဟယ်လို', 'ကျေးဇူးတင်ပါတယ်', 'ဘိုင်ဘိုင်', 'နေကောင်းလား'
#     ]

#     top_rated_keywords = [
#         'top rated', 'highest rated', 'best rating', '5 star', 'best rated',
#         'highest rating', 'rating', 'အဆင့်အမြင့်ဆုံး', 'အကောင်းဆုံး rating', 'အမြင့်ဆုံးအဆင့်'
#     ]

#     most_liked_keywords = [
#         'most liked', 'popular', 'favorite', 'likes', 'most popular', 'liked',
#         'လူကြိုက်အများဆုံး', 'အနှစ်သက်ဆုံး', 'အနှစ်သက်ဆုံးနေရာ'
#     ]

#     most_viewed_keywords = [
#         'most viewed', 'most visited', 'views', 'trending', 'viewed',
#         'ကြည့်အများဆုံး', 'လာရောက်အများဆုံး'
#     ]

#     restaurant_keywords = [
#         'restaurant', 'food', 'eat', 'dinner', 'lunch', 'breakfast', 'cafe',
#         'စားသောက်ဆိုင်', 'အစားအစာ', 'ထမင်းစား', 'ကော်ဖီဆိုင်', 'စားရမယ့်နေရာ'
#     ]

#     recommendation_keywords = [
#         'recommend', 'recommendation', 'suggest', 'best', 'where should',
#         'what should', 'which place', 'အကြံပြု', 'ဘယ်နေရာသွားရမလဲ', 'ဘာလုပ်ရမလဲ',
#         'သွားသင့်တဲ့နေရာ'
#     ]

#     comparison_keywords = [
#         ' or ', 'compare', 'difference', 'better', 'နှိုင်းယှဉ်', 'ပိုကောင်း'
#     ]

#     follow_up_keywords = [
#         'how much', 'price', 'cost', 'is it', 'what about', 'tell me more',
#         'more about', 'how long', 'when', 'there', 'it', 'that place',
#         'ဘယ်လောက်လဲ', 'ဈေးနှုန်း', 'ထပ်ပြောပါ', 'အဲ့ဒါ', 'အဲဒီနေရာ'
#     ]

#     place_keywords = [
#         'place', 'places', 'visit', 'destination', 'travel', 'go', 'trip',
#         'tourist', 'attraction', 'hotel', 'weather', 'temp', 'temperature',
#         'နေရာ', 'သွားရမယ့်နေရာ', 'ခရီးသွား', 'ရာသီဥတု', 'ဟိုတယ်', 'ခရီးစဉ်'
#     ]

#     # Order matters: specific intents first
#     if any(x in text_lower for x in casual_keywords):
#         return 'casual'
#     if any(x in text_lower for x in top_rated_keywords):
#         return 'top_rated'
#     if any(x in text_lower for x in most_liked_keywords):
#         return 'most_liked'
#     if any(x in text_lower for x in most_viewed_keywords):
#         return 'most_viewed'
#     if any(x in text_lower for x in comparison_keywords):
#         return 'comparison'
#     if any(x in text_lower for x in restaurant_keywords):
#         return 'restaurant_search'
#     if any(x in text_lower for x in recommendation_keywords):
#         return 'recommendation'
#     if any(x in text_lower for x in follow_up_keywords):
#         return 'follow_up'
#     if any(x in text_lower for x in place_keywords):
#         return 'place_search'

#     return 'general'


# def extract_region_from_text(text):
#     """Extract region ID from Burmese or English place names."""
#     text_lower = text.lower()
#     region_map = {
#         'kachin': 1, 'ကချင်': 1,
#         'kayah': 2, 'ကယား': 2,
#         'kayin': 3, 'ကရင်': 3,
#         'chin': 4, 'ချင်း': 4,
#         'sagaing': 5, 'စစ်ကိုင်း': 5,
#         'tanintharyi': 6, 'တနင်္သာရီ': 6,
#         'bago': 7, 'ပဲခူး': 7,
#         'magway': 8, 'မကွေး': 8,
#         'mandalay': 9, 'မန္တလေး': 9,
#         'mon': 10, 'မွန်': 10,
#         'rakhine': 11, 'ရခိုင်': 11, 'ngapali': 11, 'ငပလီ': 11,
#         'yangon': 12, 'ရန်ကုန်': 12,
#         'shan': 13, 'ရှမ်း': 13, 'inle': 13, 'အင်းလေး': 13, 'taunggyi': 13, 'တောင်ကြီး': 13,
#         'ayeyarwady': 14, 'ဧရာဝတီ': 14,
#         'naypyidaw': 15, 'nay pyi taw': 15, 'နေပြည်တော်': 15
#     }
#     for name, r_id in region_map.items():
#         if name in text_lower:
#             return r_id
#     return None


# def fetch_analytical_entities(intent, region_id=None):
#     """Queries DB directly using SQL aggregations for sorting by metrics."""
#     matches = []

#     if intent == 'most_liked':
#         query = db.session.query(Place, func.count(PlaceLike.id).label('like_count'))\
#             .outerjoin(PlaceLike)\
#             .group_by(Place.id)
#         if region_id:
#             query = query.filter(Place.region_id == region_id)
#         results = query.order_by(db.desc('like_count')).limit(5).all()

#         for place, count in results:
#             avg_stars = place.average_rating
#             total_comments = len(place.comments)
#             matches.append({
#                 'type': 'place',
#                 'obj': place,
#                 'desc_short': (place.description or 'N/A')[:150],
#                 'stats': f"{count} Likes, {avg_stars:.1f}/5 Rating, {total_comments} Comments, {place.view_count} Views"
#             })

#     elif intent == 'top_rated':
#         query_p = db.session.query(Place, func.coalesce(func.avg(Rating.stars), 0).label('avg_stars'))\
#             .outerjoin(Rating)\
#             .group_by(Place.id)
#         if region_id:
#             query_p = query_p.filter(Place.region_id == region_id)
#         places_res = query_p.order_by(db.desc('avg_stars')).limit(5).all()

#         for place, avg_s in places_res:
#             likes_count = len(place.likes)
#             total_comments = len(place.comments)
#             matches.append({
#                 'type': 'place',
#                 'obj': place,
#                 'desc_short': (place.description or 'N/A')[:150],
#                 'stats': f"{float(avg_s):.1f}/5 Rating, {likes_count} Likes, {total_comments} Comments"
#             })

#     elif intent == 'most_viewed':
#         query = Place.query
#         if region_id:
#             query = query.filter_by(region_id=region_id)
#         results = query.order_by(Place.view_count.desc()).limit(5).all()

#         for place in results:
#             likes_count = len(place.likes)
#             avg_stars = place.average_rating
#             matches.append({
#                 'type': 'place',
#                 'obj': place,
#                 'desc_short': (place.description or 'N/A')[:150],
#                 'stats': f"{place.view_count} Views, {likes_count} Likes, {avg_stars:.1f}/5 Rating"
#             })

#     # Hydrate matched entities with real-time weather
#     for match in matches:
#         obj = match['obj']
#         lat = getattr(obj, 'latitude', None)
#         lon = getattr(obj, 'longitude', None)
#         live_weather = get_realtime_weather(lat, lon) or get_fallback_weather_for_region(getattr(obj, 'region_id', 12))

#         match['context'] = (
#             f"Type: {match['type'].capitalize()}\n"
#             f"Name: {obj.name}\n"
#             f"Description: {match['desc_short']}\n"
#             f"Stats: {match['stats']}\n"
#             f"Real-Time Weather: {live_weather}"
#         )

#     return matches


# def find_relevant_entities(user_message, places, restaurants):
#     """TF-IDF + KNN search for text/location matching."""
#     entity_features = []
#     entity_data_context = []

#     for place in places:
#         total_likes = len(place.likes) if hasattr(place, 'likes') else 0
#         total_comments = len(place.comments) if hasattr(place, 'comments') else 0
#         avg_rating = place.average_rating

#         desc_short = (place.description or 'N/A')[:150]
#         feature_string = f"{place.name} {getattr(place, 'package', '') or ''} {desc_short} place destination hotel"
#         entity_features.append(feature_string.lower())

#         entity_data_context.append({
#             "type": "place",
#             "obj": place,
#             "desc_short": desc_short,
#             "stats": f"{total_likes} Likes, {avg_rating:.1f}/5 Rating, {total_comments} Comments, {place.view_count} Views"
#         })

#     for restaurant in restaurants:
#         total_comments = len(restaurant.comments) if hasattr(restaurant, 'comments') else 0
#         avg_rating = (sum([r.stars for r in restaurant.ratings]) / len(restaurant.ratings)) if getattr(restaurant, 'ratings', None) else 0

#         desc_short = (restaurant.description or 'N/A')[:150]
#         feature_string = f"{restaurant.name} {desc_short} food restaurant dining"
#         entity_features.append(feature_string.lower())

#         entity_data_context.append({
#             "type": "restaurant",
#             "obj": restaurant,
#             "desc_short": desc_short,
#             "stats": f"{avg_rating:.1f}/5 Rating, {total_comments} Comments"
#         })

#     if not entity_data_context:
#         return []

#     try:
#         from sklearn.feature_extraction.text import TfidfVectorizer
#         from sklearn.neighbors import NearestNeighbors

#         vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2))
#         tfidf_matrix = vectorizer.fit_transform(entity_features)

#         knn = NearestNeighbors(n_neighbors=min(5, len(entity_features)), metric='cosine')
#         knn.fit(tfidf_matrix)

#         user_vec = vectorizer.transform([user_message.lower()])
#         distances, indices = knn.kneighbors(user_vec)

#         raw_matches = [entity_data_context[idx] for idx in indices[0]]

#         final_matches = []
#         for match in raw_matches:
#             obj = match['obj']
#             lat = getattr(obj, 'latitude', None)
#             lon = getattr(obj, 'longitude', None)

#             live_weather = get_realtime_weather(lat, lon) or get_fallback_weather_for_region(getattr(obj, 'region_id', 12))

#             match['context'] = (
#                 f"Type: {match['type'].capitalize()}\n"
#                 f"Name: {obj.name}\n"
#                 f"Description: {match['desc_short']}\n"
#                 f"Stats: {match['stats']}\n"
#                 f"Real-Time Weather: {live_weather}"
#             )
#             final_matches.append(match)

#         return final_matches
#     except Exception as e:
#         print("--> TF-IDF/KNN Match Warning:", str(e))
#         return [entity_data_context[0]]


# def build_context(matches):
#     if not matches:
#         return "No specific entity records matched."
#     context = []
#     for match in matches:
#         context.append(match.get('context', f"Name: {match['obj'].name}"))
#     return "\n---\n".join(context)


# def build_system_prompt(user_message, intent, context_text, matches=None):
#     """System prompt that enforces proper spelling and language matching."""
#     comparison_note = ""
#     if intent == 'comparison' and matches and len(matches) >= 2:
#         comparison_note = (
#             "\n8. The user is asking for a COMPARISON. Compare the top 2 entities side by side "
#             "(pros, cons, stats, weather). Use a short structured format."
#         )

#     return f"""You are 'SmartTrip AI', a helpful and polite travel assistant for Myanmar.

# USER MESSAGE: "{user_message}"
# DETECTED INTENT: {intent}

# DATABASE & METRICS CONTEXT:
# {context_text}

# INSTRUCTIONS:
# 1. Respond in the SAME language as the user's message. If the user writes in Burmese, reply in Burmese. If in English, reply in English.
# 2. Use PROPER spelling, grammar, and punctuation. Do NOT use broken Burmese (Zawgyi-style typos) or misspelled English. If unsure of a Burmese word, use the standard written form.
# 3. State numbers and facts (Likes, Ratings, Views) explicitly as provided in the context data. Do NOT invent numbers.
# 4. If intent is 'top_rated', 'most_liked', or 'most_viewed', present the top matches in exact order from highest to lowest.
# 5. If the context has no relevant data, say so honestly instead of inventing facts.
# 6. Keep answers concise and under 5 sentences (except for comparisons).
# 7. For weather, only report the 'Real-Time Weather' value if present; otherwise say you don't have live weather data.{comparison_note}
# """


# def normalize_text(text):
#     """Normalize Unicode so Burmese text renders correctly (NFC form)."""
#     try:
#         return unicodedata.normalize('NFC', text)
#     except Exception:
#         return text


# def call_groq(system_prompt, user_message, chat_history, require_json=False):
#     """Call Groq API with a valid model name."""
#     groq_api_key = os.environ.get('GROQ_API_KEY')
#     if not groq_api_key:
#         return "AI service is currently unconfigured. (Missing API Key)"

#     messages = [{"role": "system", "content": system_prompt}]
#     for msg in chat_history[-4:]:
#         messages.append({"role": msg["role"], "content": msg["content"][:250]})
#     messages.append({"role": "user", "content": user_message[:300]})

#     payload = {
#         "model": "openai/gpt-oss-120b",  # ✅ Valid Groq model
#         "messages": messages,
#         "temperature": 0.4,                   # ✅ Lower temp = fewer spelling mistakes
#         "max_tokens": 800
#     }

#     if require_json:
#         payload["response_format"] = {"type": "json_object"}

#     try:
#         response = requests.post(
#             "https://api.groq.com/openai/v1/chat/completions",
#             headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_api_key}"},
#             json=payload,
#             timeout=15
#         )
#         res_json = response.json()
#         if 'error' in res_json:
#             return f"AI Error: {res_json['error'].get('message', 'Unknown error')}"
#         return res_json['choices'][0]['message']['content']
#     except Exception as e:
#         print("--> Groq Request Exception:", str(e))
#         return "Sorry, I am having trouble connecting to the AI provider right now."


# # --- MAIN AI ROUTE ---

# @ai_bp.route('/api/chat', methods=['POST'])
# @login_required
# def api_chat():
#     data = request.get_json() or {}
#     user_message = data.get('message', '').strip()

#     if not user_message:
#         return jsonify({'error': 'Message is required'}), 400

#     intent = detect_intent(user_message)
#     save_message('user', user_message)

#     matches = []
#     target_region_id = extract_region_from_text(user_message)

#     # 1. Handle Analytical Intent Queries (Direct SQL Aggregation)
#     if intent in ['most_liked', 'top_rated', 'most_viewed']:
#         matches = fetch_analytical_entities(intent, region_id=target_region_id)

#     # 2. Handle Conversation Follow-ups
#     elif intent == 'follow_up':
#         last_entity = get_last_entity()
#         if last_entity:
#             entity_obj = None
#             if last_entity['type'] == 'place':
#                 entity_obj = Place.query.get(last_entity['id'])
#             elif last_entity['type'] == 'restaurant':
#                 entity_obj = Restaurant.query.get(last_entity['id'])

#             if entity_obj:
#                 lat = getattr(entity_obj, 'latitude', None)
#                 lon = getattr(entity_obj, 'longitude', None)
#                 live_weather = get_realtime_weather(lat, lon) or get_fallback_weather_for_region(getattr(entity_obj, 'region_id', 12))

#                 extra_info = ""
#                 if last_entity['type'] == 'place':
#                     extra_info = f"Region ID: {getattr(entity_obj, 'region_id', 'N/A')}\nViews: {getattr(entity_obj, 'view_count', 0)}"
#                 elif last_entity['type'] == 'restaurant':
#                     extra_info = f"Region ID: {getattr(entity_obj, 'region_id', 'N/A')}"

#                 matches = [{
#                     'type': last_entity['type'],
#                     'obj': entity_obj,
#                     'context': (
#                         f"Type: {last_entity['type'].capitalize()}\n"
#                         f"Name: {entity_obj.name}\n"
#                         f"Description: {(entity_obj.description or 'N/A')[:150]}\n"
#                         f"{extra_info}\n"
#                         f"Real-Time Weather: {live_weather}"
#                     )
#                 }]
#         # If no last entity, fall through to general search

#     # 3. Handle Comparison Intent
#     elif intent == 'comparison':
#         if target_region_id:
#             places = Place.query.filter_by(region_id=target_region_id).all()
#             restaurants = Restaurant.query.filter_by(region_id=target_region_id).all()
#         else:
#             places = Place.query.all()
#             restaurants = Restaurant.query.all()
#         all_matches = find_relevant_entities(user_message, places, restaurants)
#         matches = all_matches[:5] if all_matches else []

#     # 4. Fallback to Vector TF-IDF Search for text/location matching
#     if not matches and intent not in ['casual', 'general']:
#         if target_region_id:
#             places = Place.query.filter_by(region_id=target_region_id).all()
#             restaurants = Restaurant.query.filter_by(region_id=target_region_id).all()
#         else:
#             places = Place.query.all()
#             restaurants = Restaurant.query.all()

#         matches = find_relevant_entities(user_message, places, restaurants)

#     context_str = build_context(matches)
#     system_prompt = build_system_prompt(user_message, intent, context_str, matches=matches)

#     reply = call_groq(system_prompt, user_message, get_conversation_history())
#     reply = normalize_text(reply)  # ✅ Fix Burmese rendering
#     save_message('assistant', reply)

#     suggested_entities = []
#     if matches and intent not in ['casual', 'general']:
#         for match in matches[:5]:
#             suggested_entities.append({
#                 'id': match['obj'].id,
#                 'name': match['obj'].name,
#                 'type': match['type']
#             })
#         save_last_entity(matches[0])

#     return jsonify({
#         'reply': reply,
#         'intent': intent,
#         'suggested_entities': suggested_entities
#     })


# @ai_bp.route('/api/trip/ai-suggest', methods=['POST'])
# @login_required
# def ai_suggest_trip():
#     try:
#         places = Place.query.limit(20).all()
#         restaurants = Restaurant.query.limit(20).all()

#         if not places:
#             return jsonify({
#                 "success": False,
#                 "error": "No places found in the database. Please add some destinations first."
#             }), 400

#         valid_place_ids = [p.id for p in places]

#         fallback_trip = {
#             "title": f"Explore {places[0].name} & Surroundings",
#             "dest_place_id": places[0].id,
#             "waypoints": [{"id": f"place_{p.id}", "name": p.name} for p in places[1:3]]
#         }

#         user_favorites = [f.place.name for f in current_user.favorites if f.place] if hasattr(current_user, 'favorites') else []
#         user_likes = [l.place.name for l in current_user.likes if l.place] if hasattr(current_user, 'likes') else []

#         places_ctx = ", ".join([f"{p.name} (ID: {p.id})" for p in places])
#         rests_ctx = ", ".join([f"{r.name} (ID: {r.id})" for r in restaurants]) if restaurants else "None available"

#         system_prompt = """You are an analytical travel strategist.
#         Analyze preferences and build a trip plan using the provided IDs. You must output in valid JSON.
#         Use proper spelling and grammar in all names and titles."""

#         user_prompt = f"""
#         User's Favorited Places: {', '.join(user_favorites) if user_favorites else 'None'}
#         User's Liked Places: {', '.join(user_likes) if user_likes else 'None'}

#         Available Places: {places_ctx}
#         Available Restaurants: {rests_ctx}

#         Select 1 destination place ID and up to 4 logical waypoints using the exact IDs provided.

#         Respond ONLY with a valid JSON object matching this exact structure:
#         {{
#             "title": "A catchy, relevant trip title",
#             "dest_place_id": <integer_id_from_available_places>,
#             "waypoints": [
#                 {{"id": "place_<id>", "name": "Place Name"}},
#                 {{"id": "restaurant_<id>", "name": "Restaurant Name"}}
#             ]
#         }}
#         """

#         reply = call_groq(system_prompt, user_prompt, chat_history=[], require_json=True)

#         try:
#             json_match = re.search(r'\{.*\}', reply, re.DOTALL)
#             clean_json_str = json_match.group() if json_match else reply

#             trip_data = json.loads(clean_json_str)

#             if not trip_data.get("title"):
#                 trip_data["title"] = fallback_trip["title"]

#             dest_id = trip_data.get("dest_place_id")
#             if dest_id not in valid_place_ids:
#                 trip_data["dest_place_id"] = fallback_trip["dest_place_id"]

#             if not trip_data.get("waypoints") or not isinstance(trip_data["waypoints"], list):
#                 trip_data["waypoints"] = fallback_trip["waypoints"]

#             return jsonify({"success": True, "trip": trip_data})

#         except Exception as parse_err:
#             print("--> JSON Parsing/Healing Fallback Triggered:", str(parse_err))
#             print("--> Raw AI Output was:", reply)
#             return jsonify({"success": True, "trip": fallback_trip})

#     except Exception as e:
#         print("--> AI Trip Generation Error:", str(e))
#         return jsonify({"success": False, "error": str(e)}), 500

import os
import requests
import json
import re
import unicodedata
from flask import Blueprint, request, jsonify, session
from flask_login import login_required, current_user

ai_bp = Blueprint('ai', __name__)

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
    """System prompt for pure Groq API usage (no database context).

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


def call_groq(system_prompt, user_message, chat_history, require_json=False):
    """Call Groq API with a valid model name.

    Uses low temperature to reduce spelling/grammar errors.
    """
    groq_api_key = os.environ.get('GROQ_API_KEY')
    if not groq_api_key:
        return "AI service is currently unconfigured. (Missing API Key)"

    messages = [{"role": "system", "content": system_prompt}]
    for msg in chat_history[-4:]:
        messages.append({"role": msg["role"], "content": msg["content"][:250]})
    messages.append({"role": "user", "content": user_message[:300]})

    payload = {
        "model": "openai/gpt-oss-120b",
        "messages": messages,
        "temperature": 0.2,   # Low temp = fewer spelling/grammar mistakes
        "max_tokens": 800
    }

    if require_json:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {groq_api_key}"},
            json=payload,
            timeout=15
        )
        res_json = response.json()
        if 'error' in res_json:
            return f"AI Error: {res_json['error'].get('message', 'Unknown error')}"
        return res_json['choices'][0]['message']['content']
    except Exception as e:
        print("--> Groq Request Exception:", str(e))
        return "Sorry, I am having trouble connecting to the AI provider right now."


def call_groq_with_validation(system_prompt, user_message, chat_history, require_json=False):
    """Call Groq, then validate spelling/encoding. If broken, retry once with a repair prompt."""
    reply = call_groq(system_prompt, user_message, chat_history, require_json=require_json)
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
        repaired = call_groq(
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


# --- MAIN AI ROUTE (PURE GROQ, NO DATABASE) ---

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

    reply = call_groq_with_validation(
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


# --- AI TRIP SUGGEST ROUTE (PURE GROQ, NO DATABASE) ---

@ai_bp.route('/api/trip/ai-suggest', methods=['POST'])
@login_required
def ai_suggest_trip():
    try:
        # No database access. Ask Groq to generate a trip from general knowledge.
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

        reply = call_groq(system_prompt, user_prompt, chat_history=[], require_json=True)
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