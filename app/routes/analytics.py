import json
from flask import render_template, request
from sqlalchemy import func
from app.models import (
    db, User, Role, Place, Restaurant, Region, Category, 
    Favorite, PlaceLike, Comment, Rating, Report, 
    TripPlan, Feedback, Ad, Announcement
)

from app.routes.admin import admin_bp, admin_required, get_current_user

# -------------------------------------------------------------------
# 1. User & Activity Analytics Dashboard
# -------------------------------------------------------------------
@admin_bp.route('/analytics/users', methods=['GET'])
@admin_required
def user_analytics():
    total_users = User.query.count()
    theme_counts = db.session.query(
        User.theme_preference, func.count(User.id)
    ).group_by(User.theme_preference).all()
    theme_labels = [t[0].capitalize() if t[0] else 'Light' for t in theme_counts]
    theme_data = [t[1] for t in theme_counts]

    role_counts = db.session.query(
        Role.name, func.count(User.id)
    ).join(User, User.role_id == Role.id).group_by(Role.name).all()
    role_labels = [r[0] for r in role_counts]
    role_data = [r[1] for r in role_counts]

    feedback_counts = db.session.query(
        Feedback.feedback_type, func.count(Feedback.id)
    ).group_by(Feedback.feedback_type).all()
    feedback_labels = [f[0] for f in feedback_counts]
    feedback_data = [f[1] for f in feedback_counts]

    page = request.args.get('page', 1, type=int)
    users_pagination = User.query.order_by(User.id.desc()).paginate(page=page, per_page=8, error_out=False)

    return render_template(
        'admin/pages/analytics/user_analytics.html',
        total_users=total_users,
        theme_labels=json.dumps(theme_labels),
        theme_data=json.dumps(theme_data),
        role_labels=json.dumps(role_labels),
        role_data=json.dumps(role_data),
        feedback_labels=json.dumps(feedback_labels),
        feedback_data=json.dumps(feedback_data),
        users=users_pagination.items,
        pagination=users_pagination,
        current_user=get_current_user()
    )


# -------------------------------------------------------------------
# 2. Places & System Overview Dashboard
# -------------------------------------------------------------------
@admin_bp.route('/analytics/places-system', methods=['GET'])
@admin_required
def places_system_analytics():
    total_places = Place.query.count()
    total_restaurants = Restaurant.query.count()
    total_trips = TripPlan.query.count()
    total_reports = Report.query.count()

    cat_counts = db.session.query(
        Category.name, func.count(Place.id)
    ).outerjoin(Place, Place.category_id == Category.id).group_by(Category.name).all()
    cat_labels = [c[0] for c in cat_counts]
    cat_data = [c[1] for c in cat_counts]

    region_counts = db.session.query(
        Region.name, func.count(Place.id)
    ).outerjoin(Place, Place.region_id == Region.id).group_by(Region.name).all()
    region_labels = [r[0] for r in region_counts]
    region_data = [r[1] for r in region_counts]

    report_counts = db.session.query(
        Report.status, func.count(Report.id)
    ).group_by(Report.status).all()
    report_labels = [rep[0] for rep in report_counts]
    report_data = [rep[1] for rep in report_counts]

    avg_price = db.session.query(func.avg(Place.base_price_per_day)).scalar() or 0.0
    avg_bus = db.session.query(func.avg(Place.bus_fare)).scalar() or 0.0
    avg_train = db.session.query(func.avg(Place.train_fare)).scalar() or 0.0
    avg_taxi = db.session.query(func.avg(Place.taxi_fare)).scalar() or 0.0

    return render_template(
        'admin/pages/analytics/places_system_analytics.html',
        total_places=total_places,
        total_restaurants=total_restaurants,
        total_trips=total_trips,
        total_reports=total_reports,
        cat_labels=json.dumps(cat_labels),
        cat_data=json.dumps(cat_data),
        region_labels=json.dumps(region_labels),
        region_data=json.dumps(region_data),
        report_labels=json.dumps(report_labels),
        report_data=json.dumps(report_data),
        avg_price=round(avg_price, 2),
        avg_bus=round(avg_bus, 2),
        avg_train=round(avg_train, 2),
        avg_taxi=round(avg_taxi, 2),
        current_user=get_current_user()
    )