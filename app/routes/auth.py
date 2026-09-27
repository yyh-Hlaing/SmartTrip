from flask import Blueprint, request, jsonify, session, redirect, url_for, render_template
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from app.models import db, User, Role

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register')
def register_page(): 
    return render_template('auth/register.html')

@auth_bp.route('/login')
def login_page(): 
    return render_template('auth/login.html')

@auth_bp.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username', '').strip()
    email = data.get('email', '').strip()
    password = data.get('password', '').strip()
    
    if User.query.filter_by(email=email).first() or User.query.filter_by(username=username).first():
        return jsonify({'status': 'error', 'message': 'Account already exists'}), 400
        
    user_role = Role.query.filter_by(name='User').first()
    new_user = User(
        username=username, 
        email=email, 
        password=generate_password_hash(password, method='scrypt'), 
        role_id=user_role.id
    )
    
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'status': 'success', 'message': 'Created successfully!'}), 201

@auth_bp.route('/signin', methods=['POST'])
def signin():
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '').strip()

    user = User.query.filter_by(username=username).first()
    
    if user and check_password_hash(user.password, password):
        login_user(user)
        
        session['user_id'] = user.id
        session['username'] = user.username
        session['role'] = user.role.name
        
        return jsonify({
            'status': 'success', 
            'message': 'Redirecting...',
            'role': user.role.name
        }), 200
        
    return jsonify({'status': 'error', 'message': 'Invalid credentials'}), 401
    
@auth_bp.route('/logout')
def logout():
    logout_user()
    session.clear()
    return redirect(url_for('index'))