import os
from functools import wraps
from flask import Blueprint, render_template, request, jsonify, session, current_app, redirect, url_for, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import db, User, Place, Restaurant, Region, TripPlan, Category, Feedback, Announcement, Ad, Role,PlaceLike,Comment,RestaurantComment,Favorite,Report,Hotel
from sqlalchemy import or_,func

admin_bp = Blueprint('admin', __name__)

# ==========================================
# HELPER FUNCTIONS & DECORATORS
# ==========================================

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'Admin':
            if request.method == 'POST':
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 403
            return "Access Denied: Admins Only", 403
        return f(*args, **kwargs)
    return decorated_function

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.method == 'POST':
                return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    return User.query.get(session.get('user_id'))

def safe_float(val, default=0.0):
    try:
        return float(val) if val else default
    except (TypeError, ValueError):
        return default

def safe_int(val, default=None):
    try:
        return int(val) if val and str(val).isdigit() else default
    except (TypeError, ValueError):
        return default

def handle_image_upload(request_files, field_name, folder_path, default_filename=None):
    if field_name in request_files:
        file = request_files[field_name]
        if file and file.filename != '':
            filename = secure_filename(file.filename)
            os.makedirs(folder_path, exist_ok=True)
            file.save(os.path.join(folder_path, filename))
            return filename
    return default_filename


# -------------------------------------------------------------------
# 1. Popular Places (Sorted by View Count)
# -------------------------------------------------------------------
@admin_bp.route('/popular-places', methods=['GET'])
@admin_required
def popular_places():
    page = request.args.get('page', 1, type=int)
    pagination = Place.query.order_by(Place.view_count.desc()).paginate(page=page, per_page=10, error_out=False)
    
    return render_template(
        'admin/pages/management/popular_places.html',
        places=pagination.items,
        pagination=pagination,
        current_user=get_current_user()
    )

# -------------------------------------------------------------------
# 2. Reviews & Comments Management (Places & Restaurants)
# -------------------------------------------------------------------
@admin_bp.route('/reviews-comments', methods=['GET'])
@admin_required
def reviews_comments():
    page_place = request.args.get('page_place', 1, type=int)
    page_rest = request.args.get('page_rest', 1, type=int)
    
    place_comments = Comment.query.order_by(Comment.created_at.desc()).paginate(page=page_place, per_page=8, error_out=False)
    restaurant_comments = RestaurantComment.query.order_by(RestaurantComment.created_at.desc()).paginate(page=page_rest, per_page=8, error_out=False)
    
    return render_template(
        'admin/pages/management/reviews_comments.html',
        place_comments=place_comments.items,
        place_pagination=place_comments,
        restaurant_comments=restaurant_comments.items,
        restaurant_pagination=restaurant_comments,
        current_user=get_current_user()
    )

@admin_bp.route('/reviews-comments/delete/<string:comment_type>/<int:comment_id>', methods=['POST'])
@admin_required
def delete_comment(comment_type, comment_id):
    if comment_type == 'place':
        comment = Comment.query.get_or_404(comment_id)
    elif comment_type == 'restaurant':
        comment = RestaurantComment.query.get_or_404(comment_id)
    else:
        flash('Invalid comment type.', 'danger')
        return redirect(url_for('admin.reviews_comments'))

    db.session.delete(comment)
    db.session.commit()
    flash('Comment deleted successfully!', 'success')
    return redirect(url_for('admin.reviews_comments'))

# -------------------------------------------------------------------
# 3. Top Liked & Favorited Places
# -------------------------------------------------------------------
@admin_bp.route('/top-liked-favorites', methods=['GET'])
@admin_required
def top_liked_favorites():
    page = request.args.get('page', 1, type=int)
    
    # Aggregation subqueries
    likes_subquery = db.session.query(
        PlaceLike.place_id,
        func.count(PlaceLike.id).label('likes_count')
    ).group_by(PlaceLike.place_id).subquery()

    favs_subquery = db.session.query(
        Favorite.place_id,
        func.count(Favorite.id).label('favs_count')
    ).group_by(Favorite.place_id).subquery()

    query = db.session.query(
        Place,
        func.coalesce(likes_subquery.c.likes_count, 0).label('likes_cnt'),
        func.coalesce(favs_subquery.c.favs_count, 0).label('favs_cnt')
    ).outerjoin(likes_subquery, Place.id == likes_subquery.c.place_id)\
     .outerjoin(favs_subquery, Place.id == favs_subquery.c.place_id)\
     .order_by((func.coalesce(likes_subquery.c.likes_count, 0) + func.coalesce(favs_subquery.c.favs_count, 0)).desc())

    pagination = query.paginate(page=page, per_page=10, error_out=False)
    
    return render_template(
        'admin/pages/management/top_liked_favorites.html',
        places_data=pagination.items,
        pagination=pagination,
        current_user=get_current_user()
    )

# ==========================================
# DASHBOARD & MAPS
# ==========================================

@admin_bp.route('/dashboard', methods=['GET'])
@admin_required
def admin_dashboard():
    users = User.query.all()
    places = Place.query.all()
    regions = Region.query.all()
    region_map = {region.id: region.name for region in regions}
    
    return render_template(
        'admin/dashboard.html', 
        username=session.get('username'), 
        users=users, 
        places=places,
        region_map=region_map  
    )

@admin_bp.route('/users/info', methods=['GET'])
@admin_required
def admin_users():
    return render_template(
        'admin/pages/overview/users_map.html', 
        current_user=get_current_user(), 
        users=User.query.all()
    )

@admin_bp.route('/places', methods=['GET'])
@admin_required
def admin_places_map():
    places = Place.query.all()
    restaurants = Restaurant.query.all() 
    return render_template(
        'admin/pages/overview/places_map.html', 
        current_user=get_current_user(), 
        places=places,
        restaurants=restaurants
    )

# ==========================================
# PLACES MANAGEMENT
# ==========================================

@admin_bp.route('/places/list', methods=['GET'])
@admin_required
def admin_places():
    search_query = request.args.get('search', '', type=str)
    category_filter = request.args.get('category', 'all', type=str)
    region_filter = request.args.get('region', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)
    
    query = Place.query

    if search_query:
        query = query.filter(or_(
            Place.name.ilike(f"%{search_query}%"),
            Place.description.ilike(f"%{search_query}%")
        ))

    cat_id = safe_int(category_filter)
    if cat_id: query = query.filter(Place.category_id == cat_id)
        
    reg_id = safe_int(region_filter)
    if reg_id: query = query.filter(Place.region_id == reg_id)

    order_options = {
        'oldest': Place.id.asc(),
        'name_asc': Place.name.asc(),
        'name_desc': Place.name.desc()
    }
    query = query.order_by(order_options.get(sort_by, Place.id.desc()))

    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/management/places_list.html',
        current_user=get_current_user(),
        places=pagination.items,
        pagination=pagination,
        categories=Category.query.all(),
        regions=Region.query.all(),
        search_query=search_query,
        category_filter=category_filter,
        region_filter=region_filter,
        sort_by=sort_by
    )

@admin_bp.route('/places', methods=['POST'])
@admin_required
def create_place():
    filename = handle_image_upload(request.files, 'image_file', current_app.config['UPLOAD_FOLDER'], 'default.jpg')
    
    new_place = Place(
        name=request.form.get('name'),
        region_id=safe_int(request.form.get('region_id')),
        category_id=safe_int(request.form.get('category_id')),
        package=request.form.get('package'),
        phone_number=request.form.get('phone_number'),
        description=request.form.get('description'),
        image_file=filename,
        latitude=safe_float(request.form.get('latitude')),
        longitude=safe_float(request.form.get('longitude')),
        # Refilled pricing & transport fares
        base_price_per_day=safe_float(request.form.get('base_price_per_day'), 50.0),
        bus_fare=safe_float(request.form.get('bus_fare'), 15.0),
        train_fare=safe_float(request.form.get('train_fare'), 20.0),
        taxi_fare=safe_float(request.form.get('taxi_fare'), 50.0)
    )
    db.session.add(new_place)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Place added successfully!'})

@admin_bp.route('/places/update/<int:id>', methods=['POST'])
@admin_required
def update_place(id):
    place = Place.query.get_or_404(id)
    place.name = request.form.get('name')
    place.region_id = safe_int(request.form.get('region_id'), place.region_id)
    place.category_id = safe_int(request.form.get('category_id'), place.category_id)
    place.package = request.form.get('package')
    place.phone_number = request.form.get('phone_number')
    place.description = request.form.get('description')
    lat = request.form.get('latitude')
    lng = request.form.get('longitude')
    if lat: place.latitude = safe_float(lat)
    if lng: place.longitude = safe_float(lng)
    base_price = request.form.get('base_price_per_day')
    bus = request.form.get('bus_fare')
    train = request.form.get('train_fare')
    taxi = request.form.get('taxi_fare')
    
    if base_price: place.base_price_per_day = safe_float(base_price)
    if bus: place.bus_fare = safe_float(bus)
    if train: place.train_fare = safe_float(train)
    if taxi: place.taxi_fare = safe_float(taxi)
        
    new_image = handle_image_upload(request.files, 'image_file', current_app.config['UPLOAD_FOLDER'])
    if new_image:
        place.image_file = new_image  
            
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Place updated successfully!'})

@admin_bp.route('/places/delete/<int:place_id>', methods=['POST'])
@admin_required
def delete_place(place_id):
    place = Place.query.get_or_404(place_id)
    db.session.delete(place)
    db.session.commit()
    flash('Place deleted successfully!', 'success')
    return redirect(url_for('admin.admin_places'))

# ==========================================
# USER MANAGEMENT
# ==========================================

@admin_bp.route('/users/list', methods=['GET'])
@admin_required
def admin_users_list():
    search_query = request.args.get('search', '', type=str)
    role_filter = request.args.get('role', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)

    query = User.query

    if search_query:
        query = query.filter(or_(
            User.username.ilike(f"%{search_query}%"),
            User.email.ilike(f"%{search_query}%")
        ))

    if role_filter != 'all':
        query = query.join(Role).filter(Role.name == role_filter)

    order_options = {
        'oldest': User.id.asc(),
        'username_asc': User.username.asc(),
        'username_desc': User.username.desc()
    }
    query = query.order_by(order_options.get(sort_by, User.id.desc()))

    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/management/users_list.html',
        current_user=get_current_user(),
        users=pagination.items,
        pagination=pagination,
        search_query=search_query,
        role_filter=role_filter,
        sort_by=sort_by
    )

@admin_bp.route('/users/create', methods=['POST'])
@admin_required
def admin_create_user():
    try:
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role_name = request.form.get('role', 'User')

        if not username or not email or not password:
            return jsonify({'status': 'error', 'message': 'All fields are required!'}), 400

        if User.query.filter((User.username == username) | (User.email == email)).first():
            return jsonify({'status': 'error', 'message': 'Username or Email already exists!'}), 400

        role_obj = Role.query.filter_by(name=role_name).first()
        if not role_obj:
            return jsonify({'status': 'error', 'message': f'Role {role_name} does not exist!'}), 400

        new_user = User(
            username=username, 
            email=email, 
            password=generate_password_hash(password, method='scrypt'), 
            role_id=role_obj.id,
            profile_pic='default_avatar.png'
        )

        db.session.add(new_user)
        db.session.commit()
        return jsonify({'status': 'success', 'message': 'User created successfully!'})
    except Exception as e:
        db.session.rollback()
        print(f"Error creating user: {str(e)}")
        return jsonify({'status': 'error', 'message': 'An internal error occurred.'}), 500

@admin_bp.route('/users/reset_password/<int:id>', methods=['POST'])
@admin_required
def admin_reset_password(id):
    data = request.get_json(silent=True) or {}
    new_password = data.get('new_password')

    if not new_password:
        return jsonify({'status': 'error', 'message': 'Please provide a valid password.'}), 400

    user = User.query.get_or_404(id)
    user.password = generate_password_hash(new_password, method='scrypt')
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Password updated successfully!'})

@admin_bp.route('/users/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_user(id):
    user = User.query.get_or_404(id)

    if user.username == 'admin' or user.id == session.get('user_id'):
        return jsonify({'status': 'error', 'message': 'Cannot delete the main admin account!'}), 400

    db.session.delete(user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'User deleted successfully!'})

# ==========================================
# RESTAURANTS MANAGEMENT
# ==========================================

@admin_bp.route('/restaurants/list', methods=['GET'])
@admin_required
def admin_restaurants_list():
    search_query = request.args.get('search', '', type=str)
    region_filter = request.args.get('region', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)

    query = Restaurant.query

    if search_query:
        query = query.filter(or_(
            Restaurant.name.ilike(f"%{search_query}%"),
            Restaurant.description.ilike(f"%{search_query}%")
        ))

    if region_filter != 'all':
        query = query.filter(Restaurant.region_id == safe_int(region_filter))

    order_options = {
        'oldest': Restaurant.id.asc(),
        'name_asc': Restaurant.name.asc(),
        'name_desc': Restaurant.name.desc()
    }
    query = query.order_by(order_options.get(sort_by, Restaurant.id.desc()))

    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/management/restaurants_list.html',
        current_user=get_current_user(),
        restaurants=pagination.items,
        regions=Region.query.all(),
        pagination=pagination,
        search_query=search_query,
        region_filter=region_filter,
        sort_by=sort_by
    )

@admin_bp.route('/restaurants/create', methods=['POST'])
@admin_required
def admin_create_restaurant():
    name = request.form.get('name')
    region_id = safe_int(request.form.get('region_id'))
    latitude = safe_float(request.form.get('latitude'), None)
    longitude = safe_float(request.form.get('longitude'), None)

    if not name or not region_id or latitude is None or longitude is None:
        return jsonify({'status': 'error', 'message': 'Name, Region, Latitude and Longitude are required!'}), 400

    new_restaurant = Restaurant(
        name=name,
        region_id=region_id,
        description=request.form.get('description'),
        latitude=latitude,
        longitude=longitude
    )
    db.session.add(new_restaurant)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Restaurant added successfully!'})

@admin_bp.route('/restaurants/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_restaurant(id):
    restaurant = Restaurant.query.get_or_404(id)
    db.session.delete(restaurant)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Restaurant deleted successfully!'})


# ==========================================
# HOTELS MANAGEMENT
# ==========================================

@admin_bp.route('/hotels/list', methods=['GET'])
@admin_required
def admin_hotels_list():

    search_query = request.args.get('search', '', type=str)
    region_filter = request.args.get('region', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)

    query = Hotel.query

    # Search
    if search_query:
        query = query.filter(or_(
            Hotel.name.ilike(f"%{search_query}%"),
            Hotel.description.ilike(f"%{search_query}%"),
            Hotel.address.ilike(f"%{search_query}%")
        ))

    # Region filter
    if region_filter != 'all':
        query = query.filter(
            Hotel.region_id == safe_int(region_filter)
        )

    # Sorting
    order_options = {
        'oldest': Hotel.id.asc(),
        'name_asc': Hotel.name.asc(),
        'name_desc': Hotel.name.desc()
    }

    query = query.order_by(
        order_options.get(
            sort_by,
            Hotel.id.desc()
        )
    )

    # Pagination
    pagination = query.paginate(
        page=page,
        per_page=10,
        error_out=False
    )

    return render_template(
        'admin/pages/management/hotels_list.html',

        current_user=get_current_user(),

        hotels=pagination.items,

        regions=Region.query.all(),

        pagination=pagination,

        search_query=search_query,

        region_filter=region_filter,

        sort_by=sort_by
    )


# ==========================================
# CREATE HOTEL
# ==========================================

@admin_bp.route('/hotels/create', methods=['POST'])
@admin_required
def admin_create_hotel():

    name = request.form.get('name')

    region_id = safe_int(
        request.form.get('region_id')
    )

    latitude = safe_float(
        request.form.get('latitude'),
        None
    )

    longitude = safe_float(
        request.form.get('longitude'),
        None
    )

    if (
        not name
        or not region_id
        or latitude is None
        or longitude is None
    ):
        return jsonify({
            'status': 'error',
            'message': 'Name, Region, Latitude and Longitude are required!'
        }), 400

    new_hotel = Hotel(

        name=name,

        region_id=region_id,

        description=request.form.get(
            'description'
        ),

        address=request.form.get(
            'address'
        ),

        latitude=latitude,

        longitude=longitude,

        rating=safe_float(
            request.form.get('rating'),
            0.0
        ),

        estimated_price=safe_float(
            request.form.get('estimated_price'),
            0.0
        )
    )

    db.session.add(new_hotel)

    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Hotel added successfully!'
    })


# ==========================================
# DELETE HOTEL
# ==========================================

@admin_bp.route(
    '/hotels/delete/<int:id>',
    methods=['POST']
)
@admin_required
def admin_delete_hotel(id):

    hotel = Hotel.query.get_or_404(id)

    db.session.delete(hotel)

    db.session.commit()

    return jsonify({
        'status': 'success',
        'message': 'Hotel deleted successfully!'
    })

# ==========================================
# TRIPS MANAGEMENT (Allows Normal Users)
# ==========================================

@admin_bp.route('/trips/view', methods=['GET'])
@login_required
def admin_trips_view():
    current_user = get_current_user()
    
    if current_user.role and current_user.role.name == 'Admin':
        trips = TripPlan.query.order_by(TripPlan.created_at.desc()).all()
    else:
        trips = TripPlan.query.filter_by(user_id=current_user.id).order_by(TripPlan.created_at.desc()).all()

    return render_template(
        'admin/pages/management/trips_list.html',
        current_user=current_user,
        trips=trips,
        places=Place.query.all()
    )

# @admin_bp.route('/trips/create', methods=['POST'])
# @login_required
# def admin_create_trip():
#     title = request.form.get('title')
#     start_lat = request.form.get('start_lat')
#     start_lng = request.form.get('start_lng')
#     dest_place_id = request.form.get('dest_place_id')

#     if not title or not start_lat or not start_lng or not dest_place_id:
#         return jsonify({'status': 'error', 'message': 'Title, starting coordinates, and destination place are required!'}), 400

#     new_trip = TripPlan(
#         user_id=session.get('user_id'),
#         title=title,
#         start_lat=safe_float(start_lat),
#         start_lng=safe_float(start_lng),
#         dest_place_id=safe_int(dest_place_id),
#         waypoints_json=request.form.get('waypoints_json')
#     )

#     db.session.add(new_trip)
#     db.session.commit()
#     return jsonify({'status': 'success', 'message': 'Trip plan created successfully!'})

# @admin_bp.route('/trips/delete/<int:id>', methods=['POST'])
# @login_required
# def admin_delete_trip(id):
#     trip = TripPlan.query.get_or_404(id)
#     current_user = get_current_user()

#     if current_user.role.name != 'Admin' and trip.user_id != current_user.id:
#         return jsonify({'status': 'error', 'message': 'Permission denied'}), 403

#     db.session.delete(trip)
#     db.session.commit()
#     return jsonify({'status': 'success', 'message': 'Trip plan deleted successfully!'})

# ==========================================
# CATEGORIES MANAGEMENT
# ==========================================

@admin_bp.route('/categories/list', methods=['GET'])
@admin_required
def admin_categories_list():
    search_query = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)

    query = Category.query
    if search_query:
        query = query.filter(Category.name.ilike(f"%{search_query}%"))

    order_options = {
        'oldest': Category.id.asc(),
        'name_asc': Category.name.asc(),
        'name_desc': Category.name.desc()
    }
    query = query.order_by(order_options.get(sort_by, Category.id.desc()))
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/management/categories_list.html',
        current_user=get_current_user(),
        categories=pagination.items,
        pagination=pagination,
        search_query=search_query,
        sort_by=sort_by
    )

@admin_bp.route('/categories/create', methods=['POST'])
@admin_required
def admin_create_category():
    name = request.form.get('name')
    if not name:
        return jsonify({'status': 'error', 'message': 'Category name is required!'}), 400
    if Category.query.filter_by(name=name).first():
        return jsonify({'status': 'error', 'message': 'Category already exists!'}), 400

    db.session.add(Category(name=name))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Category created successfully!'})

@admin_bp.route('/categories/update/<int:id>', methods=['POST'])
@admin_required
def admin_update_category(id):
    category = Category.query.get_or_404(id)
    name = request.form.get('name')
    
    if not name:
        return jsonify({'status': 'error', 'message': 'Category name cannot be empty!'}), 400

    existing = Category.query.filter_by(name=name).first()
    if existing and existing.id != id:
        return jsonify({'status': 'error', 'message': 'Another category with this name already exists!'}), 400

    category.name = name
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Category updated successfully!'})

@admin_bp.route('/categories/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_category(id):
    category = Category.query.get_or_404(id)
    db.session.delete(category)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Category deleted successfully!'})

# ==========================================
# FEEDBACKS & ANNOUNCEMENTS
# ==========================================

@admin_bp.route('/feedbacks/list', methods=['GET'])
@admin_required
def admin_feedbacks_list():
    search_query = request.args.get('search', '', type=str)
    type_filter = request.args.get('type', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)
    
    query = Feedback.query
    if search_query:
        query = query.join(User).filter(or_(
            Feedback.subject.ilike(f"%{search_query}%"),
            Feedback.message.ilike(f"%{search_query}%"),
            User.username.ilike(f"%{search_query}%")
        ))

    if type_filter != 'all':
        query = query.filter(Feedback.feedback_type == type_filter)

    query = query.order_by(Feedback.id.asc() if sort_by == 'oldest' else Feedback.id.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/help&support/feedbacks_list.html',
        current_user=get_current_user(),
        feedbacks=pagination.items,
        pagination=pagination,
        search_query=search_query,
        type_filter=type_filter,
        sort_by=sort_by
    )

@admin_bp.route('/feedbacks/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_feedback(id):
    feedback = Feedback.query.get_or_404(id)
    db.session.delete(feedback)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Feedback deleted successfully!'})

@admin_bp.route('/announcements/list', methods=['GET'])
@admin_required
def admin_announcements_list():
    search_query = request.args.get('search', '', type=str)
    priority_filter = request.args.get('priority', 'all', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)
    
    query = Announcement.query
    if search_query:
        query = query.filter(or_(
            Announcement.title.ilike(f"%{search_query}%"),
            Announcement.content.ilike(f"%{search_query}%")
        ))

    if priority_filter != 'all':
        query = query.filter(Announcement.priority == priority_filter)

    query = query.order_by(Announcement.id.asc() if sort_by == 'oldest' else Announcement.id.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/help&support/announcements_list.html',
        current_user=get_current_user(),
        announcements=pagination.items,
        pagination=pagination,
        search_query=search_query,
        priority_filter=priority_filter,
        sort_by=sort_by
    )

@admin_bp.route('/announcements/create', methods=['POST'])
@admin_required
def admin_create_announcement():
    title = request.form.get('title')
    content = request.form.get('content')

    if not title or not content:
        return jsonify({'status': 'error', 'message': 'Title and content are required!'}), 400

    new_announcement = Announcement(
        title=title,
        content=content,
        type=request.form.get('type', 'normal')
    )
    db.session.add(new_announcement)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Announcement published successfully!'})

@admin_bp.route('/announcements/update/<int:id>', methods=['POST'])
@admin_required
def admin_update_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    title = request.form.get('title')
    content = request.form.get('content')

    if not title or not content:
        return jsonify({'status': 'error', 'message': 'Title and content cannot be empty!'}), 400

    announcement.title = title
    announcement.content = content
    announcement.priority = request.form.get('type', 'normal')
    
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Announcement updated successfully!'})

@admin_bp.route('/announcements/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_announcement(id):
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Announcement deleted successfully!'})

# ==========================================
# ADS MANAGEMENT
# ==========================================

@admin_bp.route('/ads/list', methods=['GET'])
@admin_required
def admin_ads_list():
    search_query = request.args.get('search', '', type=str)
    sort_by = request.args.get('sort', 'newest', type=str)
    page = request.args.get('page', 1, type=int)

    query = Ad.query
    if search_query:
        query = query.filter(Ad.title.ilike(f"%{search_query}%"))

    query = query.order_by(Ad.id.asc() if sort_by == 'oldest' else Ad.id.desc())
    pagination = query.paginate(page=page, per_page=10, error_out=False)

    return render_template(
        'admin/pages/help&support/ads_list.html',
        current_user=get_current_user(),
        ads=pagination.items,
        pagination=pagination,
        search_query=search_query,
        sort_by=sort_by
    )

@admin_bp.route('/ads/create', methods=['POST'])
@admin_required
def admin_create_ad():
    title = request.form.get('title')
    if not title:
        return jsonify({'status': 'error', 'message': 'Ad title is required!'}), 400

    db.session.add(Ad(title=title, is_active=True))
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Ad created successfully!'})

@admin_bp.route('/ads/update/<int:id>', methods=['POST'])
@admin_required
def admin_update_ad(id):
    ad = Ad.query.get_or_404(id)
    title = request.form.get('title')
    
    if not title:
        return jsonify({'status': 'error', 'message': 'Ad title cannot be empty!'}), 400

    ad.title = title
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Ad updated successfully!'})

@admin_bp.route('/ads/toggle/<int:id>', methods=['POST'])
@admin_required
def admin_toggle_ad(id):
    ad = Ad.query.get_or_404(id)
    ad.is_active = not ad.is_active
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Ad status updated successfully!', 'is_active': ad.is_active})

@admin_bp.route('/ads/delete/<int:id>', methods=['POST'])
@admin_required
def admin_delete_ad(id):
    ad = Ad.query.get_or_404(id)
    db.session.delete(ad)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Ad deleted successfully!'})

# ==========================================
# SETTINGS
# ==========================================

@admin_bp.route('/settings', methods=['GET', 'POST'])
@admin_required
def admin_settings():
    current_user = get_current_user()

    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'update_password':
            current_pass = request.form.get('current_password')
            new_pass = request.form.get('new_password')
            
            if not current_pass or not new_pass:
                return jsonify({'status': 'error', 'message': 'All password fields are required!'}), 400
            if not check_password_hash(current_user.password, current_pass):
                return jsonify({'status': 'error', 'message': 'Incorrect current password!'}), 400
            
            current_user.password = generate_password_hash(new_pass)
            db.session.commit()
            return jsonify({'status': 'success', 'message': 'Password updated successfully!'})

        current_user.phone = request.form.get('phone')
        current_user.bio = request.form.get('bio')
        current_user.latitude = safe_float(request.form.get('latitude'), current_user.latitude)
        current_user.longitude = safe_float(request.form.get('longitude'), current_user.longitude)

        upload_path = os.path.join(current_app.root_path, 'static', 'uploads')
        new_pic = handle_image_upload(request.files, 'profile_pic', upload_path)
        if new_pic:
            current_user.profile_pic = new_pic

        db.session.commit()
        return jsonify({'status': 'success', 'message': 'Admin settings updated successfully!'})

    return render_template(
        'admin/pages/help&support/settings.html',
        current_user=current_user,
        user=current_user
    )


# -------------------------------------------------------------------
# 1. Reports List & Filtering Route
# -------------------------------------------------------------------
@admin_bp.route('/reports', methods=['GET'])
@admin_required
def reports_list():
    status_filter = request.args.get('status', 'all')
    search_query = request.args.get('q', '').strip()
    page = request.args.get('page', 1, type=int)

    query = Report.query
    if status_filter in ['Pending', 'Resolved', 'Dismissed']:
        query = query.filter(Report.status == status_filter)

    if search_query:
        query = query.join(User).outerjoin(Place).filter(
            (Report.reason.ilike(f'%{search_query}%')) |
            (Report.details.ilike(f'%{search_query}%')) |
            (User.username.ilike(f'%{search_query}%')) |
            (Place.name.ilike(f'%{search_query}%'))
        )
    pagination = query.order_by(Report.id.desc()).paginate(
        page=page, per_page=10, error_out=False
    )
    return render_template(
        'admin/pages/analytics/reports.html',
        reports=pagination.items,
        pagination=pagination,
        current_status=status_filter,
        search_query=search_query,
        current_user=get_current_user()
    )


# -------------------------------------------------------------------
# 2. Update Report Status Route
# -------------------------------------------------------------------
@admin_bp.route('/reports/<int:report_id>/status', methods=['POST'])
@admin_required
def update_report_status(report_id):
    report = db.session.get(Report, report_id)
    if not report:
        flash('Report not found.', 'danger')
        return redirect(url_for('admin.reports_list'))
    new_status = request.form.get('status')
    if new_status in ['Pending', 'Resolved', 'Dismissed']:
        report.status = new_status
        db.session.commit()
        flash(f'Report #{report.id} status updated to {new_status}.', 'success')
    else:
        flash('Invalid status provided.', 'warning')
    return redirect(request.referrer or url_for('admin.reports_list'))


from . import analytics   
