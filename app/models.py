from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
db = SQLAlchemy()

class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(20), unique=True, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

class Region(db.Model):
    __tablename__ = 'regions'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    places = db.relationship('Place', backref='region', lazy=True)
    restaurants = db.relationship('Restaurant', backref='region', lazy=True)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)
    places = db.relationship('Place', backref='category', lazy=True)

class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    profile_pic = db.Column(db.String(255), default='default_avatar.png')
    phone = db.Column(db.String(30), nullable=True)
    bio = db.Column(db.Text, nullable=True)
    theme_preference = db.Column(db.String(10), default='light')
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    favorites = db.relationship('Favorite', backref='user', cascade='all, delete-orphan')
    likes = db.relationship('PlaceLike', backref='user', cascade='all, delete-orphan')
    comments = db.relationship('Comment', backref='user', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='user', cascade='all, delete-orphan')
    trips = db.relationship('TripPlan', backref='user', cascade='all, delete-orphan')

class Place(db.Model):
    __tablename__ = 'places'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False) 
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    package = db.Column(db.String(100), nullable=True)
    phone_number = db.Column(db.String(20), nullable=True)
    description = db.Column(db.Text, nullable=True)
    image_file = db.Column(db.String(255), nullable=False, default='default.jpg')
    latitude = db.Column(db.Float, default=0)
    longitude = db.Column(db.Float, default=0)
    view_count = db.Column(db.Integer, default=0)
    # base_price_per_day = db.Column(db.Float, default=50.0)
    # bus_fare = db.Column(db.Float, default=15.0)
    # train_fare = db.Column(db.Float, default=20.0)
    # taxi_fare = db.Column(db.Float, default=50.0)
    comments = db.relationship('Comment', backref='place', cascade='all, delete-orphan')
    ratings = db.relationship('Rating', backref='place', cascade='all, delete-orphan')
    likes = db.relationship('PlaceLike', backref='place', cascade='all, delete-orphan')
    @property
    def average_rating(self):
        if not self.ratings:
            return 0.0
        total_stars = sum(rating.stars for rating in self.ratings)
        return round(total_stars / len(self.ratings), 1)

    @property
    def total_reviews(self):
        return len(self.ratings)

        
class Restaurant(db.Model):
    __tablename__ = 'restaurants'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    region_id = db.Column(db.Integer, db.ForeignKey('regions.id'), nullable=False)
    description = db.Column(db.Text, nullable=True)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    comments = db.relationship('RestaurantComment', backref='restaurant', cascade='all, delete-orphan')
    ratings = db.relationship('RestaurantRating', backref='restaurant', cascade='all, delete-orphan')

class Favorite(db.Model):
    __tablename__ = 'favorites'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    place = db.relationship('Place', backref=db.backref('favorites', cascade='all, delete-orphan'))

class PlaceLike(db.Model):
    __tablename__ = 'place_likes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)

class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Rating(db.Model):
    __tablename__ = 'ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    stars = db.Column(db.Integer, nullable=False)


class RestaurantComment(db.Model):
    __tablename__ = 'restaurant_comments'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('restaurant_comments', cascade='all, delete-orphan'))

class RestaurantRating(db.Model):
    __tablename__ = 'restaurant_ratings'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    restaurant_id = db.Column(db.Integer, db.ForeignKey('restaurants.id'), nullable=False)
    stars = db.Column(db.Integer, nullable=False)
    user = db.relationship('User', backref=db.backref('restaurant_ratings', cascade='all, delete-orphan'))

class Report(db.Model):
    __tablename__ = 'reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=True)
    reason = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='Pending')
    user = db.relationship('User', backref=db.backref('reports', cascade='all, delete-orphan'))
    place = db.relationship('Place', backref=db.backref('reports', cascade='all, delete-orphan'))


class TripPlan(db.Model):
    __tablename__ = 'trip_plans'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    start_lat = db.Column(db.Float, nullable=False)
    start_lng = db.Column(db.Float, nullable=False)
    dest_place_id = db.Column(db.Integer, db.ForeignKey('places.id'), nullable=False)
    total_budget = db.Column(db.Float, nullable=True)
    total_days = db.Column(db.Integer, nullable=True, default=1) 
    waypoints_json = db.Column(db.Text, nullable=True) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    destination = db.relationship('Place', foreign_keys=[dest_place_id])
    days = db.relationship('TripDay', backref='trip_plan', cascade="all, delete-orphan", order_by="TripDay.day_number")

 

class Feedback(db.Model):
    __tablename__ = 'feedbacks'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    feedback_type = db.Column(db.String(30), nullable=False)
    subject = db.Column(db.String(150), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user = db.relationship('User', backref=db.backref('feedbacks', cascade='all, delete-orphan'))

class Ad(db.Model):
    __tablename__ = 'ads'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False) 
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Announcement(db.Model):
    __tablename__ = 'announcements'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    content = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), nullable=False) 
    created_at = db.Column(db.DateTime, default=datetime.utcnow)



class TripDay(db.Model):
    __tablename__ = 'trip_days'
    id = db.Column(db.Integer, primary_key=True)
    trip_id = db.Column(db.Integer, db.ForeignKey('trip_plans.id'), nullable=False) 
    day_number = db.Column(db.Integer, nullable=False)
    notes = db.Column(db.String(255), nullable=True)
    activities_json = db.Column(db.Text, nullable=True)

class City(db.Model):
    __tablename__ = 'cities'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    city = db.Column(
        db.String(100),
        nullable=False,
        unique=True
    )

    latitude = db.Column(
        db.Float,
        nullable=False
    )

    longitude = db.Column(
        db.Float,
        nullable=False
    )

    hotel_cost = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    food_cost = db.Column(
        db.Float,
        nullable=False,
        default=0.0
    )

    def __repr__(self):
        return f'<City {self.city}>'


class Pagoda(db.Model):
    __tablename__ = "pagoda"

    p_id = db.Column(db.Integer, primary_key=True, nullable=False)

    pgdName = db.Column(db.String(1000), nullable=False)

    division = db.Column(db.String(50), nullable=False)

    district = db.Column(db.String(50), nullable=False)

    township = db.Column(db.String(50), nullable=False)

    photo = db.Column(db.String(250), nullable=False)

    map_link = db.Column(db.String(1000), nullable=False)

    website = db.Column(db.String(50), nullable=False)

    address = db.Column(db.String(300), nullable=False)

    history = db.Column(db.String(10000), nullable=False)

    def __repr__(self):
        return f"<Pagoda {self.pgdName}>"

class Hotel(db.Model):
    __tablename__ = 'hotels'

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    name = db.Column(
        db.String(150),
        nullable=False
    )

    address = db.Column(
        db.String(300),
        nullable=True
    )

  

    latitude = db.Column(
        db.Float,
        nullable=False
    )

    longitude = db.Column(
        db.Float,
        nullable=False
    )

    rating = db.Column(
        db.Float,
        default=0.0
    )

    estimated_price_per_night = db.Column(
        db.Float,
        default=0.0
    )

    def __repr__(self):
        return f'<Hotel {self.name}>'
