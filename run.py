# import os
# from flask import Flask, redirect, url_for, render_template, session, jsonify, request
# from dotenv import load_dotenv
# from app.models import db, Role, User, Region, Ad
# from werkzeug.security import generate_password_hash
# from flask_login import LoginManager
# from app.routes.auth import auth_bp
# from app.routes.admin import admin_bp
# from app.routes.ai import ai_bp
# from app.routes.user import user_bp

# load_dotenv()

# login_manager = LoginManager()

# @login_manager.user_loader
# def load_user(user_id):
#     return db.session.get(User, int(user_id))

# @login_manager.unauthorized_handler
# def unauthorized():
#     if request.path.startswith('/api/'):
#         return jsonify({'error': 'Unauthorized'}), 401
#     return redirect(url_for('auth.login_page'))

# def create_app():
#     app = Flask(__name__)
#     app.secret_key = os.getenv('SECRET_KEY')
#     app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URI')
#     app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    
#     UPLOAD_FOLDER = os.path.join('static', 'uploads')
#     app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
#     os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
#     db.init_app(app)
#     login_manager.init_app(app)
#     login_manager.login_view = 'auth.login_page' 
#     login_manager.login_message_category = 'info' 
    
#     app.register_blueprint(auth_bp)
#     app.register_blueprint(admin_bp, url_prefix='/admin')
#     app.register_blueprint(ai_bp)
#     app.register_blueprint(user_bp)

#     with app.app_context():
#         db.create_all()
        
#         if not Role.query.filter_by(name='Admin').first():
#             db.session.add(Role(name='Admin'))
#         if not Role.query.filter_by(name='User').first():
#             db.session.add(Role(name='User'))
#         db.session.commit()

#         if not User.query.filter_by(username='admin').first():
#             admin_role = Role.query.filter_by(name='Admin').first()
#             db.session.add(User(
#                 username='admin',
#                 email='admin@smarttrip.com',
#                 password=generate_password_hash('Admin@123', method='scrypt'),
#                 role_id=admin_role.id
#             ))
#             db.session.commit() 

#         regions_data = [
#             {'id': 1, 'name': 'Kachin State', 'lat': 25.3852, 'lng': 97.4025},
#             {'id': 2, 'name': 'Kayah State', 'lat': 19.2343, 'lng': 97.2892},
#             {'id': 3, 'name': 'Kayin State', 'lat': 16.9459, 'lng': 97.9624},
#             {'id': 4, 'name': 'Chin State', 'lat': 22.1739, 'lng': 93.5813},
#             {'id': 5, 'name': 'Sagaing Region', 'lat': 23.9749, 'lng': 95.9142},
#             {'id': 6, 'name': 'Tanintharyi Region', 'lat': 12.0824, 'lng': 99.0129},
#             {'id': 7, 'name': 'Bago Region', 'lat': 18.2575, 'lng': 96.0645},
#             {'id': 8, 'name': 'Magway Region', 'lat': 20.1465, 'lng': 94.9455},
#             {'id': 9, 'name': 'Mandalay Region', 'lat': 21.9747, 'lng': 96.0836},
#             {'id': 10, 'name': 'Mon State', 'lat': 16.2947, 'lng': 97.7317},
#             {'id': 11, 'name': 'Rakhine State', 'lat': 20.1041, 'lng': 93.5813},
#             {'id': 12, 'name': 'Yangon Region', 'lat': 16.7954, 'lng': 96.1610},
#             {'id': 13, 'name': 'Shan State', 'lat': 21.5794, 'lng': 97.4589},
#             {'id': 14, 'name': 'Ayeyarwady Region', 'lat': 16.8202, 'lng': 95.0315},
#             {'id': 15, 'name': 'Naypyidaw Union Territory', 'lat': 19.7633, 'lng': 96.0785}
#         ]

#         for data in regions_data:
#             if not db.session.get(Region, data['id']):
#                 new_region = Region(
#                     id=data['id'],
#                     name=data['name'],
#                     latitude=data['lat'],
#                     longitude=data['lng']
#                 )
#                 db.session.add(new_region)
#         db.session.commit()

#     @app.context_processor
#     def inject_user():
#         active_ads = Ad.query.filter_by(is_active=True).order_by(Ad.created_at.desc()).all()
#         ad_titles = [ad.title for ad in active_ads] if active_ads else ["📣 Welcome to SmartTrip!"]
#         user = None
#         if 'user_id' in session:
#             user = db.session.get(User, session['user_id'])
#         return dict(current_user=user, active_ads=ad_titles)

#     @app.route('/')
#     def index():
#         return render_template('landing/home.html')

#     return app

# if __name__ == '__main__':
#     app = create_app()
#     app.run(debug=True, port=5000)

# ============================================================
# run.py
# SmartTrip Flask Application
# ============================================================

import os

from flask import (
    Flask,
    redirect,
    url_for,
    render_template,
    session,
    jsonify,
    request
)

from dotenv import load_dotenv
from werkzeug.security import generate_password_hash
from flask_login import LoginManager, login_required
from sqlalchemy import or_

# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# IMPORT DATABASE MODELS
# ============================================================

from app.models import (
    db,
    Role,
    User,
    Region,
    Ad,
    Pagoda
)


# ============================================================
# IMPORT BLUEPRINTS
# ============================================================

from app.routes.auth import auth_bp
from app.routes.admin import admin_bp
from app.routes.ai import ai_bp
from app.routes.user import user_bp


# ============================================================
# FLASK LOGIN
# ============================================================

login_manager = LoginManager()


@login_manager.user_loader
def load_user(user_id):

    try:
        return db.session.get(
            User,
            int(user_id)
        )

    except (ValueError, TypeError):

        return None

    except Exception as e:

        print(
            f"⚠️ Error loading user: {e}"
        )

        return None


@login_manager.unauthorized_handler
def unauthorized():

    """
    Return JSON for API requests.
    Redirect normal browser requests to login page.
    """

    if request.path.startswith('/api/'):

        return jsonify({
            'error': 'Unauthorized',
            'message': 'Please login first.'
        }), 401

    return redirect(
        url_for('auth.login_page')
    )


# ============================================================
# CREATE APP
# ============================================================

def create_app():

    app = Flask(__name__)


    # ========================================================
    # SECRET KEY
    # ========================================================

    app.secret_key = os.getenv(
        'SECRET_KEY',
        'smarttrip-development-secret-key'
    )


    # ========================================================
    # DATABASE
    # ========================================================

    database_uri = os.getenv(
        'DATABASE_URI'
    )

    if not database_uri:

        raise RuntimeError(
            'DATABASE_URI is not configured in .env file'
        )

    app.config[
        'SQLALCHEMY_DATABASE_URI'
    ] = database_uri

    app.config[
        'SQLALCHEMY_TRACK_MODIFICATIONS'
    ] = False


    # ========================================================
    # UPLOAD FOLDER
    # ========================================================

    upload_folder = os.path.join(
        app.root_path,
        'static',
        'uploads'
    )

    app.config[
        'UPLOAD_FOLDER'
    ] = upload_folder

    os.makedirs(
        upload_folder,
        exist_ok=True
    )


    # ========================================================
    # INITIALIZE DATABASE
    # ========================================================

    db.init_app(app)


    # ========================================================
    # INITIALIZE FLASK LOGIN
    # ========================================================

    login_manager.init_app(app)

    login_manager.login_view = 'auth.login_page'

    login_manager.login_message = (
        'Please login first.'
    )

    login_manager.login_message_category = 'info'


    # ========================================================
    # REGISTER BLUEPRINTS
    # ========================================================

    app.register_blueprint(
        auth_bp
    )

    app.register_blueprint(
        admin_bp,
        url_prefix='/admin'
    )

    app.register_blueprint(
        ai_bp
    )

    app.register_blueprint(
        user_bp
    )


    # ========================================================
    # DATABASE INITIALIZATION
    # ========================================================

    with app.app_context():

        # ----------------------------------------------------
        # CREATE TABLES
        # ----------------------------------------------------

        try:

            db.create_all()

            print(
                '✅ Database tables checked/created.'
            )

        except Exception as e:

            print(
                f'❌ Database table creation error: {e}'
            )


        # ====================================================
        # CREATE DEFAULT ROLES
        # ====================================================

        try:

            # ------------------------------------------------
            # ADMIN ROLE
            # ------------------------------------------------

            admin_role = Role.query.filter_by(
                name='Admin'
            ).first()

            if not admin_role:

                admin_role = Role(
                    name='Admin'
                )

                db.session.add(
                    admin_role
                )

            # ------------------------------------------------
            # USER ROLE
            # ------------------------------------------------

            user_role = Role.query.filter_by(
                name='User'
            ).first()

            if not user_role:

                user_role = Role(
                    name='User'
                )

                db.session.add(
                    user_role
                )

            db.session.commit()

            print(
                '✅ Default roles checked.'
            )

        except Exception as e:

            db.session.rollback()

            print(
                f'❌ Role initialization error: {e}'
            )


        # ====================================================
        # CREATE DEFAULT ADMIN
        # ====================================================

        try:

            admin_user = User.query.filter_by(
                username='admin'
            ).first()

            if not admin_user:

                admin_role = Role.query.filter_by(
                    name='Admin'
                ).first()

                if admin_role:

                    admin_user = User(

                        username='admin',

                        email='admin@smarttrip.com',

                        password=generate_password_hash(
                            'Admin@123',
                            method='scrypt'
                        ),

                        role_id=admin_role.id
                    )

                    db.session.add(
                        admin_user
                    )

                    db.session.commit()

                    print(
                        '✅ Default admin account created.'
                    )

            else:

                print(
                    'ℹ️ Default admin account already exists.'
                )

        except Exception as e:

            db.session.rollback()

            print(
                f'❌ Admin initialization error: {e}'
            )


        # ====================================================
        # DEFAULT REGIONS
        # ====================================================

        regions_data = [

            {
                'id': 1,
                'name': 'Kachin State',
                'lat': 25.3852,
                'lng': 97.4025
            },

            {
                'id': 2,
                'name': 'Kayah State',
                'lat': 19.2343,
                'lng': 97.2892
            },

            {
                'id': 3,
                'name': 'Kayin State',
                'lat': 16.9459,
                'lng': 97.9624
            },

            {
                'id': 4,
                'name': 'Chin State',
                'lat': 22.1739,
                'lng': 93.5813
            },

            {
                'id': 5,
                'name': 'Sagaing Region',
                'lat': 23.9749,
                'lng': 95.9142
            },

            {
                'id': 6,
                'name': 'Tanintharyi Region',
                'lat': 12.0824,
                'lng': 99.0129
            },

            {
                'id': 7,
                'name': 'Bago Region',
                'lat': 18.2575,
                'lng': 96.0645
            },

            {
                'id': 8,
                'name': 'Magway Region',
                'lat': 20.1465,
                'lng': 94.9455
            },

            {
                'id': 9,
                'name': 'Mandalay Region',
                'lat': 21.9747,
                'lng': 96.0836
            },

            {
                'id': 10,
                'name': 'Mon State',
                'lat': 16.2947,
                'lng': 97.7317
            },

            {
                'id': 11,
                'name': 'Rakhine State',
                'lat': 20.1041,
                'lng': 93.5813
            },

            {
                'id': 12,
                'name': 'Yangon Region',
                'lat': 16.7954,
                'lng': 96.1610
            },

            {
                'id': 13,
                'name': 'Shan State',
                'lat': 21.5794,
                'lng': 97.4589
            },

            {
                'id': 14,
                'name': 'Ayeyarwady Region',
                'lat': 16.8202,
                'lng': 95.0315
            },

            {
                'id': 15,
                'name': 'Naypyidaw Union Territory',
                'lat': 19.7633,
                'lng': 96.0785
            }
        ]


        # ====================================================
        # INSERT REGIONS
        # ====================================================

        try:

            for data in regions_data:

                existing_region = db.session.get(
                    Region,
                    data['id']
                )

                if not existing_region:

                    new_region = Region(

                        id=data['id'],

                        name=data['name'],

                        latitude=data['lat'],

                        longitude=data['lng']
                    )

                    db.session.add(
                        new_region
                    )

            db.session.commit()

            print(
                '✅ Default regions checked.'
            )

        except Exception as e:

            db.session.rollback()

            print(
                f'❌ Region initialization error: {e}'
            )


    # ========================================================
    # CONTEXT PROCESSOR
    # ========================================================

    @app.context_processor
    def inject_user():

        # ----------------------------------------------------
        # DEFAULT ADS
        # ----------------------------------------------------

        ad_titles = [
            '📣 Welcome to SmartTrip!'
        ]

        try:

            active_ads = (
                Ad.query
                .filter_by(
                    is_active=True
                )
                .order_by(
                    Ad.created_at.desc()
                )
                .all()
            )

            if active_ads:

                ad_titles = [
                    ad.title
                    for ad in active_ads
                    if ad.title
                ]

                if not ad_titles:

                    ad_titles = [
                        '📣 Welcome to SmartTrip!'
                    ]

        except Exception as e:

            print(
                f'⚠️ Error loading advertisements: {e}'
            )


        # ----------------------------------------------------
        # CURRENT USER
        # ----------------------------------------------------

        user = None

        if 'user_id' in session:

            try:

                user = db.session.get(
                    User,
                    session['user_id']
                )

            except Exception as e:

                print(
                    f'⚠️ Error loading user: {e}'
                )

        return {

            'current_user': user,

            'active_ads': ad_titles
        }


    # ========================================================
    # HOME PAGE
    # ========================================================

    @app.route('/')
    def index():

        return render_template(
            'landing/home.html'
        )


    # ========================================================
    # PAGODA API
    # ========================================================

    # @app.route('/api/pagodas', methods=['GET'])
    # def api_pagodas():

    #     try:

    #         print("================================")
    #         print("🛕 /api/pagodas CALLED")
    #         print("Pagoda =", Pagoda)
    #         print("Table =", Pagoda.__tablename__)
    #         print("================================")

    #         # Get all pagodas
    #         pagodas = Pagoda.query.all()

    #         print(
    #             f"✅ Found {len(pagodas)} pagodas"
    #         )

    #         result = []

    #         for p in pagodas:

    #             result.append({
    #                 'id': p.p_id,
    #                 'name': p.pgdName,
    #                 'division': p.division,
    #                 'district': p.district,
    #                 'township': p.township,
    #                 'address': p.address,
    #                 'photo': p.photo,
    #                 'map_link': p.map_link,
    #                 'website': p.website,
    #                 'history': p.history
    #             })

    #         return jsonify({
    #             'success': True,
    #             'total': len(result),
    #             'pagodas': result
    #         }), 200

    #     except Exception as e:

    #         import traceback

    #         print("❌ PAGODA API ERROR")
    #         traceback.print_exc()

    #         return jsonify({
    #             'success': False,
    #             'error': str(e),
    #             'error_type': type(e).__name__
    #         }), 500


    # # ========================================================
    # # PAGODAS BY TOWNSHIP
    # # ========================================================

    # @app.route(
    #     '/api/pagodas/township/<township_name>',
    #     methods=['GET']
    # )
    # @login_required
    # def api_pagodas_by_township(
    #     township_name
    # ):

    #     """
    #     Example:

    #         /api/pagodas/township/Pyay
    #     """

    #     try:

    #         township_name = (
    #             township_name
    #             .strip()
    #         )


    #         # ------------------------------------------------
    #         # QUERY
    #         # ------------------------------------------------

    #         pagodas = (

    #             Pagoda.query

    #             .filter(
    #                 Pagoda.township.ilike(
    #                     f'%{township_name}%'
    #                 )
    #             )

    #             .order_by(
    #                 Pagoda.pgdName.asc()
    #             )

    #             .all()
    #         )


    #         # ------------------------------------------------
    #         # FORMAT
    #         # ------------------------------------------------

    #         result_pagodas = []


    #         for p in pagodas:

    #             history = (
    #                 p.history or ''
    #             )

    #             if len(history) > 200:

    #                 history = (
    #                     history[:200]
    #                     + '...'
    #                 )


    #             result_pagodas.append({

    #                 'id': p.p_id,

    #                 'name': p.pgdName,

    #                 'division': p.division,

    #                 'district': p.district,

    #                 'township': p.township,

    #                 'address': p.address,

    #                 'map_link': p.map_link,

    #                 'photo': p.photo,

    #                 'website': p.website,

    #                 'history': history
    #             })


    #         # ------------------------------------------------
    #         # RESPONSE
    #         # ------------------------------------------------

    #         return jsonify({

    #             'success': True,

    #             'township': township_name,

    #             'count': len(
    #                 result_pagodas
    #             ),

    #             'pagodas': result_pagodas

    #         }), 200


    #     except Exception as e:

    #         print(
    #             f'❌ Error fetching township pagodas: {e}'
    #         )

    #         return jsonify({

    #             'success': False,

    #             'error': 'Failed to fetch township pagodas',

    #             'message': str(e)

    #         }), 500

    @app.route('/api/pagodas', methods=['GET'])
    def api_pagodas():

        township = request.args.get("township", "").strip()

        if not township:
            return jsonify({
                "success": False,
                "message": "Township is required.",
                "example": "/api/pagodas?township=ပြည်"
            }), 400

        # ==========================================
        # PYAY TOWNSHIP
        # ==========================================

        pyay_keywords = [
            "ပြည်",
            "ပြည်မြို့",
            "ပြည်မြို့နယ်",
            "Pyay",
            "Pyay Township"
        ]

        is_pyay = any(
            keyword.lower() in township.lower()
            for keyword in pyay_keywords
        )

        if is_pyay:

            pagodas = Pagoda.query.filter(
                or_(
                    Pagoda.township.contains("ပြည်"),
                    Pagoda.township.contains("Pyay")
                )
            ).all()

        # ==========================================
        # OTHER TOWNSHIPS
        # ==========================================

        else:

            pagodas = Pagoda.query.filter(
                Pagoda.township.contains(township)
            ).all()

        # ==========================================
        # RESPONSE
        # ==========================================

        result = []

        for p in pagodas:

            result.append({
                "id": p.p_id,
                "name": p.pgdName,
                "division": p.division,
                "district": p.district,
                "township": p.township,
                "photo": p.photo,
                "history": getattr(p, "history", None),
                "address": getattr(p, "address", None)
            })

        return jsonify({
            "success": True,
            "count": len(result),
            "township": township,
            "pagodas": result
        })


    # ========================================================
    # GET ALL TOWNSHIPS
    # ========================================================

    @app.route(
        '/api/townships',
        methods=['GET']
    )
    @login_required
    def api_townships():

        """
        Get unique townships from Pagoda table.
        """

        try:

            townships = (

                db.session

                .query(
                    Pagoda.township
                )

                .filter(
                    Pagoda.township.isnot(None)
                )

                .distinct()

                .all()
            )


            # ------------------------------------------------
            # CLEAN DATA
            # ------------------------------------------------

            township_list = []

            for row in townships:

                township = row[0]

                if township:

                    township = (
                        township
                        .strip()
                    )

                    if township:

                        township_list.append(
                            township
                        )


            township_list = sorted(
                set(township_list)
            )


            # ------------------------------------------------
            # RESPONSE
            # ------------------------------------------------

            return jsonify({

                'success': True,

                'count': len(
                    township_list
                ),

                'townships': township_list

            }), 200


        except Exception as e:

            print(
                f'❌ Error fetching townships: {e}'
            )

            return jsonify({

                'success': False,

                'error': 'Failed to fetch townships',

                'message': str(e)

            }), 500


    # ========================================================
    # SINGLE PAGODA
    # ========================================================

    @app.route(
        '/api/pagodas/<int:pagoda_id>',
        methods=['GET']
    )
    @login_required
    def api_single_pagoda(
        pagoda_id
    ):

        """
        Get one pagoda.

        Example:

            /api/pagodas/1
        """

        try:

            pagoda = db.session.get(
                Pagoda,
                pagoda_id
            )


            if not pagoda:

                return jsonify({

                    'success': False,

                    'error': 'Pagoda not found'

                }), 404


            return jsonify({

                'success': True,

                'pagoda': {

                    'id': pagoda.p_id,

                    'name': pagoda.pgdName,

                    'division': pagoda.division,

                    'district': pagoda.district,

                    'township': pagoda.township,

                    'address': pagoda.address,

                    'photo': pagoda.photo,

                    'map_link': pagoda.map_link,

                    'website': pagoda.website,

                    'history': pagoda.history
                }

            }), 200


        except Exception as e:

            print(
                f'❌ Error fetching pagoda: {e}'
            )

            return jsonify({

                'success': False,

                'error': 'Failed to fetch pagoda',

                'message': str(e)

            }), 500


    # ========================================================
    # HEALTH CHECK
    # ========================================================

    @app.route(
        '/api/health',
        methods=['GET']
    )
    def health_check():

        return jsonify({

            'status': 'ok',

            'message': 'SmartTrip API is running'

        }), 200


    # ========================================================
    # API DEBUG - CHECK PAGODA MODEL
    # ========================================================

    @app.route(
        '/api/debug/pagoda',
        methods=['GET']
    )
    def debug_pagoda():

        """
        Temporary debugging endpoint.
        Remove this in production.
        """

        try:

            return jsonify({

                'success': True,

                'model': str(Pagoda),

                'tablename': Pagoda.__tablename__,

                'message': 'Pagoda model is loaded correctly.'

            }), 200

        except Exception as e:

            return jsonify({

                'success': False,

                'error': str(e)

            }), 500


    # ========================================================
    # RETURN APP
    # ========================================================

    return app


# ============================================================
# RUN APPLICATION
# ============================================================

if __name__ == '__main__':

    app = create_app()

    print('')
    print('==========================================')
    print('🚀 SmartTrip Flask Application')
    print('==========================================')
    print('🌐 http://127.0.0.1:5000')
    print('❤️  http://127.0.0.1:5000/api/health')
    print('🛕 http://127.0.0.1:5000/api/pagodas')
    print('==========================================')
    print('')

    app.run(

        debug=True,

        host='127.0.0.1',

        port=5000
    )