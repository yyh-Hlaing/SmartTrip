# SmartTrip — User Side Routes and KNN Recommendation Documentation

## 1. Overview

The SmartTrip user module provides the main functionality available to authenticated users. It handles:

* User settings and profile management
* User feedback
* Location tracking
* Nearby place recommendations
* KNN-based location recommendations
* Places and destination browsing
* Reviews, ratings, comments, likes, favorites, and reports
* Trip itinerary creation
* Saved trip plans
* Restaurants and restaurant reviews
* Transportation and bus searching
* Weather
* Events
* AI travel assistant
* Announcements
* Travel calculator
* User profile and password pages

The user routes are implemented using the Flask Blueprint:

```python
user_bp = Blueprint('user', __name__)
```

Most user-facing routes are protected by:

```python
@login_required
```

This means users must be authenticated before accessing those pages or APIs.

---

# 2. User-Side Route Structure

The user routes can be divided into several functional groups.

## 2.1 User API Routes

| Method | Route                       | Purpose                                                                  |
| ------ | --------------------------- | ------------------------------------------------------------------------ |
| POST   | `/api/user/settings`        | Update user settings, profile information, location, and profile picture |
| POST   | `/api/user/feedback`        | Submit feedback                                                          |
| GET    | `/api/bus-search`           | Search bus trips through the external bus-ticket website                 |
| POST   | `/api/user/update-location` | Save the user's current latitude and longitude                           |
| POST   | `/api/knn/nearest`          | Calculate nearest locations using KNN                                    |

---

# 3. Dashboard Routes

## 3.1 Dashboard

```text
GET /user/dashboard
```

Function:

```python
def dashboard_page():
```

The dashboard performs the following operations:

1. Gets the latest announcement.
2. Gets all places with valid latitude and longitude.
3. Converts database records into location dictionaries.
4. Checks whether the user has a stored location.
5. Runs the KNN algorithm if the user's location exists.
6. Returns the top 5 nearest places.
7. Sends the results to the dashboard template.

The important part is:

```python
nearby_places = []

if current_user.latitude is not None \
        and current_user.longitude is not None \
        and all_locations:

    nearby_places = get_nearest_places(
        current_lat=current_user.latitude,
        current_lng=current_user.longitude,
        all_locations=all_locations,
        top_n=5
    )
```

Therefore, the dashboard uses KNN to provide **nearby place recommendations**.

---

# 4. User Settings

## 4.1 Settings Page

```text
GET /user/settings
```

Function:

```python
def settings_page():
```

Displays the user's settings page.

---

## 4.2 Update Settings API

```text
POST /api/user/settings
```

Function:

```python
def update_settings():
```

This endpoint updates:

* Theme preference
* Phone number
* Bio
* Latitude
* Longitude
* Profile picture

### Location update

The endpoint accepts:

```text
latitude
longitude
```

and stores them in the `User` table.

Example:

```python
current_user.latitude = float(request.form['latitude'])
current_user.longitude = float(request.form['longitude'])
```

The stored coordinates are later used by the KNN recommendation system.

---

# 5. Location Update

```text
POST /api/user/update-location
```

Function:

```python
def update_user_location():
```

This endpoint receives JSON:

```json
{
    "latitude": 16.8661,
    "longitude": 96.1951
}
```

The values are stored in:

```python
current_user.latitude
current_user.longitude
```

After updating the database:

```python
db.session.commit()
```

the user's location becomes available to the KNN recommendation system.

---

# 6. Places Routes

## 6.1 Places List

```text
GET /user/places
```

Function:

```python
def places_page():
```

Loads all places:

```python
places = Place.query.all()
```

and displays them in the places page.

---

## 6.2 Place Details

```text
GET /user/places/<place_id>
```

Function:

```python
def place_detail_page(place_id):
```

This page displays information about a specific place.

It also increments the view count:

```python
place.view_count += 1
db.session.commit()
```

The route checks whether the current user has:

* Liked the place
* Favorited the place

These values are passed to the template:

```python
user_liked=user_liked,
user_favorited=user_favorited
```

---

# 7. Place Reviews

## 7.1 Add Place Rating

```text
POST /user/places/<place_id>/review
```

Function:

```python
def add_review(place_id):
```

Users can give a rating from 1 to 5.

```python
if stars and 1 <= stars <= 5:
```

If the user already rated the place, the existing rating is updated.

Otherwise, a new `Rating` record is created.

---

## 7.2 Add Place Comment

```text
POST /user/places/<place_id>/comment
```

Function:

```python
def add_comment(place_id):
```

Users can submit comments about a place.

Empty comments are rejected.

---

# 8. Place Likes and Favorites

## 8.1 Like / Unlike Place

```text
POST /user/places/<place_id>/like
```

Function:

```python
def toggle_like(place_id):
```

The function checks whether the current user already likes the place.

If a like exists:

```python
db.session.delete(existing_like)
```

Otherwise:

```python
new_like = PlaceLike(
    user_id=current_user.id,
    place_id=place.id
)
```

The API returns:

```json
{
    "success": true,
    "liked": true,
    "likes_count": 10
}
```

---

## 8.2 Favorite / Unfavorite Place

```text
POST /user/places/<place_id>/favorite
```

Function:

```python
def toggle_favorite(place_id):
```

This works similarly to the like functionality but uses the `Favorite` model.

---

# 9. Report Place

```text
POST /user/places/<place_id>/report
```

Function:

```python
def submit_report(place_id):
```

Users can report inappropriate or incorrect place information.

The report contains:

* User
* Place
* Reason
* Details

---

# 10. Trending

```text
GET /user/trending
```

Function:

```python
def trending_page():
```

Loads all places and displays them on the trending page.

At the current implementation level, the route retrieves:

```python
places = Place.query.all()
```

The actual ranking of trending places should therefore be handled by the template or can be improved later using views, likes, ratings, or popularity scores.

---

# 11. Smart Map

```text
GET /user/smart-map
```

Function:

```python
def smart_map_page():
```

This is one of the important routes for location-based functionality.

The route loads places and converts them into map-friendly dictionaries.

Example:

```python
{
    'id': p.id,
    'name': p.name,
    'latitude': p.latitude or 0.0,
    'longitude': p.longitude or 0.0,
    'lat': p.latitude or 0.0,
    'lng': p.longitude or 0.0,
    'description': p.description or '',
    'phone_number': p.phone_number or 'Not Available',
    'package': p.package or 'Standard Booking',
    'image_file': p.image_file or 'default.jpg',
    'likes_count': len(p.likes)
}
```

The route also finds the nearest place.

```python
nearest_list = get_nearest_places(
    current_user.latitude,
    current_user.longitude,
    all_locations,
    top_n=1
)
```

Therefore:

* Dashboard → top 5 nearest places
* Smart Map → nearest place

Both use the same KNN helper function.

---

# 12. Announcements

```text
GET /user/announcements
```

Function:

```python
def announcements_page():
```

Announcements are retrieved in descending creation order:

```python
Announcement.query.order_by(
    Announcement.created_at.desc()
).all()
```

The newest announcement appears first.

---

# 13. Weather

```text
GET /user/weather
```

Function:

```python
def weather_page():
```

Displays the weather page.

The actual weather API functionality can be implemented in the frontend or through a separate API.

---

# 14. Travel Calculator

```text
GET /user/calculator
```

Function:

```python
def calculator_page():
```

Loads places and sends them to the calculator page.

---

# 15. AI Travel Assistant

```text
GET /user/ai
```

Function:

```python
def ai_page():
```

Displays the SmartTrip AI assistant interface.

---

# 16. Itinerary System

## 16.1 Itinerary List

```text
GET /user/itineraries
```

Function:

```python
def itineraries_page():
```

This route loads:

* Places
* Restaurants
* User's saved trip plans

The route creates a unified location dictionary.

Example:

```python
locations_dict[f"place_{p.id}"] = {
    'id': p.id,
    'name': p.name,
    'lat': p.latitude or 0.0,
    'lng': p.longitude or 0.0,
    'type': 'place'
}
```

Restaurants use:

```python
locations_dict[f"restaurant_{r.id}"]
```

The route then loads only the current user's trips:

```python
TripPlan.query.filter_by(
    user_id=current_user.id
)
```

---

## 16.2 Create Trip

```text
GET /trip/create
POST /trip/create
```

Function:

```python
def create_trip():
```

### GET

Loads available places and restaurants.

### POST

Creates a new `TripPlan`.

The saved information includes:

* User ID
* Trip title
* Starting latitude
* Starting longitude
* Destination
* Waypoints

Waypoints are stored as JSON:

```python
waypoints_json=json.dumps(waypoints)
```

After saving:

```python
return redirect(url_for('user.itineraries_page'))
```

---

# 17. Events

```text
GET /user/events
```

Function:

```python
def events_page():
```

Displays the travel events page.

---

# 18. Transportation

```text
GET /user/transportation
```

Function:

```python
def transportation_page():
```

Loads places and displays transportation-related functionality.

---

# 19. Bus Search API

```text
GET /api/bus-search
```

Function:

```python
def bus_search_proxy():
```

This route acts as a backend proxy between SmartTrip and:

```text
mmbusticket.com
```

The user can provide:

* Source
* Destination
* Departure date
* Number of seats
* Foreigner status

The backend sends a request to the external website using:

```python
requests.get(...)
```

BeautifulSoup then parses the HTML response.

The route extracts:

* Operator name
* Operator logo
* Departure time
* Bus class
* Route
* Boarding point
* Dropping point
* Duration
* Price
* Features
* Requirements
* Selection URL

The result is returned as JSON.

---

# 20. Restaurant Routes

## Restaurant List

```text
GET /user/restaurant
```

Loads all restaurants.

---

## Restaurant Details

```text
GET /user/restaurant/<restaurant_id>
```

Displays a specific restaurant.

---

## Restaurant Rating

```text
POST /user/restaurant/<restaurant_id>/review
```

Allows users to rate restaurants from 1 to 5.

---

## Restaurant Comment

```text
POST /user/restaurant/<restaurant_id>/comment
```

Allows users to comment on restaurants.

---

# 21. Help and Feedback

## Help

```text
GET /user/help
```

Displays the help page.

## Feedback Page

```text
GET /user/feedback
```

Displays the feedback form.

## Submit Feedback

```text
POST /api/user/feedback
```

Stores user feedback in the `Feedback` table.

Required fields:

```text
feedback_type
subject
message
```

---

# 22. User Profile

## Profile

```text
GET /my/profile
```

Displays the user's profile.

## Change Password

```text
GET /my/change-password
```

Displays the change-password page.

---

# 23. Personal User Data

## My Plans

```text
GET /my-plans
```

Retrieves the current user's trip plans.

```python
TripPlan.query.filter_by(
    user_id=current_user.id
)
```

---

## My Reviews

```text
GET /my-reviews
```

Retrieves:

* User's place ratings
* User's restaurant ratings

---

## My Favorites

```text
GET /my-favorites
```

Retrieves the places favorited by the current user.

---

# 24. Total User-Side Routes

The user module currently contains approximately **39 route definitions**, including page routes and API endpoints.

They can be grouped as follows:

| Module                   | Routes |
| ------------------------ | -----: |
| User API / Settings      |      3 |
| Transportation / Bus API |      1 |
| KNN API                  |      1 |
| Dashboard                |      1 |
| Places                   |      8 |
| Trending / Smart Map     |      2 |
| Announcements            |      1 |
| Travel Tools             |      4 |
| Itinerary                |      2 |
| Events / Transportation  |      2 |
| Restaurant               |      4 |
| Help / Feedback          |      2 |
| Profile                  |      2 |
| Personal Data            |      3 |

Some routes contain multiple HTTP methods, so the exact count depends on whether documentation counts route declarations or individual HTTP operations.

---

# 25. KNN Recommendation System

## 25.1 What Is KNN?

KNN means:

> K-Nearest Neighbors

In SmartTrip, KNN is used as a **location-based recommendation algorithm**.

The system receives:

1. User's current latitude
2. User's current longitude
3. List of available places
4. Number of recommendations required

It calculates the distance between the user and every available location.

The locations are then sorted by distance.

The closest locations are returned.

---

# 26. KNN Architecture

The basic flow is:

```text
User Location
      |
      v
Latitude + Longitude
      |
      v
Load Places from Database
      |
      v
Convert Places to Coordinates
      |
      v
Calculate Distance
      |
      v
Distance for Every Place
      |
      v
Sort by Distance
      |
      v
Select Top K
      |
      v
Nearest Places
      |
      v
Display Recommendations
```

---

# 27. KNN Functions

The KNN implementation contains two main functions.

## 27.1 `calculate_distance()`

```python
def calculate_distance(lat1, lon1, lat2, lon2):
    """Standard Euclidean distance estimation"""
    return math.hypot(lat1 - lat2, lon1 - lon2)
```

This function calculates the mathematical distance between two coordinate points.

It receives:

```text
lat1 = first latitude
lon1 = first longitude
lat2 = second latitude
lon2 = second longitude
```

The calculation is:

```text
distance = √((lat1 - lat2)² + (lon1 - lon2)²)
```

Python's:

```python
math.hypot(x, y)
```

performs:

```text
√(x² + y²)
```

Therefore:

```python
math.hypot(
    lat1 - lat2,
    lon1 - lon2
)
```

is equivalent to:

```text
√((lat1-lat2)² + (lon1-lon2)²)
```

---

# 28. Example Distance Calculation

Assume the user's location is:

```text
Latitude: 16.8661
Longitude: 96.1951
```

A place has:

```text
Latitude: 16.8700
Longitude: 96.2000
```

The difference is:

```text
Latitude difference
= 16.8661 - 16.8700
= -0.0039

Longitude difference
= 96.1951 - 96.2000
= -0.0049
```

Therefore:

```text
distance
= √((-0.0039)² + (-0.0049)²)

≈ 0.00626
```

This value is a coordinate-space distance.

It is **not kilometers or meters**.

---

# 29. `get_nearest_places()`

The main KNN function is:

```python
def get_nearest_places(
    current_lat,
    current_lng,
    all_locations,
    top_n=5
):
```

Its purpose is to find the closest `top_n` locations.

The algorithm starts with:

```python
distances = []
```

Then it loops through every location:

```python
for loc in all_locations:
```

For each location:

```python
dist = calculate_distance(
    current_lat,
    current_lng,
    loc['lat'],
    loc['lng']
)
```

The result is stored together with the location:

```python
distances.append((dist, loc))
```

The list therefore looks conceptually like:

```text
[
    (0.0042, Place A),
    (0.0125, Place B),
    (0.0021, Place C),
    (0.0084, Place D)
]
```

The list is sorted:

```python
distances.sort(key=lambda x: x[0])
```

This sorts according to the first element of each tuple — the distance.

The result becomes:

```text
[
    (0.0021, Place C),
    (0.0042, Place A),
    (0.0084, Place D),
    (0.0125, Place B)
]
```

Finally:

```python
return [
    item[1]
    for item in distances[:top_n]
]
```

selects only the locations.

If:

```python
top_n = 5
```

the five closest locations are returned.

---

# 30. Complete KNN Example

Assume the user is located at:

```text
User:
Latitude  = 16.8661
Longitude = 96.1951
```

There are four places:

| Place   | Latitude | Longitude |
| ------- | -------: | --------: |
| Place A |  16.8700 |   96.2000 |
| Place B |  16.9000 |   96.2500 |
| Place C |  16.8650 |   96.1920 |
| Place D |  16.8800 |   96.2100 |

The system calculates:

```text
User
  |
  +-- Place A → distance
  |
  +-- Place B → distance
  |
  +-- Place C → distance
  |
  +-- Place D → distance
```

After sorting:

```text
Place C → closest
Place A
Place D
Place B → farthest
```

If:

```python
top_n = 3
```

the result becomes:

```text
Place C
Place A
Place D
```

---

# 31. KNN Flow in the Dashboard

The dashboard performs the following flow:

```text
User logs in
      |
      v
Open /user/dashboard
      |
      v
Load current_user.latitude
current_user.longitude
      |
      v
Load Places from database
      |
      v
Keep places with valid coordinates
      |
      v
Create all_locations[]
      |
      v
get_nearest_places()
      |
      v
Calculate distance to every place
      |
      v
Sort distances
      |
      v
Take top 5
      |
      v
nearby_places
      |
      v
dashboard.html
```

The important condition is:

```python
if current_user.latitude is not None \
    and current_user.longitude is not None \
    and all_locations:
```

KNN only runs when the system has both:

```text
User latitude
User longitude
```

and available locations.

---

# 32. KNN Flow in Smart Map

The Smart Map uses the same algorithm.

Flow:

```text
Open /user/smart-map
       |
       v
Load all places
       |
       v
Create map location objects
       |
       v
Check user's coordinates
       |
       v
get_nearest_places(..., top_n=1)
       |
       v
Return closest place
       |
       v
nearest_place
       |
       v
Display on Smart Map
```

The difference is:

```python
top_n=1
```

instead of:

```python
top_n=5
```

Therefore the dashboard asks:

> "Give me the 5 closest places."

while Smart Map asks:

> "Give me the closest place."

---

# 33. KNN API Endpoint

There is also a dedicated API:

```text
POST /api/knn/nearest
```

The endpoint receives:

```json
{
    "lat": 16.8661,
    "lng": 96.1951,
    "locations": [
        {
            "id": 1,
            "name": "Place A",
            "lat": 16.8700,
            "lng": 96.2000
        },
        {
            "id": 2,
            "name": "Place B",
            "lat": 16.9000,
            "lng": 96.2500
        }
    ]
}
```

The server executes:

```python
nearest = get_nearest_places(
    current_lat,
    current_lng,
    locations,
    top_n=5
)
```

and returns:

```json
{
    "nearest": [
        {
            "id": 1,
            "name": "Place A",
            "lat": 16.8700,
            "lng": 96.2000
        }
    ]
}
```

This allows the frontend to request nearby recommendations dynamically.

---

# 34. Where KNN Is Used

KNN is currently used in three important places.

## 34.1 Dashboard

```text
/user/dashboard
```

Purpose:

```text
Recommend the 5 nearest places.
```

Implementation:

```python
get_nearest_places(
    current_lat=current_user.latitude,
    current_lng=current_user.longitude,
    all_locations=all_locations,
    top_n=5
)
```

---

## 34.2 Smart Map

```text
/user/smart-map
```

Purpose:

```text
Find the single closest place.
```

Implementation:

```python
get_nearest_places(
    current_user.latitude,
    current_user.longitude,
    all_locations,
    top_n=1
)
```

---

## 34.3 KNN API

```text
/api/knn/nearest
```

Purpose:

```text
Allow frontend/API clients to request nearest locations.
```

Implementation:

```python
get_nearest_places(
    current_lat,
    current_lng,
    locations,
    top_n=5
)
```

---

# 35. KNN Data Flow

The complete data flow is:

```text
                    DATABASE
                       |
             +---------+---------+
             |                   |
             v                   v
          User Table         Place Table
             |                   |
       latitude/longitude    lat/lng
             |                   |
             +---------+---------+
                       |
                       v
                KNN Algorithm
                       |
                       v
             calculate_distance()
                       |
                       v
              Distance List
                       |
                       v
                Sort Ascending
                       |
                       v
                  Top K
                       |
             +---------+---------+
             |                   |
             v                   v
         Dashboard           Smart Map
          Top 5               Top 1
```

---

# 36. Why the User Location Is Important

The KNN system needs a reference point.

That reference point is the user's current location.

The location can be stored through:

```text
POST /api/user/update-location
```

or through:

```text
POST /api/user/settings
```

For example:

```text
User
latitude  = 16.8661
longitude = 96.1951
```

The system then compares this point against every place.

---

# 37. KNN Does Not Recommend Based on Ratings

The current implementation is purely location-based.

The distance calculation uses only:

```text
latitude
longitude
```

It does not currently consider:

* Rating
* Number of likes
* Number of views
* Price
* Category
* User preferences
* Popularity
* Opening hours

Therefore, the current recommendation means:

> "Nearest places"

rather than:

> "Best places for this user."

This distinction is important in the SmartTrip technical documentation.

---

# 38. Current KNN Algorithm

The current algorithm can be summarized as:

```text
Input:
    User coordinates
    List of places
    K

For every place:
    Calculate distance from user
    Store distance + place

Sort all places by distance

Return first K places
```

In pseudocode:

```text
FUNCTION get_nearest_places(user_lat, user_lng, locations, K):

    distances = []

    FOR each location IN locations:

        distance =
            sqrt(
                (user_lat - location.lat)^2
                +
                (user_lng - location.lng)^2
            )

        add (distance, location) to distances

    SORT distances by distance ascending

    RETURN first K locations
```

---

# 39. Computational Complexity

Suppose there are `N` places.

The algorithm calculates the distance for every place:

```text
O(N)
```

Then it sorts the entire list:

```text
O(N log N)
```

Therefore the overall complexity is approximately:

```text
O(N log N)
```

For a small or medium-sized travel database, this is generally acceptable.

For a very large database, the algorithm could be optimized using:

* Database geospatial queries
* Spatial indexes
* R-tree
* PostGIS
* Haversine distance filtering
* KD-tree
* Ball tree

---

# 40. Important Coordinate Limitation

The current implementation uses:

```python
math.hypot(
    lat1 - lat2,
    lon1 - lon2
)
```

This treats latitude and longitude as normal Cartesian coordinates.

However, latitude and longitude represent positions on the Earth's surface.

Therefore, this calculation is an approximation.

It should not be interpreted directly as:

```text
0.006 = 0.006 km
```

For geographically accurate distance calculations, a future implementation should use the **Haversine formula** or a geospatial database function.

---

# 41. Current KNN Recommendation Architecture

The current SmartTrip architecture is therefore:

```text
                 SmartTrip User
                       |
                       v
              Browser / Frontend
                       |
             +---------+---------+
             |                   |
             v                   v
       Update Location       Request Page
             |                   |
             v                   v
        User.latitude       Dashboard /
        User.longitude      Smart Map
             |                   |
             +---------+---------+
                       |
                       v
                KNN Function
                       |
              +--------+--------+
              |                 |
              v                 v
      calculate_distance()   Sorting
              |                 |
              +--------+--------+
                       |
                       v
                  Top K Places
                       |
             +---------+---------+
             |                   |
             v                   v
        Dashboard             Smart Map
         Top 5                  Top 1
```

---

# 42. Overall User-Side Functional Flow

The complete user-side system can be represented as:

```text
LOGIN
  |
  v
USER DASHBOARD
  |
  +---- Nearby Places --------> KNN
  |
  +---- Announcements
  |
  +---- Smart Map ------------> KNN
  |
  +---- Places
  |       |
  |       +---- Details
  |       +---- Rating
  |       +---- Comment
  |       +---- Like
  |       +---- Favorite
  |       +---- Report
  |
  +---- Restaurants
  |       |
  |       +---- Details
  |       +---- Rating
  |       +---- Comment
  |
  +---- Itineraries
  |       |
  |       +---- Create Trip
  |       +---- Saved Plans
  |
  +---- Transportation
  |       |
  |       +---- Bus Search API
  |
  +---- Weather
  |
  +---- Events
  |
  +---- Calculator
  |
  +---- AI Assistant
  |
  +---- Settings
  |       |
  |       +---- Profile
  |       +---- Location
  |       +---- Theme
  |       +---- Profile Picture
  |
  +---- Feedback
  |
  +---- Help
  |
  +---- My Profile
  |
  +---- My Reviews
  |
  +---- My Favorites
  |
  +---- My Plans
  |
  +---- Change Password
```

---

# 43. Summary

The SmartTrip user module provides the complete travel experience for authenticated users.

The most important location-based component is the KNN recommendation system.

The KNN system works by:

1. Obtaining the user's latitude and longitude.
2. Loading available places.
3. Extracting the coordinates of each place.
4. Calculating the distance between the user and each place.
5. Sorting the places by distance.
6. Selecting the first `K` locations.
7. Returning those locations to the requested page or API.

The same KNN helper is reused throughout the application.

### Dashboard

```text
K = 5
```

Used to show the five nearest places.

### Smart Map

```text
K = 1
```

Used to identify the nearest place.

### KNN API

```text
K = 5
```

Used to provide nearest-place data to frontend clients.

This design keeps the KNN implementation reusable because the distance calculation and nearest-location logic are centralized in:

```python
calculate_distance()
```

and:

```python
get_nearest_places()
```

Rather than implementing the algorithm separately inside every route.
