# SmartTrip — Admin Side Routes and Administration Documentation

## 1. Overview

The SmartTrip Admin module provides administrative control over the entire travel platform.

The administrator can manage:

* Dashboard
* Users
* Places
* Restaurants
* Categories
* Reviews and comments
* Likes and favorites
* Trip plans
* Feedback
* Announcements
* Advertisements
* User reports
* Admin profile and settings
* Location/map information
* Popularity and engagement analytics

The admin module is implemented using the Flask Blueprint:

```python
admin_bp = Blueprint('admin', __name__)
```

The routes are designed to separate normal user functionality from administrative functionality.

---

# 2. Admin Authentication and Authorization

The admin module uses two custom decorators:

```python
admin_required
```

and:

```python
login_required
```

These decorators control access to admin routes.

---

# 3. `admin_required()` Decorator

The main authorization mechanism is:

```python
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'Admin':
            ...
        return f(*args, **kwargs)
    return decorated_function
```

The decorator checks two conditions:

```text
1. User must be logged in.
2. User role must be "Admin".
```

The session must contain:

```text
user_id
role = Admin
```

If either condition fails, access is denied.

### GET request

For a normal page request:

```text
Access Denied: Admins Only
```

with HTTP status:

```text
403 Forbidden
```

### POST request

For AJAX/API-style requests:

```json
{
    "status": "error",
    "message": "Unauthorized"
}
```

with:

```text
403 Forbidden
```

---

# 4. Normal `login_required()` Decorator

The admin module also defines its own login decorator:

```python
def login_required(f):
```

This decorator checks only whether:

```python
'user_id' in session
```

If the user is not logged in:

* GET requests are redirected to the login page.
* POST requests return HTTP 401.

This is intentionally used for some routes where both normal users and administrators are allowed.

The main example is:

```text
/trips/view
```

---

# 5. Current User Helper

The function:

```python
def get_current_user():
    return User.query.get(session.get('user_id'))
```

retrieves the currently authenticated user from the database.

It is used throughout the admin routes to pass the administrator into templates:

```python
current_user=get_current_user()
```

This allows templates to access administrator information such as:

* Username
* Email
* Profile picture
* Role
* Phone
* Bio
* Location

---

# 6. Safe Conversion Helpers

The admin module contains two helper functions for safely converting request values.

## 6.1 `safe_float()`

```python
def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default
```

This prevents invalid numeric input from crashing the application.

Example:

```text
Input:
"16.8661"

Output:
16.8661
```

Invalid input:

```text
"abc"
```

returns the default value.

---

## 6.2 `safe_int()`

```python
def safe_int(val, default=None):
    try:
        return int(val) if val and str(val).isdigit() else default
    except (TypeError, ValueError):
        return default
```

This is mainly used for:

* Category IDs
* Region IDs
* Place IDs
* Other integer form parameters

---

# 7. Image Upload Helper

The function:

```python
def handle_image_upload(
    request_files,
    field_name,
    folder_path,
    default_filename=None
):
```

handles uploaded images.

The process is:

```text
Receive uploaded file
       |
       v
Check filename
       |
       v
secure_filename()
       |
       v
Create upload directory
       |
       v
Save image
       |
       v
Return filename
```

The use of:

```python
secure_filename()
```

helps prevent unsafe filenames from being written directly to the filesystem.

---

# 8. Admin Dashboard

## Route

```text
GET /admin/dashboard
```

Function:

```python
admin_dashboard()
```

The dashboard loads:

```python
users = User.query.all()
places = Place.query.all()
regions = Region.query.all()
```

It also creates a region mapping:

```python
region_map = {
    region.id: region.name
    for region in regions
}
```

The dashboard can therefore display an overview of:

* Registered users
* Available places
* Regions
* Geographic information

---

# 9. Users Map

## Route

```text
GET /admin/users/info
```

Function:

```python
admin_users()
```

This route loads all users:

```python
User.query.all()
```

and sends them to:

```text
admin/pages/overview/users_map.html
```

The purpose is to provide an administrative geographic view of users.

If user latitude and longitude are stored, the frontend can display their locations on a map.

---

# 10. Places Map

## Route

```text
GET /admin/places
```

Function:

```python
admin_places_map()
```

Loads:

```python
places = Place.query.all()
restaurants = Restaurant.query.all()
```

The data is passed to:

```text
admin/pages/overview/places_map.html
```

This allows the administrator to visually inspect:

* Places
* Restaurants
* Geographic locations

---

# 11. Places Management

The administrator can:

* View places
* Search places
* Filter by category
* Filter by region
* Sort places
* Create places
* Update places
* Delete places
* Upload place images
* Configure pricing
* Configure transportation fares
* Configure geographic coordinates

---

# 12. Place List

## Route

```text
GET /admin/places/list
```

Function:

```python
admin_places()
```

The route supports:

### Search

```text
?search=Bagan
```

Searches:

```python
Place.name
Place.description
```

using:

```python
ilike()
```

---

### Category Filter

```text
?category=3
```

Filters by:

```python
Place.category_id
```

---

### Region Filter

```text
?region=2
```

Filters by:

```python
Place.region_id
```

---

### Sorting

Available options include:

```text
newest
oldest
name_asc
name_desc
```

---

### Pagination

Places are displayed ten per page:

```python
paginate(
    page=page,
    per_page=10,
    error_out=False
)
```

This prevents large datasets from being loaded into a single page.

---

# 13. Create Place

## Route

```text
POST /admin/places
```

Function:

```python
create_place()
```

The administrator can create a place with:

* Name
* Region
* Category
* Package
* Phone number
* Description
* Image
* Latitude
* Longitude
* Base price per day
* Bus fare
* Train fare
* Taxi fare

Example data:

```text
Place:
Bagan

Latitude:
21.1719

Longitude:
94.8610

Base price:
50

Bus fare:
15

Train fare:
20

Taxi fare:
50
```

The place is then stored in the database.

---

# 14. Update Place

## Route

```text
POST /admin/places/update/<id>
```

Function:

```python
update_place(id)
```

The administrator can update:

* Basic information
* Region
* Category
* Package
* Phone
* Description
* Latitude
* Longitude
* Base price
* Bus fare
* Train fare
* Taxi fare
* Image

The existing values are retained when optional numeric values are not supplied.

---

# 15. Delete Place

## Route

```text
POST /admin/places/delete/<place_id>
```

Function:

```python
delete_place(place_id)
```

The selected place is removed from the database.

---

# 16. User Management

The admin can:

* View users
* Search users
* Filter by role
* Sort users
* Create users
* Reset passwords
* Delete users

---

# 17. User List

## Route

```text
GET /admin/users/list
```

Function:

```python
admin_users_list()
```

The administrator can search by:

```text
Username
Email
```

The route also supports role filtering.

For example:

```text
?role=Admin
```

The role is resolved through the `Role` table:

```python
query.join(Role).filter(
    Role.name == role_filter
)
```

---

# 18. Create User

## Route

```text
POST /admin/users/create
```

Function:

```python
admin_create_user()
```

Required fields:

```text
Username
Email
Password
```

The administrator can also assign a role.

Before creating the account, the system checks whether the username or email already exists.

The password is hashed using:

```python
generate_password_hash(
    password,
    method='scrypt'
)
```

Therefore, plaintext passwords are not stored in the database.

---

# 19. Reset User Password

## Route

```text
POST /admin/users/reset_password/<id>
```

Function:

```python
admin_reset_password(id)
```

The administrator supplies a new password.

The password is hashed before storage:

```python
user.password = generate_password_hash(
    new_password,
    method='scrypt'
)
```

---

# 20. Delete User

## Route

```text
POST /admin/users/delete/<id>
```

Function:

```python
admin_delete_user(id)
```

The system prevents deletion of:

```text
The main admin account
The currently logged-in administrator
```

The protection is:

```python
if user.username == 'admin' \
    or user.id == session.get('user_id'):
```

This helps prevent accidental removal of the primary administrator account.

---

# 21. Restaurant Management

The administrator can:

* View restaurants
* Search restaurants
* Filter by region
* Sort restaurants
* Create restaurants
* Delete restaurants

---

# 22. Restaurant List

## Route

```text
GET /admin/restaurants/list
```

Function:

```python
admin_restaurants_list()
```

Search fields:

```text
Restaurant name
Restaurant description
```

Filtering:

```text
Region
```

Sorting:

```text
Newest
Oldest
Name ascending
Name descending
```

Pagination:

```text
10 restaurants per page
```

---

# 23. Create Restaurant

## Route

```text
POST /admin/restaurants/create
```

Function:

```python
admin_create_restaurant()
```

Required fields:

```text
Name
Region
Latitude
Longitude
```

Optional field:

```text
Description
```

The latitude and longitude are required because restaurants can be displayed on the SmartTrip map and potentially used by location-based functionality.

---

# 24. Delete Restaurant

## Route

```text
POST /admin/restaurants/delete/<id>
```

Function:

```python
admin_delete_restaurant(id)
```

Deletes the selected restaurant.

---

# 25. Trip Management

## Route

```text
GET /admin/trips/view
```

Function:

```python
admin_trips_view()
```

This route has a special permission model.

### Administrator

An administrator can see:

```text
All trip plans
```

because:

```python
if current_user.role \
    and current_user.role.name == 'Admin':
```

loads:

```python
TripPlan.query.order_by(
    TripPlan.created_at.desc()
).all()
```

### Normal User

A normal authenticated user can only see their own trips:

```python
TripPlan.query.filter_by(
    user_id=current_user.id
)
```

Therefore:

```text
Admin
  |
  +-- All users' trips

Normal User
  |
  +-- Own trips only
```

This route uses `login_required` rather than `admin_required` because it intentionally supports both administrators and normal users.

---

# 26. Categories Management

Categories provide classification for places.

The administrator can:

* View categories
* Search categories
* Sort categories
* Create categories
* Update categories
* Delete categories

---

# 27. Category List

## Route

```text
GET /admin/categories/list
```

Function:

```python
admin_categories_list()
```

Supports:

```text
Search
Pagination
Sorting
```

---

# 28. Create Category

## Route

```text
POST /admin/categories/create
```

Function:

```python
admin_create_category()
```

The category name is required.

Duplicate category names are rejected.

---

# 29. Update Category

## Route

```text
POST /admin/categories/update/<id>
```

Function:

```python
admin_update_category(id)
```

The administrator can rename an existing category.

The system also checks for duplicate names.

---

# 30. Delete Category

## Route

```text
POST /admin/categories/delete/<id>
```

Function:

```python
admin_delete_category(id)
```

Deletes a category.

When implementing production deployment, foreign-key relationships should be considered before allowing deletion of categories that are currently assigned to places.

---

# 31. Reviews and Comments Management

## Route

```text
GET /admin/reviews-comments
```

Function:

```python
reviews_comments()
```

The administrator can see comments from:

```text
Places
Restaurants
```

The system uses two independent paginations:

```text
Place comments → 8 per page

Restaurant comments → 8 per page
```

This allows the page to display both comment types independently.

---

# 32. Delete Comment

## Route

```text
POST /admin/reviews-comments/delete/<comment_type>/<comment_id>
```

Examples:

```text
/admin/reviews-comments/delete/place/10
```

or:

```text
/admin/reviews-comments/delete/restaurant/20
```

The route determines the model from:

```python
comment_type
```

Possible values:

```text
place
restaurant
```

Invalid values are rejected.

---

# 33. Popular Places

## Route

```text
GET /admin/popular-places
```

Function:

```python
popular_places()
```

Popular places are determined by:

```python
Place.view_count
```

The query sorts:

```python
Place.view_count.desc()
```

Therefore, the most viewed place appears first.

Pagination:

```text
10 places per page
```

---

# 34. Top Liked and Favorited Places

## Route

```text
GET /admin/top-liked-favorites
```

Function:

```python
top_liked_favorites()
```

This is an engagement-based ranking system.

The system calculates:

```text
Likes count
+
Favorites count
```

for every place.

---

# 35. Like Aggregation

The system creates a subquery:

```python
likes_subquery = db.session.query(
    PlaceLike.place_id,
    func.count(PlaceLike.id).label('likes_count')
).group_by(
    PlaceLike.place_id
).subquery()
```

Conceptually:

```text
Place ID | Likes
---------|------
1        | 50
2        | 32
3        | 70
```

---

# 36. Favorite Aggregation

A second subquery calculates favorites:

```python
favs_subquery = db.session.query(
    Favorite.place_id,
    func.count(Favorite.id).label('favs_count')
).group_by(
    Favorite.place_id
).subquery()
```

Conceptually:

```text
Place ID | Favorites
---------|----------
1        | 20
2        | 45
3        | 10
```

---

# 37. Engagement Ranking Formula

The final query calculates:

```text
Engagement Score =
Likes + Favorites
```

Example:

| Place   | Likes | Favorites | Score |
| ------- | ----: | --------: | ----: |
| Place A |    50 |        20 |    70 |
| Place B |    32 |        45 |    77 |
| Place C |    70 |        10 |    80 |

The resulting order is:

```text
Place C → 80
Place B → 77
Place A → 70
```

This gives administrators a simple way to identify highly engaged destinations.

---

# 38. Feedback Management

## Route

```text
GET /admin/feedbacks/list
```

Function:

```python
admin_feedbacks_list()
```

Administrators can:

* Search feedback
* Filter by feedback type
* Sort feedback
* View feedback
* Delete feedback

Search can match:

```text
Feedback subject
Feedback message
Username
```

---

# 39. Delete Feedback

## Route

```text
POST /admin/feedbacks/delete/<id>
```

Function:

```python
admin_delete_feedback(id)
```

Deletes the selected feedback record.

---

# 40. Announcement Management

Administrators can:

* View announcements
* Search announcements
* Filter by priority
* Sort announcements
* Create announcements
* Update announcements
* Delete announcements

---

# 41. Announcement List

## Route

```text
GET /admin/announcements/list
```

Function:

```python
admin_announcements_list()
```

Searches:

```text
Title
Content
```

Filtering:

```text
Priority
```

Sorting:

```text
Newest
Oldest
```

---

# 42. Create Announcement

## Route

```text
POST /admin/announcements/create
```

Function:

```python
admin_create_announcement()
```

Required:

```text
Title
Content
```

The announcement type defaults to:

```text
normal
```

Example:

```text
Title:
Water Festival Travel Notice

Content:
Travelers are advised to book transportation early.
```

---

# 43. Update Announcement

## Route

```text
POST /admin/announcements/update/<id>
```

Function:

```python
admin_update_announcement(id)
```

Updates:

```text
Title
Content
Priority/type
```

---

# 44. Delete Announcement

## Route

```text
POST /admin/announcements/delete/<id>
```

Function:

```python
admin_delete_announcement(id)
```

Deletes an announcement.

---

# 45. Advertisement Management

The administrator can manage advertisements displayed throughout SmartTrip.

Available operations:

```text
View
Create
Update
Activate/Deactivate
Delete
```

---

# 46. Advertisement List

## Route

```text
GET /admin/ads/list
```

Function:

```python
admin_ads_list()
```

Supports:

```text
Search by title
Sorting
Pagination
```

---

# 47. Create Advertisement

## Route

```text
POST /admin/ads/create
```

Function:

```python
admin_create_ad()
```

Requires:

```text
Title
```

New advertisements are automatically enabled:

```python
is_active=True
```

---

# 48. Update Advertisement

## Route

```text
POST /admin/ads/update/<id>
```

Function:

```python
admin_update_ad(id)
```

Updates the advertisement title.

---

# 49. Toggle Advertisement

## Route

```text
POST /admin/ads/toggle/<id>
```

Function:

```python
admin_toggle_ad(id)
```

This changes:

```python
ad.is_active
```

from:

```text
True → False
```

or:

```text
False → True
```

This allows advertisements to be temporarily disabled without deleting them.

---

# 50. Delete Advertisement

## Route

```text
POST /admin/ads/delete/<id>
```

Function:

```python
admin_delete_ad(id)
```

Permanently removes the advertisement.

---

# 51. Admin Settings

## Route

```text
GET /admin/settings
POST /admin/settings
```

Function:

```python
admin_settings()
```

This route manages the administrator's personal settings.

The administrator can update:

* Password
* Phone
* Bio
* Latitude
* Longitude
* Profile picture

---

# 52. Admin Password Update

The administrator submits:

```text
Current password
New password
```

The system verifies the current password:

```python
check_password_hash(
    current_user.password,
    current_pass
)
```

If the password is correct, a new password hash is generated.

This prevents an administrator from changing the password without knowing the current password.

---

# 53. Admin Profile Information

The administrator can update:

```text
Phone
Bio
Latitude
Longitude
Profile picture
```

The profile image is stored in:

```text
static/uploads
```

---

# 54. Reports Management

## Route

```text
GET /admin/reports
```

Function:

```python
reports_list()
```

This is the administrative moderation system for user-submitted place reports.

Reports can be filtered by:

```text
Pending
Resolved
Dismissed
```

---

# 55. Report Search

The administrator can search reports using:

```text
Reason
Details
Username
Place name
```

The query joins:

```text
User
Place
```

to make cross-table searching possible.

---

# 56. Report Status Management

## Route

```text
POST /admin/reports/<report_id>/status
```

Function:

```python
update_report_status(report_id)
```

Allowed statuses:

```text
Pending
Resolved
Dismissed
```

Example workflow:

```text
User submits report
        |
        v
Pending
        |
        v
Admin reviews report
        |
   +----+----+
   |         |
   v         v
Resolved   Dismissed
```

This provides a basic moderation workflow.

---

# 57. Admin Route Summary

The admin module can be grouped into the following functional areas:

| Module                | Main Functionality          |
| --------------------- | --------------------------- |
| Authentication        | Admin authorization         |
| Dashboard             | Platform overview           |
| Users Map             | User geographic information |
| Places Map            | Places and restaurants map  |
| Place Management      | CRUD + location + pricing   |
| User Management       | CRUD + passwords            |
| Restaurant Management | CRUD                        |
| Trip Management       | View user trips             |
| Category Management   | CRUD                        |
| Reviews               | Moderation                  |
| Comments              | Moderation                  |
| Popular Places        | View-based ranking          |
| Likes/Favorites       | Engagement ranking          |
| Feedback              | User feedback management    |
| Announcements         | Platform announcements      |
| Advertisements        | Ad management               |
| Reports               | Moderation workflow         |
| Settings              | Admin account management    |

---

# 58. Complete Admin Route Table

| HTTP     | Route                                  | Function                    | Access |
| -------- | -------------------------------------- | --------------------------- | ------ |
| GET      | `/popular-places`                      | `popular_places`            | Admin  |
| GET      | `/reviews-comments`                    | `reviews_comments`          | Admin  |
| POST     | `/reviews-comments/delete/<type>/<id>` | `delete_comment`            | Admin  |
| GET      | `/top-liked-favorites`                 | `top_liked_favorites`       | Admin  |
| GET      | `/dashboard`                           | `admin_dashboard`           | Admin  |
| GET      | `/users/info`                          | `admin_users`               | Admin  |
| GET      | `/places`                              | `admin_places_map`          | Admin  |
| GET      | `/places/list`                         | `admin_places`              | Admin  |
| POST     | `/places`                              | `create_place`              | Admin  |
| POST     | `/places/update/<id>`                  | `update_place`              | Admin  |
| POST     | `/places/delete/<id>`                  | `delete_place`              | Admin  |
| GET      | `/users/list`                          | `admin_users_list`          | Admin  |
| POST     | `/users/create`                        | `admin_create_user`         | Admin  |
| POST     | `/users/reset_password/<id>`           | `admin_reset_password`      | Admin  |
| POST     | `/users/delete/<id>`                   | `admin_delete_user`         | Admin  |
| GET      | `/restaurants/list`                    | `admin_restaurants_list`    | Admin  |
| POST     | `/restaurants/create`                  | `admin_create_restaurant`   | Admin  |
| POST     | `/restaurants/delete/<id>`             | `admin_delete_restaurant`   | Admin  |
| GET      | `/trips/view`                          | `admin_trips_view`          | Login  |
| GET      | `/categories/list`                     | `admin_categories_list`     | Admin  |
| POST     | `/categories/create`                   | `admin_create_category`     | Admin  |
| POST     | `/categories/update/<id>`              | `admin_update_category`     | Admin  |
| POST     | `/categories/delete/<id>`              | `admin_delete_category`     | Admin  |
| GET      | `/feedbacks/list`                      | `admin_feedbacks_list`      | Admin  |
| POST     | `/feedbacks/delete/<id>`               | `admin_delete_feedback`     | Admin  |
| GET      | `/announcements/list`                  | `admin_announcements_list`  | Admin  |
| POST     | `/announcements/create`                | `admin_create_announcement` | Admin  |
| POST     | `/announcements/update/<id>`           | `admin_update_announcement` | Admin  |
| POST     | `/announcements/delete/<id>`           | `admin_delete_announcement` | Admin  |
| GET      | `/ads/list`                            | `admin_ads_list`            | Admin  |
| POST     | `/ads/create`                          | `admin_create_ad`           | Admin  |
| POST     | `/ads/update/<id>`                     | `admin_update_ad`           | Admin  |
| POST     | `/ads/toggle/<id>`                     | `admin_toggle_ad`           | Admin  |
| POST     | `/ads/delete/<id>`                     | `admin_delete_ad`           | Admin  |
| GET/POST | `/settings`                            | `admin_settings`            | Admin  |
| GET      | `/reports`                             | `reports_list`              | Admin  |
| POST     | `/reports/<id>/status`                 | `update_report_status`      | Admin  |

---

# 59. Admin Data Flow

The overall administration flow is:

```text
                    ADMIN LOGIN
                        |
                        v
                 Session Created
                        |
                        v
                 /admin/dashboard
                        |
        +---------------+---------------+
        |               |               |
        v               v               v
      Users           Places        Restaurants
        |               |               |
        v               v               v
    Management       Management       Management
        |               |               |
        +---------------+---------------+
                        |
                        v
                   Content Control
                        |
       +----------------+----------------+
       |                |                |
       v                v                v
 Announcements        Ads           Categories
       |
       v
Moderation
       |
 +-----+-------+
 |             |
 v             v
Comments      Reports
 |
 v
Feedback
```

---

# 60. Admin Security Flow

The normal security flow is:

```text
Request
   |
   v
admin_required()
   |
   v
Is user_id in session?
   |
   +---- No ----> 401 / Redirect
   |
   Yes
   |
   v
Is role == "Admin"?
   |
   +---- No ----> 403 Access Denied
   |
   Yes
   |
   v
Execute Admin Route
   |
   v
Database Operation
   |
   v
Response
```

This ensures that administrative CRUD operations are not available to ordinary users.

---

# 61. CRUD Architecture

Most admin management modules follow the same pattern:

```text
LIST
 |
 +-- Search
 +-- Filter
 +-- Sort
 +-- Pagination
 |
 v
CREATE
 |
 v
UPDATE
 |
 v
DELETE
```

For example, Place Management:

```text
/admin/places/list
        |
        +---- Search
        +---- Category Filter
        +---- Region Filter
        +---- Sorting
        +---- Pagination
        |
        +---- POST /admin/places
        |
        +---- POST /admin/places/update/<id>
        |
        +---- POST /admin/places/delete/<id>
```

This pattern is reused throughout the admin module.

---

# 62. Pagination Architecture

Most list pages use Flask-SQLAlchemy pagination:

```python
pagination = query.paginate(
    page=page,
    per_page=10,
    error_out=False
)
```

The frontend receives:

```text
pagination.items
pagination
```

This allows the template to display:

* Current page
* Total pages
* Next page
* Previous page
* Total records

The standard page size is:

```text
10 records
```

The reviews/comments page uses:

```text
8 records
```

---

# 63. Search Architecture

The admin module uses SQLAlchemy's:

```python
ilike()
```

for case-insensitive search.

Example:

```python
Place.name.ilike(
    f"%{search_query}%"
)
```

For places, the administrator can search both:

```text
Name
Description
```

For users:

```text
Username
Email
```

For feedback:

```text
Subject
Message
Username
```

For reports:

```text
Reason
Details
Username
Place name
```

---

# 64. Filtering Architecture

The admin module uses request query parameters.

Example:

```text
/admin/places/list?category=2&region=1
```

The route converts the IDs using:

```python
safe_int()
```

and then adds SQLAlchemy filters.

This keeps filtering at the database query level instead of loading every record into Python.

---

# 65. Sorting Architecture

Sorting is controlled through a request parameter:

```text
?sort=name_asc
```

The code maps allowed values to SQLAlchemy ordering expressions.

Example:

```python
order_options = {
    'oldest': Place.id.asc(),
    'name_asc': Place.name.asc(),
    'name_desc': Place.name.desc()
}
```

This is safer and cleaner than directly inserting user-provided SQL expressions.

---

# 66. Administrative Analytics

The admin module contains several forms of analytics.

### Popularity

Based on:

```text
Place.view_count
```

### Engagement

Based on:

```text
PlaceLike count
+
Favorite count
```

### User activity

Available through:

```text
Users
Trip plans
Reviews
Comments
Favorites
Reports
Feedback
```

These features provide administrators with information about how users interact with SmartTrip.

---

# 67. Moderation Workflow

SmartTrip has multiple moderation mechanisms.

## Comments

```text
User posts comment
       |
       v
Comment stored
       |
       v
Admin reviews
       |
       v
Admin can delete
```

## Reports

```text
User reports place
       |
       v
Report status = Pending
       |
       v
Admin reviews
       |
       +----> Resolved
       |
       +----> Dismissed
```

This provides a basic content moderation system.

---

# 68. Admin vs Normal User Permissions

The permission model can be summarized as:

| Feature               | Normal User | Admin |
| --------------------- | ----------: | ----: |
| View own profile      |         Yes |   Yes |
| Create trip           |         Yes |   Yes |
| View own trips        |         Yes |   Yes |
| View all trips        |          No |   Yes |
| View places           |         Yes |   Yes |
| Create places         |          No |   Yes |
| Update places         |          No |   Yes |
| Delete places         |          No |   Yes |
| Manage users          |          No |   Yes |
| Manage restaurants    |          No |   Yes |
| Manage categories     |          No |   Yes |
| Manage announcements  |          No |   Yes |
| Manage ads            |          No |   Yes |
| Moderate comments     |          No |   Yes |
| View reports          |          No |   Yes |
| Update report status  |          No |   Yes |
| Submit feedback       |         Yes |   Yes |
| Manage admin settings |          No |   Yes |

---

# 69. Admin Module Architecture

The admin module follows a layered approach:

```text
                   Browser
                      |
                      v
                Flask Route
                      |
                      v
              Authorization
                      |
             +--------+--------+
             |                 |
             v                 v
        Validation         Request Data
             |                 |
             +--------+--------+
                      |
                      v
                 SQLAlchemy
                      |
                      v
                   Database
                      |
                      v
                  Response
                      |
             +--------+--------+
             |                 |
             v                 v
          Template          JSON
```

GET requests primarily return HTML templates.

POST requests generally perform database operations and return either:

```text
JSON
```

or:

```text
Redirect + Flash Message
```

---

# 70. Important Design Characteristics

The current admin implementation has several useful characteristics.

### Centralized authorization

```python
@admin_required
```

is reused across administrative routes.

### Reusable validation helpers

```python
safe_float()
safe_int()
```

reduce repetitive conversion logic.

### Reusable file handling

```python
handle_image_upload()
```

centralizes image upload behavior.

### Database-side pagination

Large lists are paginated through SQLAlchemy rather than manually slicing Python lists.

### Database-side aggregation

Likes and favorites are counted using SQL aggregation rather than loading all records into Python.

### Role-based trip visibility

Administrators can view all trips while normal users only see their own.

---

# 71. Overall Admin System

The SmartTrip administrator acts as the central management layer.

The system can be summarized as:

```text
                       ADMIN
                         |
             +-----------+-----------+
             |                       |
             v                       v
       CONTENT MANAGEMENT       USER MANAGEMENT
             |                       |
       +-----+------+           +----+----+
       |     |      |           |         |
       v     v      v           v         v
    Places  Ads Categories    Users     Trips
       |
       v
 Restaurants
       |
       v
 Announcements

                         ADMIN
                           |
                           v
                     MODERATION
                           |
              +------------+------------+
              |            |            |
              v            v            v
          Comments      Reports      Feedback

                         ADMIN
                           |
                           v
                       ANALYTICS
                           |
              +------------+------------+
              |                         |
              v                         v
       Popular Places          Likes + Favorites
```

---

# 72. Conclusion

The SmartTrip Admin module provides centralized control over the travel platform.

Its primary responsibilities are:

1. **User Management** — create, search, reset passwords, and remove users.
2. **Place Management** — manage destinations, coordinates, pricing, images, categories, and regions.
3. **Restaurant Management** — manage restaurant information and locations.
4. **Content Management** — manage announcements, advertisements, and categories.
5. **Moderation** — review comments, feedback, and user reports.
6. **Analytics** — identify popular and highly engaged destinations.
7. **Trip Management** — allow administrators to monitor user-created trip plans.
8. **Map Management** — visualize users, places, and restaurants.
9. **Security** — restrict administrative operations using session-based role authorization.
10. **Account Management** — allow administrators to update their own profile and password.

The admin architecture is built around Flask Blueprints, decorators, SQLAlchemy ORM queries, pagination, filtering, aggregation, and JSON/HTML responses.

The overall design provides SmartTrip with a centralized administration panel capable of managing the application's users, travel content, geographic data, engagement, moderation, and platform communication.
