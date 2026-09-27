import os
import re
import json
import math
import requests
from google import genai
from sqlalchemy import or_

from flask import ( 
    Blueprint, request, jsonify, session, render_template, 
    redirect, url_for, flash, current_app ,abort
)
from flask_cors import CORS
from flask_login import login_required, current_user 
from werkzeug.utils import secure_filename
from bs4 import BeautifulSoup










from app.models import (
    db, User, Place, Feedback, Rating, Comment, PlaceLike, 
    Restaurant, RestaurantComment, RestaurantRating, Announcement, 
    Ad, Role, TripPlan, Favorite, Report,TripDay, City,Category,Region
)

user_bp = Blueprint('user', __name__)
CORS(user_bp)


# ============================================================
# OPENSTREETMAP / OSRM CONFIGURATION
# ============================================================

OSRM_BASE_URL = "https://router.project-osrm.org/route/v1/driving"


# ============================================================
# HAVERSINE FALLBACK
# ============================================================


def calculate_haversine_distance_km(
    lat1,
    lng1,
    lat2,
    lng2
):

    earth_radius_km = 6371.0

    lat1 = math.radians(
        float(lat1)
    )

    lng1 = math.radians(
        float(lng1)
    )

    lat2 = math.radians(
        float(lat2)
    )

    lng2 = math.radians(
        float(lng2)
    )

    delta_lat = lat2 - lat1
    delta_lng = lng2 - lng1

    a = (
        math.sin(delta_lat / 2) ** 2
        +
        math.cos(lat1)
        *
        math.cos(lat2)
        *
        math.sin(delta_lng / 2) ** 2
    )

    c = 2 * math.atan2(
        math.sqrt(a),
        math.sqrt(1 - a)
    )

    return round(
        earth_radius_km * c,
        2
    )

def calculate_distance(lat1, lon1, lat2, lon2):
  R = 6371.0  

  lat1_rad = math.radians(lat1)
  lon1_rad = math.radians(lon1)
  lat2_rad = math.radians(lat2)
  lon2_rad = math.radians(lon2)

  dlat = lat2_rad - lat1_rad
  dlon = lon2_rad - lon1_rad

  a = (
      math.sin(dlat / 2) ** 2
      + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2) ** 2
  )
  c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

  distance = R * c
  return distance
    

# ============================================================
# OSRM ROAD DISTANCE
# ============================================================

def get_osrm_route(lat1, lon1, lat2, lon2):
    """
    Get real road-route distance and duration from OSRM.

    OSRM uses OpenStreetMap road network data.

    Returns:
        {
            "distance_km": float,
            "duration_minutes": float,
            "distance_meters": float,
            "duration_seconds": float
        }

    Returns None if OSRM request fails.
    """

    try:

        url = (
            f"{OSRM_BASE_URL}/"
            f"{float(lon1)},{float(lat1)};"
            f"{float(lon2)},{float(lat2)}"
        )

        params = {
            "overview": "false",
            "steps": "false",
            "alternatives": "false"
        }

        headers = {
            "User-Agent": "SmartTrip Travel Planning System/1.0"
        }

        response = requests.get(
            url,
            params=params,
            headers=headers,
            timeout=10
        )

        if response.status_code != 200:
            current_app.logger.warning(
                f"OSRM returned status {response.status_code}"
            )
            return None

        data = response.json()

        if data.get("code") != "Ok":
            current_app.logger.warning(
                f"OSRM error: {data.get('message', 'Unknown error')}"
            )
            return None

        routes = data.get("routes", [])

        if not routes:
            return None

        route = routes[0]

        distance_meters = float(
            route.get("distance", 0)
        )

        duration_seconds = float(
            route.get("duration", 0)
        )

        return {
            "distance_km": round(
                distance_meters / 1000,
                2
            ),

            "distance_meters": round(
                distance_meters,
                2
            ),

            "duration_minutes": round(
                duration_seconds / 60,
                1
            ),

            "duration_seconds": round(
                duration_seconds,
                2
            )
        }

    except (
        requests.RequestException,
        ValueError,
        TypeError,
        KeyError
    ) as e:

        current_app.logger.warning(
            f"OSRM request failed: {str(e)}"
        )

        return None


# ============================================================
# SMART DISTANCE FUNCTION
# ============================================================

def calculate_distance_km(lat1, lon1, lat2, lon2):
    """
    Calculate road distance using OSRM.

    If OSRM is unavailable, use Haversine as fallback.

    Returns:
        distance in kilometers
    """

    route = get_osrm_route(
        lat1,
        lon1,
        lat2,
        lon2
    )

    if route:
        return route["distance_km"]

    # Fallback
    return round(
        calculate_haversine_distance_km(
            lat1,
            lon1,
            lat2,
            lon2
        ),
        2
    )


# ============================================================
# OSRM ROUTE WITH FALLBACK INFORMATION
# ============================================================

def calculate_route_distance(lat1, lon1, lat2, lon2):
    """
    Returns route information.

    OSRM first.
    Haversine fallback if OSRM fails.
    """

    route = get_osrm_route(
        lat1,
        lon1,
        lat2,
        lon2
    )

    if route:

        return {
            "distance_km": route["distance_km"],
            "duration_minutes": route["duration_minutes"],
            "source": "OSRM / OpenStreetMap"
        }

    # Fallback

    distance = calculate_haversine_distance_km(
        lat1,
        lon1,
        lat2,
        lon2
    )

    return {
        "distance_km": round(distance, 2),
        "duration_minutes": None,
        "source": "Haversine fallback"
    }


# ============================================================
# MULTI-STOP ROUTE
# ============================================================

def calculate_multi_route(locations):
    """
    Calculate total road distance for:

    Start
      ↓
    Waypoint 1
      ↓
    Waypoint 2
      ↓
    Destination

    using OSRM.

    locations example:

    [
        {
            "name": "Start",
            "lat": 16.8,
            "lng": 96.1
        },
        {
            "name": "Bagan",
            "lat": 21.17,
            "lng": 94.86
        }
    ]
    """

    if not locations or len(locations) < 2:
        return {
            "distance_km": 0,
            "duration_minutes": 0,
            "segments": []
        }

    total_distance = 0.0
    total_duration = 0.0

    segments = []

    for i in range(len(locations) - 1):

        start = locations[i]
        end = locations[i + 1]

        route = calculate_route_distance(
            start["lat"],
            start["lng"],
            end["lat"],
            end["lng"]
        )

        distance = route["distance_km"]
        duration = route["duration_minutes"]

        total_distance += distance

        if duration:
            total_duration += duration

        segments.append({
            "from": start["name"],
            "to": end["name"],
            "distance_km": distance,
            "duration_minutes": duration,
            "source": route["source"]
        })

    return {
        "distance_km": round(total_distance, 2),
        "duration_minutes": round(total_duration, 1),
        "segments": segments
    }


# ============================================================
# KNN HELPER FUNCTIONS
# ============================================================

def calculate_coordinate_distance(lat1, lon1, lat2, lon2):
    """
    Fast coordinate distance for KNN.

    OSRM is NOT used here because KNN may compare many places.
    """

    return math.hypot(
        float(lat1) - float(lat2),
        float(lon1) - float(lon2)
    )


def get_nearest_places(
    current_lat,
    current_lng,
    all_locations,
    top_n=10
):
    """
    Find nearest places using coordinate distance.
    """

    distances = []

    for loc in all_locations:

        try:

            if loc.get("lat") is None or loc.get("lng") is None:
                continue

            dist = calculate_coordinate_distance(
                current_lat,
                current_lng,
                loc["lat"],
                loc["lng"]
            )

            distances.append(
                (dist, loc)
            )

        except (
            ValueError,
            TypeError
        ):
            continue

    distances.sort(
        key=lambda x: x[0]
    )

    return [
        item[1]
        for item in distances[:top_n]
    ]


# ==========================================
# --- API ROUTES ---
# ==========================================
@user_bp.route("/calculate-budget", methods=["POST"])
@login_required
def calculate_budget():
    try:
        data = request.get_json()
        if not data:
            return (
                jsonify({"status": "error", "message": "Invalid JSON payload"}),
                400,
            )

        city_id = data.get("city_id") or data.get("place_id")
        transport = data.get("transport")
        days = data.get("days", 3)
        people = data.get("people", 1)

        if current_user.latitude is None or current_user.longitude is None:
            return (
                jsonify({
                    "status": "error",
                    "message": "Please save your location from the Dashboard first.",
                }),
                400,
            )

        target_city = City.query.get(city_id)
        if not target_city:
            return jsonify({"status": "error", "message": "Destination city not found"}), 404

        destination_name = target_city.city
        lat = target_city.latitude
        lng = target_city.longitude
        hotel_cost = target_city.hotel_cost or 0.0
        food_cost = target_city.food_cost or 0.0

        distance_km = calculate_distance(
            current_user.latitude,
            current_user.longitude,
            lat,
            lng,
        )

        daily_cost = hotel_cost + food_cost

        return jsonify({
            "status": "success",
            "start_latitude": current_user.latitude,
            "start_longitude": current_user.longitude,
            "destination": destination_name,
            "distance_km": round(distance_km, 2),
            "daily_cost": daily_cost,
            "hotel_cost": hotel_cost,
            "food_cost": food_cost
        })

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@user_bp.route('/api/user/settings', methods=['POST'])
@login_required
def update_settings():
    if 'theme_preference' in request.form:
        current_user.theme_preference = request.form['theme_preference']
    if 'phone' in request.form:
        current_user.phone = request.form['phone']
    if 'bio' in request.form:
        current_user.bio = request.form['bio']
        
    if 'latitude' in request.form and request.form['latitude']:
        try:
            current_user.latitude = float(request.form['latitude'])
        except ValueError:
            pass
            
    if 'longitude' in request.form and request.form['longitude']:
        try:
            current_user.longitude = float(request.form['longitude'])
        except ValueError:
            pass

    if 'profile_pic' in request.files:
        file = request.files['profile_pic']
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            filename = f"user_{current_user.id}_{filename}"
            upload_folder = os.path.join(current_app.root_path, 'static', 'uploads')
            os.makedirs(upload_folder, exist_ok=True)
            file.save(os.path.join(upload_folder, filename))
            current_user.profile_pic = filename

    db.session.commit()
    return jsonify({
        'status': 'success',
        'theme': current_user.theme_preference,
        'profile_pic': current_user.profile_pic
    })

@user_bp.route('/api/user/feedback', methods=['POST'])
@login_required
def submit_feedback():
    data = request.get_json()
    
    feedback_type = data.get('feedback_type')
    subject = data.get('subject')
    message = data.get('message')
    
    if not feedback_type or not subject or not message:
        return jsonify({'status': 'error', 'message': 'All fields are required.'}), 400
        
    try:
        new_feedback = Feedback(
            user_id=current_user.id, 
            feedback_type=feedback_type,
            subject=subject,
            message=message
        )
        db.session.add(new_feedback)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Feedback sent successfully!'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@user_bp.route("/api/bus-search", methods=["GET"])
def bus_search_proxy():
    source_id = request.args.get("sourceId", "Yangon")
    dest_id = request.args.get("destinationId", "Mandalay")
    date = request.args.get("departureDate", "")
    num_seats = request.args.get("numberOfSeats", "1")
    is_foreigner = request.args.get("isForeigner", "false")

    target_url = "https://www.mmbusticket.com/main/tripResultsFragment"
    params = {
        "sourceId": source_id,
        "destId": dest_id,
        "date": date,
        "numSeats": num_seats,
        "isForeigner": is_foreigner,
        "vehicleType": "express",
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.mmbusticket.com/",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        response = requests.get(target_url, params=params, headers=headers, timeout=12)

        if response.status_code != 200:
            return jsonify({
                "success": False,
                "error": f"Upstream server responded with status {response.status_code}."
            }), 502

        soup = BeautifulSoup(response.text, "html.parser")
        trips = []
        trip_cards = soup.select(".trip-result")

        for card in trip_cards:
            logo_img = card.select_one(".operator-logo")
            operator_logo = logo_img.get("src", "") if logo_img else ""
            if operator_logo and not operator_logo.startswith("http"):
                operator_logo = f"https://www.mmbusticket.com{operator_logo}"
            
            op_name_elem = card.select_one(".area-operator-info small, .operator-name")
            operator_name = op_name_elem.get_text(strip=True) if op_name_elem else "Express Operator"
            
            time_elem = card.select_one(".trip-result-content-title .lead")
            departure_time = time_elem.get_text(strip=True) if time_elem else "N/A"
            
            class_elem = card.select_one(".trip-result-content-title span.font-weight-bold")
            bus_class = class_elem.get_text(strip=True) if class_elem else "Standard"
            
            path_elem = card.select_one(".area-trip-info .mt-2 small")
            route_path = path_elem.get_text(strip=True) if path_elem else ""
            
            waypoints = card.select(".waypoint-name")
            boarding_point = waypoints[0].get_text(strip=True) if len(waypoints) > 0 else source_id
            dropping_point = waypoints[1].get_text(strip=True) if len(waypoints) > 1 else dest_id
            
            duration_elem = card.select_one(".bi-clock-history + span")
            duration = duration_elem.get_text(strip=True) if duration_elem else ""
            
            price_elem = card.select_one(".area-action .lead.text-success")
            if price_elem:
                raw_text = price_elem.get_text(separator=" ", strip=True)
                matches = re.findall(r"[\d,]+", raw_text)
                price = f"{matches[0]} MMK" if matches else "N/A"
            else:
                price = "N/A"
                
            features = [
                span.get_text(strip=True)
                for span in card.select(".operator-info-content span span")
                if span.get_text(strip=True)
            ]
            requirements = [
                req.get_text(strip=True)
                for req in card.select(".card-footer .dot-text")
                if req.get_text(strip=True)
            ]
            
            action_btn = card.select_one(".area-action a.btn")
            select_link = action_btn.get("href", "") if action_btn else "javascript:void(0)"
            if select_link and select_link.startswith("/"):
                select_link = f"https://www.mmbusticket.com{select_link}"

            trips.append({
                "operator_name": operator_name,
                "operator_logo": operator_logo,
                "departure_time": departure_time,
                "bus_class": bus_class,
                "route_path": route_path,
                "boarding_point": boarding_point,
                "dropping_point": dropping_point,
                "duration": duration,
                "price": price,
                "features": features,
                "requirements": requirements,
                "select_link": select_link,
            })

        return jsonify({"success": True, "count": len(trips), "trips": trips})

    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route("/api/train-search", methods=["GET"])
def train_search_proxy():
    source_id = request.args.get("sourceId", "")
    dest_id = request.args.get("destinationId", "")
    date = request.args.get("departureDate", "")
    num_seats = request.args.get("numberOfSeats", "1")

    target_url = "https://ortp.railways.gov.mm/search"
    
    params = {
        "from": source_id,
        "to": dest_id,
        "departure_date": date,
        "count": num_seats,
        "children": "0",
        "infants": "0"
    }

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        ),
        "Referer": "https://ortp.railways.gov.mm/",
    }

    try:
        response = requests.get(target_url, params=params, headers=headers, timeout=15)

        if response.status_code != 200:
            return jsonify({
                "success": False,
                "error": f"Upstream server responded with status {response.status_code}."
            }), 502

        soup = BeautifulSoup(response.text, "html.parser")
        trips = []
        trip_cards = soup.select(".main-card")

        for card in trip_cards:
            # -- Extract Logo --
            logo_img = card.select_one(".route-image img")
            operator_logo = logo_img.get("src") if logo_img else "https://ortp.railways.gov.mm/imgs/myanma_train.jpg"

            # -- Extract Timeline Data (Departure & Arrival) --
            timeline_points = card.select(".timeline-circle-group p")
            
            departure_time = "N/A"
            boarding_point = "N/A"
            dropping_point = "N/A"

            # Departure logic
            if len(timeline_points) >= 1:
                dep_text = timeline_points[0].get_text(strip=True).split(',')
                if len(dep_text) >= 3:
                    departure_time = dep_text[0].strip()
                    boarding_point = dep_text[2].strip()

            # Arrival logic
            if len(timeline_points) >= 2:
                arr_text = timeline_points[1].get_text(strip=True).split(',')
                if len(arr_text) >= 3:
                    dropping_point = arr_text[2].strip()

            # -- Extract Duration & Train Class Info --
            duration_elem = card.select_one(".timeline-duration")
            train_details = duration_elem.get_text(separator=" ", strip=True) if duration_elem else "Express Train"

            # -- Extract Price --
            
            price_elem = card.select_one(".search-total h4")
            price_text = "N/A"
            if price_elem:
                raw_price = price_elem.get_text(strip=True)
                price_text = raw_price.replace("ခရီးသည်တစ်ဦးလျှင်", "").replace("မှစတင်၍", "").strip()

            # -- Create the Select Link --
            # Since the official site uses a modal overlay for actual seat maps via hidden CSRF tokens,
            # the safest fallback is routing the user to the generated search URL to finish checking out.
            checkout_url = f"{target_url}?from={source_id}&to={dest_id}&departure_date={date}&count={num_seats}"

            # Append the structured data for the frontend mapping
            trips.append({
                "operator_name": "မြန်မာ့မီးရထား (Myanma Railways)",
                "operator_logo": operator_logo,
                "departure_time": departure_time,
                "bus_class": train_details, 
                "boarding_point": boarding_point,
                "dropping_point": dropping_point,
                "duration": "",
                "price": price_text,
                "select_link": checkout_url,
            })

        return jsonify({"success": True, "count": len(trips), "trips": trips})

    except requests.RequestException as e:
        return jsonify({"success": False, "error": str(e)}), 500

@user_bp.route('/api/user/update-location', methods=['POST'])
@login_required
def update_user_location():
    data = request.get_json() or {}
    lat = data.get('latitude')
    lon = data.get('longitude')

    if lat is not None and lon is not None:
        current_user.latitude = float(lat)
        current_user.longitude = float(lon)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Location updated successfully'})
    
    return jsonify({'status': 'error', 'message': 'Invalid coordinates'}), 400


@user_bp.route('/api/knn/nearest', methods=['POST'])
@login_required
def api_nearest_places():
    """KNN API Endpoint: returns top 5 nearest suggestions"""
    data = request.json or {}
    current_lat = float(data.get('lat', 0.0))
    current_lng = float(data.get('lng', 0.0))
    locations = data.get('locations', [])
    
    nearest = get_nearest_places(current_lat, current_lng, locations, top_n=10)
    return jsonify({'nearest': nearest})


# ==========================================
# --- VIEW ROUTES ---
# ==========================================

@user_bp.route('/user/dashboard', methods=['GET'])
@login_required
def dashboard_page():
    latest_announcement = Announcement.query.order_by(Announcement.id.desc()).first()
    places_query = Place.query.filter(Place.latitude.isnot(None), Place.longitude.isnot(None)).all()
    
    all_locations = [{
        'id': p.id, 'name': p.name, 'description': p.description,
        'package': p.package, 'lat': p.latitude, 'lng': p.longitude
    } for p in places_query]

    nearby_places = []
    if current_user.latitude is not None and current_user.longitude is not None and all_locations:
        nearby_places = get_nearest_places(
            current_lat=current_user.latitude,
            current_lng=current_user.longitude,
            all_locations=all_locations,
            top_n=10
        )

    return render_template(
        'users/pages/overview/dashboard.html', 
        user=current_user, 
        nearby_places=nearby_places,
        announcement=latest_announcement
    )

@user_bp.route('/user/settings', methods=['GET'])
@login_required
def settings_page():
    return render_template('users/pages/prefer/settings.html', user=current_user)

def safe_int(val):
    try:
        return int(val)
    except (TypeError, ValueError):
        return None

@user_bp.route('/user/places', methods=['GET'])
@login_required
def places_page():
    search_query = request.args.get('search', '', type=str)
    category_filter = request.args.get('category', 'all', type=str)
    region_filter = request.args.get('region', 'all', type=str)
    sort_by = request.args.get('sort', 'oldest', type=str)
    page = request.args.get('page', 1, type=int)
    query = Place.query
    if search_query:
        query = query.filter(or_(
            Place.name.ilike(f"%{search_query}%"),
            Place.description.ilike(f"%{search_query}%")
        ))

    cat_id = safe_int(category_filter)
    if cat_id:
        query = query.filter(Place.category_id == cat_id)

    reg_id = safe_int(region_filter)
    if reg_id:
        query = query.filter(Place.region_id == reg_id)

    has_desc = hasattr(Place, 'average_rating') and hasattr(getattr(Place, 'average_rating'), 'desc')
    rating_sort = Place.average_rating.desc() if has_desc else Place.id.asc()

    order_options = {
        'oldest': Place.id.asc(),
        'newest': Place.id.desc(),
        'name_asc': Place.name.asc(),
        'name_desc': Place.name.desc(),
        'rating_desc': rating_sort
    }

    query = query.order_by(order_options.get(sort_by, Place.id.asc()))

    pagination = query.paginate(page=page, per_page=9, error_out=False)

    return render_template(
        'users/pages/overview/places.html',
        user=current_user,
        places=pagination.items,
        pagination=pagination,
        categories=Category.query.all(),
        regions=Region.query.all(),
        search_query=search_query,
        category_filter=category_filter,
        region_filter=region_filter,
        sort_by=sort_by
    )

  # Add this import at the top of your user.py file

# @user_bp.route('/user/pagoda', methods=['GET'])
# @login_required
# def pdd_page():
#     pdd = Pagoda.query.all()  # Changed from 'pagoda' to 'Pagoda' (capitalized)
#     return render_template('users/pages/overview/places.html', user=current_user, pdd=pdd)

# @user_bp.route('/api/pagodas', methods=['GET'])
# @login_required
# def api_pagodas():
#     """API endpoint to fetch pagodas, optionally filtered by township"""
#     try:
#         township = request.args.get('township', '', type=str)
#         search = request.args.get('search', '', type=str)
        
#         query = Pagoda.query
        
#         # Filter by township
#         if township:
#             query = query.filter(Pagoda.township.ilike(f"%{township}%"))
        
#         # Filter by search term (name, address, etc.)
#         if search:
#             query = query.filter(
#                 or_(
#                     Pagoda.pgdName.ilike(f"%{search}%"),
#                     Pagoda.address.ilike(f"%{search}%"),
#                     Pagoda.township.ilike(f"%{search}%")
#                 )
#             )
        
#         # Get all pagodas
#         pagodas = query.all()
        
#         # Format response
#         result = {
#             'pagodas': [
#                 {
#                     'id': p.p_id,
#                     'name': p.pgdName,
#                     'division': p.division,
#                     'district': p.district,
#                     'township': p.township,  # ✅ Included in response
#                     'address': p.address,
#                     'photo': p.photo,
#                     'map_link': p.map_link,
#                     'website': p.website,
#                     'history': p.history
#                 } for p in pagodas
#             ],
#             'total': len(pagodas)
#         }
        
#         return jsonify(result)
        
#     except Exception as e:
#         print(f"Error fetching pagodas: {str(e)}")
#         return jsonify({'error': str(e)}), 500

# @user_bp.route('/api/pagodas/township/<township_name>', methods=['GET'])
# @login_required
# def api_pagodas_by_township(township_name):
#     """Get pagodas by township name"""
#     try:
#         pagodas = Pagoda.query.filter(
#             Pagoda.township.ilike(f"%{township_name}%")
#         ).all()
        
#         return jsonify({
#             'township': township_name,
#             'count': len(pagodas),
#             'pagodas': [
#                 {
#                     'id': p.p_id,
#                     'name': p.pgdName,
#                     'address': p.address,
#                     'map_link': p.map_link,
#                     'photo': p.photo,
#                     'history': p.history[:200] + '...' if len(p.history) > 200 else p.history
#                 } for p in pagodas
#             ]
#         })
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500

# @user_bp.route('/api/townships', methods=['GET'])
# @login_required
# def api_townships():
#     """Get all unique townships from pagodas"""
#     try:
#         townships = db.session.query(Pagoda.township).distinct().all()
#         township_list = [t[0] for t in townships if t[0]]
        
#         return jsonify({
#             'townships': sorted(township_list),
#             'count': len(township_list)
#         })
        
#     except Exception as e:
#         return jsonify({'error': str(e)}), 500


@user_bp.route('/user/places/<int:place_id>/review', methods=['POST'])
@login_required
def add_review(place_id):
    place = Place.query.get_or_404(place_id)
    stars = request.form.get('rating', type=int)
    
    if stars and 1 <= stars <= 5:
        existing_rating = Rating.query.filter_by(user_id=current_user.id, place_id=place.id).first()
        if existing_rating:
            existing_rating.stars = stars
        else:
            new_rating = Rating(user_id=current_user.id, place_id=place.id, stars=stars)
            db.session.add(new_rating)
        db.session.commit()
        flash('Your rating has been submitted successfully!', 'success')
    else:
        flash('Please select a valid rating between 1 and 5 stars.', 'danger')
        
    return redirect(url_for('user.place_detail_page', place_id=place.id))

@user_bp.route('/user/places/<int:place_id>/comment', methods=['POST'])
@login_required
def add_comment(place_id):
    place = Place.query.get_or_404(place_id)
    content = request.form.get('comment_text')
    
    if content and content.strip():
        new_comment = Comment(user_id=current_user.id, place_id=place.id, content=content.strip())
        db.session.add(new_comment)
        db.session.commit()
        flash('Your comment has been posted!', 'success')
    else:
        flash('Comment cannot be empty.', 'danger')
        
    return redirect(url_for('user.place_detail_page', place_id=place.id))

@user_bp.route('/user/places/<int:place_id>/like', methods=['POST'])
@login_required
def toggle_like(place_id):
    place = Place.query.get_or_404(place_id)
    existing_like = PlaceLike.query.filter_by(user_id=current_user.id, place_id=place.id).first()
    
    if existing_like:
        db.session.delete(existing_like)
        db.session.commit()
        liked = False
    else:
        new_like = PlaceLike(user_id=current_user.id, place_id=place.id)
        db.session.add(new_like)
        db.session.commit()
        liked = True
        
    likes_count = PlaceLike.query.filter_by(place_id=place.id).count()
    return jsonify({'success': True, 'liked': liked, 'likes_count': likes_count})

@user_bp.route('/user/places/<int:place_id>', methods=['GET'])
@login_required
def place_detail_page(place_id):
    place = Place.query.get_or_404(place_id)
    place.view_count += 1
    db.session.commit()
    
    user_liked = PlaceLike.query.filter_by(user_id=current_user.id, place_id=place.id).first() is not None
    user_favorited = Favorite.query.filter_by(user_id=current_user.id, place_id=place.id).first() is not None
    
    return render_template(
        'users/pages/overview/placedetail.html', 
        user=current_user,  

        place=place,
        user_liked=user_liked,
        user_favorited=user_favorited
    )

@user_bp.route('/user/places/<int:place_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(place_id):
    place = Place.query.get_or_404(place_id)
    existing_fav = Favorite.query.filter_by(user_id=current_user.id, place_id=place.id).first()
    
    if existing_fav:
        db.session.delete(existing_fav)
        favorited = False
    else:
        new_fav = Favorite(user_id=current_user.id, place_id=place.id)
        db.session.add(new_fav)
        favorited = True
        
    db.session.commit()
    return jsonify({'success': True, 'favorited': favorited})

@user_bp.route('/user/places/<int:place_id>/report', methods=['POST'])
@login_required
def submit_report(place_id):
    place = Place.query.get_or_404(place_id)
    reason = request.form.get('reason')
    details = request.form.get('details')
    
    if reason:
        report = Report(user_id=current_user.id, place_id=place.id, reason=reason, details=details)
        db.session.add(report)
        db.session.commit()
        flash('Your report has been submitted successfully and will be reviewed.', 'success')
    else:
        flash('Please select a reason for reporting.', 'danger')
        
    return redirect(url_for('user.place_detail_page', place_id=place_id))

@user_bp.route('/user/trending', methods=['GET'])
@login_required
def trending_page():
    places = Place.query.all()
    return render_template('users/pages/overview/trending.html', user=current_user, places=places)   

@user_bp.route('/user/smart-map', methods=['GET'])
@login_required
def smart_map_page():
    places_query = Place.query.all()
    all_locations = [{
        'id': p.id, 'name': p.name, 'latitude': p.latitude or 0.0,
        'longitude': p.longitude or 0.0, 'lat': p.latitude or 0.0, 
        'lng': p.longitude or 0.0, 'description': p.description or '',
        'phone_number': p.phone_number or 'Not Available',
        'package': p.package or 'Standard Booking',
        'image_file': p.image_file or 'default.jpg',
        'likes_count': len(p.likes)
    } for p in places_query]

    nearest_place = None
    if current_user.latitude is not None and current_user.longitude is not None and all_locations:
        nearest_list = get_nearest_places(current_user.latitude, current_user.longitude, all_locations, top_n=1)
        if nearest_list:
            nearest_place = nearest_list[0]

    total_favorites = PlaceLike.query.count() + Favorite.query.count()

    return render_template(
        'users/pages/overview/map.html', 
        user=current_user, 
        places=all_locations,
        nearest_place=nearest_place,
        total_favorites=total_favorites
    )    

@user_bp.route('/user/announcements', methods=['GET'])
@login_required
def announcements_page():
    announcements = Announcement.query.order_by(Announcement.created_at.desc()).all()
    return render_template('users/pages/overview/announcements.html', user=current_user, announcements=announcements)

@user_bp.route('/SmartTripProject/users/generate')
def generate():
    return render_template('users/generate.html')

@user_bp.route('/SmartTripProject/users/budgetCal')
def budgetCal():
    return render_template('users/budgetCal.html')

@user_bp.route('/user/weather', methods=['GET'])
@login_required
def weather_page():
    return render_template('users/pages/travel/weather.html', user=current_user)

@user_bp.route('/user/calculator', methods=['GET'])
@login_required
def calculator_page():
    cities = City.query.order_by(City.city.asc()).all()
    return render_template('users/pages/tool/calculator.html', user=current_user, cities=cities)


@user_bp.route('/user/budget', methods=['GET'])
@login_required
def reverse_calculator_page():
    places = Place.query.all()
    return render_template('users/pages/tool/re_calculator.html', user=current_user, places=places)

@user_bp.route('/user/trip/save-draft', methods=['POST'])
@login_required
def save_trip_draft():
    """Stores initial trip selection in Flask Session."""
    data = request.get_json()
    if not data:
        return jsonify({'status': 'error', 'message': 'Invalid data'}), 400

    session['draft_trip'] = {
        'dest_place_id': data.get('dest_place_id'),
        'dest_name': data.get('dest_name'),
        'days': int(data.get('days', 1)),
        'people': int(data.get('people', 1)),
        'user_budget': float(data.get('user_budget', 0)),
        'transport_name': data.get('transport_name'),
        'transport_cost': float(data.get('transport_cost', 0)),
        'package': data.get('package', 'General'),
        'lat': float(data.get('lat', 0.0)),
        'lng': float(data.get('lng', 0.0))
    }
    
    return jsonify({
        'status': 'success',
        'redirect_url': url_for('user.itinerary_builder_page')
    })


@user_bp.route('/user/trip/itinerary', methods=['GET'])
@login_required
def itinerary_builder_page():
    """Renders the itinerary builder page using session data."""
    draft_trip = session.get('draft_trip')
    if not draft_trip:
        flash("Please select a destination first.", "warning")
        return redirect(url_for('user.reverse_calculator_page'))
        
    return render_template('users/pages/tool/itinerary_builder.html', user=current_user, trip=draft_trip)


@user_bp.route('/user/ai', methods=['GET'])
@login_required
def ai_page():
    return render_template('users/pages/tool/ai.html', user=current_user)

@user_bp.route('/user/itineraries', methods=['GET'])
@login_required
def itineraries_page():
    places = Place.query.all()
    # restaurants = Restaurant.query.all()

    locations_dict = {}
    for p in places:
        locations_dict[f"place_{p.id}"] = {
            'id': p.id, 'name': p.name, 'lat': p.latitude or 0.0,
            'lng': p.longitude or 0.0, 'type': 'place'
        }
    # for r in restaurants:
    #     locations_dict[f"restaurant_{r.id}"] = {
    #         'id': r.id, 'name': f"🍽️ {r.name}", 'lat': r.latitude or 0.0,
    #         'lng': r.longitude or 0.0, 'type': 'restaurant'
    #     }

    user_trips = TripPlan.query.filter_by(user_id=current_user.id).order_by(TripPlan.created_at.desc()).all()
    trips_data = []

    for trip in user_trips:
        waypoint_keys = []
        if trip.waypoints_json:
            try:
                waypoint_keys = json.loads(trip.waypoints_json)
            except (json.JSONDecodeError, TypeError):
                pass

        waypoint_places = []
        for key in waypoint_keys:
            str_key = str(key)
            if str_key in locations_dict:
                waypoint_places.append(locations_dict[str_key])
            elif f"place_{str_key}" in locations_dict:
                waypoint_places.append(locations_dict[f"place_{str_key}"])

        dest_key = f"place_{trip.dest_place_id}" if trip.dest_place_id else None
        dest_place = locations_dict.get(dest_key) if dest_key else None

        trips_data.append({
            'id': trip.id,
            'title': trip.title or 'Unnamed Trip',
            'created_at': trip.created_at.strftime('%b %d, %Y') if trip.created_at else 'Recent',
            'start_lat': trip.start_lat or (current_user.latitude if current_user.latitude else 16.8661),
            'start_lng': trip.start_lng or (current_user.longitude if current_user.longitude else 96.1951),
            'waypoints': waypoint_places,
            'destination': dest_place
        })

    return render_template(
        'users/pages/tool/itineraries.html',
        user=current_user,
        trips=trips_data,
        trips_json=json.dumps(trips_data)
    )


@user_bp.route('/trip/create', methods=['GET', 'POST'])
@login_required
def create_trip():

    if request.method == 'POST':

        try:
            title = request.form.get('title')

            start_lat = float(
                request.form.get('start_lat')
            )

            start_lng = float(
                request.form.get('start_lng')
            )

            dest_place_id = int(
                request.form.get('dest_place_id')
            )

            # Selected waypoints
            waypoints = request.form.getlist(
                'waypoints[]'
            )

            # ----------------------------------------
            # Create Trip
            # ----------------------------------------

            new_trip = TripPlan(
                user_id=current_user.id,
                title=title,
                start_lat=start_lat,
                start_lng=start_lng,
                dest_place_id=dest_place_id,
                waypoints_json=json.dumps(waypoints)
            )

            db.session.add(new_trip)
            db.session.commit()

            # ----------------------------------------
            # Go directly to Budget Page
            # ----------------------------------------

            return redirect(
                url_for(
                    'user.trip_budget',
                    trip_id=new_trip.id
                )
            )

        except Exception as e:

            db.session.rollback()

            flash(
                f'Error creating trip: {str(e)}',
                'danger'
            )

            return redirect(
                url_for('user.create_trip')
            )

    # ============================================
    # GET REQUEST
    # ============================================

    places = Place.query.all()
    # restaurants = Restaurant.query.all()

    locations = []

    # --------------------------------------------
    # Places
    # --------------------------------------------

    for p in places:

        locations.append({
            'id': f'place_{p.id}',
            'real_id': p.id,
            'name': p.name,
            'lat': p.latitude,
            'lng': p.longitude,
            'type': 'place'
        })

    # --------------------------------------------
    # Restaurants
    # --------------------------------------------

    # for r in restaurants:

    #     locations.append({
    #         'id': f'restaurant_{r.id}',
    #         'real_id': r.id,
    #         'name': f'🍽️ {r.name}',
    #         'lat': r.latitude,
    #         'lng': r.longitude,
    #         'type': 'restaurant'
    #     })

    return render_template(
        'users/pages/tool/create_trip.html',
        user=current_user,
        locations=locations,
        locations_json=json.dumps(locations)
    )



@user_bp.route('/trip/edit/<int:trip_id>', methods=['GET', 'POST'])
@login_required
def edit_trip(trip_id):
    trip = TripPlan.query.get_or_404(trip_id)
    
    if trip.user_id != current_user.id:
        abort(403)
        
    if request.method == 'POST':
        trip.title = request.form.get('title')
        trip.start_lat = float(request.form.get('start_lat'))
        trip.start_lng = float(request.form.get('start_lng'))
        trip.dest_place_id = int(request.form.get('dest_place_id'))
        waypoints = request.form.getlist('waypoints[]')
        trip.waypoints_json = json.dumps(waypoints)
        
        db.session.commit()
        return redirect(url_for('user.itineraries_page'))

    places = Place.query.all()
    restaurants = Restaurant.query.all()
    
    locations = []
    for p in places:
        locations.append({
            'id': f"place_{p.id}", 'real_id': p.id, 'name': p.name,
            'lat': p.latitude, 'lng': p.longitude, 'type': 'place'
        })
    for r in restaurants:
        locations.append({
            'id': f"restaurant_{r.id}", 'real_id': r.id, 'name': f"🍽️ {r.name}",
            'lat': r.latitude, 'lng': r.longitude, 'type': 'restaurant'
        })

    existing_waypoints = json.loads(trip.waypoints_json) if trip.waypoints_json else []

    return render_template(
        'users/pages/tool/edit_trip.html', 
        user=current_user, 
        trip=trip,
        existing_waypoints=existing_waypoints,
        locations=locations, 
        locations_json=json.dumps(locations)
    )


@user_bp.route('/user/events', methods=['GET'])
@login_required
def events_page():
    return render_template('users/pages/travel/events.html', user=current_user)

@user_bp.route('/user/transportation', methods=['GET'])
@login_required
def transportation_page():
    places = Place.query.all()
    return render_template('users/pages/travel/transportation.html', user=current_user, places=places)

@user_bp.route('/user/train', methods=['GET'])
@login_required
def train_page():
    places = Place.query.all()
    return render_template('users/pages/travel/train.html', user=current_user, places=places)

@user_bp.route('/user/restaurant', methods=['GET'])
@login_required
def restaurant_page():
    restaurants = Restaurant.query.all()
    return render_template('users/pages/travel/restaurants.html', user=current_user, restaurants=restaurants)

@user_bp.route('/user/restaurant/<int:restaurant_id>', methods=['GET'])
@login_required
def restaurant_detail_page(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    return render_template('users/pages/travel/restaurant_detail.html', user=current_user, restaurant=restaurant)

@user_bp.route('/user/restaurant/<int:restaurant_id>/review', methods=['POST'])
@login_required
def add_restaurant_review(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    stars = request.form.get('rating', type=int)
    
    if stars and 1 <= stars <= 5:
        existing_rating = RestaurantRating.query.filter_by(user_id=current_user.id, restaurant_id=restaurant.id).first()
        if existing_rating:
            existing_rating.stars = stars
        else:
            new_rating = RestaurantRating(user_id=current_user.id, restaurant_id=restaurant.id, stars=stars)
            db.session.add(new_rating)
        db.session.commit()
        flash('Your rating has been submitted successfully!', 'success')
    else:
        flash('Please select a valid rating between 1 and 5 stars.', 'danger')
        
    return redirect(url_for('user.restaurant_detail_page', restaurant_id=restaurant.id))

@user_bp.route('/user/restaurant/<int:restaurant_id>/comment', methods=['POST'])
@login_required
def add_restaurant_comment(restaurant_id):
    restaurant = Restaurant.query.get_or_404(restaurant_id)
    content = request.form.get('comment_text')
    
    if content and content.strip():
        new_comment = RestaurantComment(user_id=current_user.id, restaurant_id=restaurant.id, content=content.strip())
        db.session.add(new_comment)
        db.session.commit()
        flash('Your comment has been posted!', 'success')
    else:
        flash('Comment cannot be empty.', 'danger')
        
    return redirect(url_for('user.restaurant_detail_page', restaurant_id=restaurant.id))

@user_bp.route('/user/help', methods=['GET'])
@login_required
def need_help_page():
    return render_template('users/pages/prefer/needhelp.html', user=current_user)

@user_bp.route('/user/feedback')
@login_required 
def feedback_page():
    return render_template('users/pages/prefer/feedback.html', user=current_user)

@user_bp.route('/my/profile')
@login_required
def my_profile():
    return render_template('users/profile.html', user=current_user) 

@user_bp.route('/my/change-password', methods=['GET'])
@login_required
def change_password_page():
    return render_template('users/change_password.html', user=current_user)

@user_bp.route('/my-plans')
@login_required
def my_plans():
    trips = TripPlan.query.filter_by(user_id=current_user.id)\
        .join(Place, TripPlan.dest_place_id == Place.id)\
        .order_by(TripPlan.created_at.desc()).all()
        
    # 💰 Trip တစ်ခုစီ၏ ခန့်မှန်းကုန်ကျစရိတ်နှင့် စုစုပေါင်း Budget ကို တွက်ချက်ခြင်း
    trip_data = []
    total_budget = 0.0
    
    for trip in trips:
        # ဥပမာ - Destination ရဲ့ base_price_per_day နှင့် taxi_fare ကို ပေါင်းစပ်တွက်ချက်ခြင်း
        trip_cost = 0.0
        if trip.destination:
            trip_cost = trip.destination.base_price_per_day + trip.destination.taxi_fare
            
        total_budget += trip_cost
        trip_data.append({
            'trip': trip,
            'budget': trip_cost
        })
        
    return render_template('users/my_plans.html', trip_data=trip_data, total_budget=total_budget)

@user_bp.route('/my-reviews')
@login_required
def my_reviews():
    place_reviews = Rating.query.filter_by(user_id=current_user.id)\
        .join(Place).order_by(Rating.stars.desc()).all()
    restaurant_reviews = RestaurantRating.query.filter_by(user_id=current_user.id)\
        .join(Restaurant).order_by(RestaurantRating.stars.desc()).all()
        
    return render_template(
        'users/my_reviews.html', 
        place_reviews=place_reviews, 
        restaurant_reviews=restaurant_reviews
    )

@user_bp.route('/my-favorites')
@login_required
def my_favorites():
    favorites = Favorite.query.filter_by(user_id=current_user.id)\
        .join(Place)\
        .order_by(Favorite.created_at.desc()).all()
        
    return render_template('users/my_favorites.html', favorites=favorites)

@user_bp.route('/api/knn/live-search', methods=['POST'])
@login_required
def api_live_search():
    """New Live Search & KNN API Endpoint for the Itinerary Builder"""
    data = request.json or {}
    current_lat = float(data.get('lat', 0.0))
    current_lng = float(data.get('lng', 0.0))
    search_query = data.get('query', '').strip().lower()
    limit = int(data.get('limit', 6))
    
    places = Place.query.all()
    restaurants = Restaurant.query.all()
    results = []

    for p in places:
        if p.latitude and p.longitude:
            if search_query and search_query not in p.name.lower():
                continue
            dist = calculate_distance(current_lat, current_lng, p.latitude, p.longitude)
            results.append({
                'id': f"place_{p.id}",
                'real_id': p.id,
                'name': p.name,
                'lat': p.latitude,
                'lng': p.longitude,
                'type': 'place',
                'distance_km': round(dist, 2)
            })

    # Search Restaurants
    for r in restaurants:
        if r.latitude and r.longitude:
            if search_query and search_query not in r.name.lower():
                continue
            dist = calculate_distance(current_lat, current_lng, r.latitude, r.longitude)
            results.append({
                'id': f"restaurant_{r.id}",
                'real_id': r.id,
                'name': f"🍜 {r.name}",
                'lat': r.latitude,
                'lng': r.longitude,
                'type': 'restaurant',
                'distance_km': round(dist, 2)
            })

    # Sort by nearest distance
    results.sort(key=lambda x: x['distance_km'])
   
    
    return jsonify({'locations': results[:limit]})

@user_bp.route('/trip/confirm', methods=['POST'])
@login_required 
def confirm_trip():
    try:
        data = request.get_json() or {}
        
        daily_plans = data.get('daily_plans', {})
        waypoints = []

        if daily_plans and isinstance(daily_plans, dict):
            sorted_days = sorted(daily_plans.keys(), key=lambda x: int(x))
            for day_num in sorted_days:
                activities = daily_plans[day_num]
                for act in activities:
                    if isinstance(act, dict) and 'id' in act:
                        waypoints.append(act['id'])
                    elif isinstance(act, str):
                        waypoints.append(act)

        if not waypoints:
            return jsonify({'status': 'error', 'message': 'Please add at least one stop to your trip.'}), 400

        final_waypoint = waypoints[-1]
        
        if final_waypoint.startswith('place_'):
            dest_place_id = int(final_waypoint.split('_')[1])
        else:
            dest_place_id = data.get('dest_place_id')

        if not dest_place_id:
            return jsonify({'status': 'error', 'message': 'Final destination ID could not be determined'}), 400

        new_trip = TripPlan(
            user_id=current_user.id, 
            title=str(data.get('title', 'Saved Destination')),
            dest_place_id=int(dest_place_id), 
            start_lat=float(data.get('start_lat', 0.0)),
            start_lng=float(data.get('start_lng', 0.0)),
            total_budget=float(data.get('total_budget', 0.0)),
            total_days=int(data.get('days_count', 1)),
            waypoints_json=json.dumps(waypoints) 
        )
        db.session.add(new_trip)
        db.session.flush() 
        
        if daily_plans and isinstance(daily_plans, dict):
            for day_num, activities in daily_plans.items():
                if not activities:
                    continue

                trip_day = TripDay(
                    trip_id=new_trip.id,
                    day_number=int(day_num),
                    activities_json=json.dumps(activities)
                )
                db.session.add(trip_day)

        db.session.commit()
        return jsonify({'status': 'success', 'trip_id': new_trip.id})

    except Exception as e:
        db.session.rollback()
        print(f" Error saving trip: {str(e)}") 
        return jsonify({'status': 'error', 'message': f'Server Error: {str(e)}'}), 500




# Gemini API ကို configure လုပ်ပါ (Environment variable မှ Key ယူမည်)



client = genai.Client(api_key=GOOGLE_API_KEY)
if not GOOGLE_API_KEY:
    print("WARNING: GEMINI_API_KEY not found in environment variables.")
else:
    print("GEMINI_API_KEY loaded successfully.")
@user_bp.route('/api/generate-itinerary', methods=['POST','GET'])
@login_required
def generate_itinerary():
    if request.method == 'GET':
        # Browser ကနေ တိုက်ရိုက် လာကြည့်ရင် သို့မဟုတ် 
        # ဒီ URL ကို render လုပ်ရမယ့် HTML page ရှိရင် ပြန်ပေးရန်
        return render_template('users/generate.html')
    try:
        data = request.get_json() or {}
        origin = data.get('origin')
        destination = data.get('destination')
        days = data.get('days', 3)
        
        if not origin or not destination:
            return jsonify({'status': 'error', 'message': 'Origin and destination are required'}), 400

        # Gemini AI Prompt ကို တည်ဆောက်ခြင်း
        prompt = f"""
        Act as a professional travel guide and tour planner for Myanmar. 
        Create a detailed {days}-day travel itinerary for a trip from {origin} to {destination}.
        Provide the response strictly as a valid JSON object without any markdown code blocks (like ```json), matching this exact structure:
        {{
            "destination": "{destination}",
            "days_count": {days},
            "estimated_transport_cost": "e.g., Express Bus: 25,000 MMK",
            "local_transport_cost": "e.g., Trishaw/Tuk-Tuk: 5,000 MMK per day",
            "hotels": [
                {{"name": "Hotel Name", "price_range": "Price per night", "description": "Short description"}}
            ],
            "restaurants": [
                {{"name": "Restaurant Name", "specialty": "Food specialty", "description": "Short description"}}
            ],
            "attractions": [
                {{"name": "Place Name", "description": "What to see here"}}
            ],
            "itinerary": [
                {{"day": 1, "title": "Day 1 Theme", "activities": ["Activity 1", "Activity 2"]}}
            ]
        }}
        """

        # Google GenAI SDK အသစ်ဖြင့် Content Generate လုပ်ခြင်း
        response = client.models.generate_content(
            model='gemini-3.6-flash', # သို့မဟုတ် gemini-1.5-flash
            contents=prompt,
        )
        
        # Clean response text to ensure valid JSON
        raw_text = response.text.strip()
        if raw_text.startswith("```json"):
            raw_text = raw_text[7:]
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3]
            
        itinerary_data = json.loads(raw_text.strip())

        return jsonify({
            'status': 'success',
            'data': itinerary_data
        })

    except Exception as e:
        print(f"Gemini Itinerary Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500