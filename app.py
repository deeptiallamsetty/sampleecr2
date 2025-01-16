import os
import awsgi
from flask import Flask, jsonify, request
from flask_sqlalchemy import SQLAlchemy
from datetime import timedelta
from flask_jwt_extended import (
    JWTManager, create_access_token, create_refresh_token, jwt_required, get_jwt_identity
)

app = Flask(__name__)

def handler(event, context):
    return awsgi.response(app, event, context)

app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'mysql+pymysql://admin:admin123@terraform-20250116192216465000000001.cxac8gmue0ap.us-east-1.rds.amazonaws.com:3306/flaskdb'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure the secret key for JWT
#app.config['JWT_SECRET_KEY'] = 'your-secret-key'  # Replace with a strong secret key
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'fallback-secret-key')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(minutes=15)  # Token valid for 15 minutes
app.config['JWT_REFRESH_TOKEN_EXPIRES'] = timedelta(days=30)    # Refresh token valid for 30 days
db = SQLAlchemy(app)
jwt = JWTManager(app)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    completed = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.String(80), db.ForeignKey('user.username'), nullable=False)


def seed_database():
    """Seed the database with sample users."""
    if not User.query.filter_by(username="user1").first():
        sample_users = [
            {"username": "user1", "password": "password1"},
            {"username": "user2", "password": "password2"},
        ]
        for user_data in sample_users:
            user = User(username=user_data["username"], password=user_data["password"])
            db.session.add(user)
        db.session.commit()
        print("Database seeded successfully!")
    else:
        print("Database already seeded.")    

with app.app_context():
    db.create_all()
    seed_database()

# In-memory "database" for demo purposes
#users = {"user1": "password1", "user2": "password2"}

@app.route('/')
def hello():
    return "Hello, world!"

# Route to log in and get a token
@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()

    # Validate username and password
#    if username in users and users[username] == password:
#        access_token = create_access_token(identity=username)
#        refresh_token = create_refresh_token(identity=username)
#        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
#    return jsonify({"msg": "Invalid username or password"}), 401

    if user and user.password == password:
        access_token = create_access_token(identity=username)
        refresh_token = create_refresh_token(identity=username)
        return jsonify(access_token=access_token, refresh_token=refresh_token), 200
    
    return jsonify({"msg": "Invalid username or password"}), 401

@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    new_access_token = create_access_token(identity=current_user)
    return jsonify(access_token=new_access_token), 200

# Protected route
@app.route('/protected', methods=['GET'])
@jwt_required()
def protected():
    # Access the identity of the current user
    current_user = get_jwt_identity()
    return jsonify(logged_in_as=current_user), 200

@app.route('/todo', methods=['POST'])
@jwt_required()
def create_task():
    user_id = get_jwt_identity()
    data = request.get_json()

    # Validate the input
    if not data or not data.get('title'):
        return jsonify({"msg": "Missing title"}), 400
#    user = User.query.get(user_id) 
#    if not user: 
#        return jsonify({"msg": "Invalid user ID"}), 400    

    try:
        new_task = Todo(
            title=data['title'],
            description=data.get('description'),
            completed=data.get('completed', False),
            user_id=user_id
        )
        db.session.add(new_task)
        db.session.commit()
        return jsonify({"msg": "Task created", "task": new_task.id}), 201
    except Exception as e:
        print(f"Error creating task: {e}")
        return jsonify({"msg": "Internal server error"}), 500

@app.route('/todo', methods=['GET'])
@jwt_required()
def get_tasks():
    user_id = get_jwt_identity()
    tasks = Todo.query.filter_by(user_id=user_id).all()
    return jsonify([{
        "id": task.id,
        "title": task.title,
        "description": task.description,
        "completed": task.completed
    } for task in tasks])

@app.route('/todo/<int:task_id>', methods=['PUT'])
@jwt_required()
def update_task(task_id):
    user_id = get_jwt_identity()
    task = Todo.query.filter_by(id=task_id, user_id=user_id).first_or_404()
    data = request.get_json()
    task.title = data.get('title', task.title)
    task.description = data.get('description', task.description)
    task.completed = data.get('completed', task.completed)
    db.session.commit()
    return jsonify({"msg": "Task updated"})

@app.route('/todo/<int:task_id>', methods=['DELETE'])
@jwt_required()
def delete_task(task_id):
    user_id = get_jwt_identity()
    task = Todo.query.filter_by(id=task_id, user_id=user_id).first_or_404()
    db.session.delete(task)
    db.session.commit()
    return jsonify({"msg": "Task deleted"})

if __name__ == "__main__":
    app.run(debug=True)
