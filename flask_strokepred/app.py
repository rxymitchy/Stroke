from flask import Flask, render_template, request, redirect, url_for, session, g
from flask_mail import Mail, Message
from sklearn.base import BaseEstimator
from pathlib import Path

import joblib
import logging
import numpy as np
import sqlite3


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Change this to a secure secret key
DATABASE = 'database.db'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'your_mail_server'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = 'your_mail_username'
app.config['MAIL_PASSWORD'] = 'your_mail_password'
app.config['MAIL_DEFAULT_SENDER'] = 'your_mail_username'

mail = Mail(app)

# Create a database if it doesn't exist
Path(DATABASE).touch()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        app.logger.info("Creating a new database connection.")
        db = g._database = sqlite3.connect(DATABASE)
    return db


@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

# Initialize the database with a user table
def init_db():
    with app.app_context():
        db = get_db()
        try:
            with app.open_resource('schema.sql', mode='r') as f:
                db.cursor().executescript(f.read())
            db.commit()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error initializing database: {e}")

init_db()

# Define the EnsembleModel class
class EnsembleModel(BaseEstimator):
    def __init__(self, models):
        self.models = models  # A list of the individual models

    def fit(self, X, y):
        # Fit each of the models on the data
        for model in self.models:
            model.fit(X, y)
        return self

    def predict_proba(self, X):
        # Averaging the predict_proba of each of the models
        predictions = [model.predict_proba(X)[:, 1] for model in self.models]
        return np.mean(predictions, axis=0)

    def predict(self, X):
        # Convert probabilities to final predictions
        probabilities = self.predict_proba(X)
        return np.where(probabilities > 0.5, 1, 0)  # Using 0.5 as threshold for binary classification

# Attempt to load the trained model and scaler
try:
    model_path = 'ensemble_models(1).pkl'
    scaler_path = 'scalers(1).pkl'

    # Check if the paths are specified correctly
    app.logger.info(f"Attempting to load model from: {model_path}")
    app.logger.info(f"Attempting to load scaler from: {scaler_path}")

    model = joblib.load(model_path)
    scaler = joblib.load(scaler_path)  # Load the scaler

    if not hasattr(model, 'predict'):
        raise ValueError("Loaded object is not a model.")

    app.logger.info("Model and scaler loaded successfully.")
except Exception as e:
    model = None
    scaler = None
    app.logger.error(f"Error loading model or scaler: {e}")

@app.route('/')
def home():
    if 'username' in session:
        return render_template('home.html', username=session['username'])
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Check if the username is already taken
        if is_username_taken(username):
            return render_template('register.html', error='Username is already taken. Please choose another username.')

        # Check if the email is already registered
        if is_email_registered(email):
            return render_template('register.html', error='Email is already registered. Please use another email.')

        # Check if passwords match
        if password != confirm_password:
            return render_template('register.html', error='Passwords do not match. Please try again.')

        # Save the user to the database
        save_user(username, email, password)

        # Send confirmation message via email
        send_email_confirmation(email)

        # Redirect to login page with a recommendation to log in
        return redirect(url_for('login', recommend_login=True))

    return render_template('register.html')

# Function to send a confirmation email
def send_email_confirmation(email):
    confirmation_subject = 'Registration Confirmation'
    confirmation_body = 'Thank you for registering! Your account has been successfully created.'

    msg = Message(confirmation_subject, recipients=[email])
    msg.body = confirmation_body

    try:
        mail.send(msg)
    except Exception as e:
        print(f"Error sending email confirmation: {str(e)}")


# Function to check if a username is already taken
def is_username_taken(username):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ?', (username,))
    return cursor.fetchone() is not None

# Function to check if an email is already registered
def is_email_registered(email):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE email = ?', (email,))
    return cursor.fetchone() is not None

# Function to save a user to the database
def save_user(username, email, password):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                   (username, email, password))
    db.commit()

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_or_email = request.form['login_info']
        password = request.form['password']

        # Check if the user exists and the password is correct
        user = get_user(username_or_email)
        if user and user['password'] == password:
            session['username'] = user['username']
            return redirect(url_for('home'))

        # If login is unsuccessful, display an error message
        return render_template('login.html', error='Invalid username/email or password')

    recommend_login = request.args.get('recommend_login', False)
    return render_template('login.html', recommend_login=recommend_login)

# Function to retrieve user details based on username or email
def get_user(username_or_email):
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users WHERE username = ? OR email = ?',
                   (username_or_email, username_or_email))
    result = cursor.fetchone()

    if result:
        # Convert the tuple to a dictionary for easier access
        user_dict = {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3]
        }
        return user_dict
    else:
        return None

@app.route('/users')
def view_users():
    users = get_all_users()
    return render_template('users.html', users=users)

# Function to retrieve all users from the database
def get_all_users():
    db = get_db()
    cursor = db.cursor()
    cursor.execute('SELECT * FROM users')
    results = cursor.fetchall()

    users = []
    for result in results:
        user_dict = {
            'id': result[0],
            'username': result[1],
            'email': result[2],
            'password': result[3]
        }
        users.append(user_dict)

    return users

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

@app.route('/predict')
def prediction_page():
    return render_template('index.html')

@app.route('/predict', methods=['POST'])
def predict():
    if not model or not scaler:
        app.logger.error("Model or scaler not loaded properly.")
        return "Model or scaler not loaded properly.", 500

    if request.method == 'POST':
        form_data = request.form.to_dict()
        try:
            processed_features = preprocess_form_data(form_data)
            # Apply scaling to the processed features
            scaled_features = scaler.transform([processed_features])
            prediction = model.predict(scaled_features)
            result = "You are likely to get a stroke." if prediction[0] == 1 else "You are not likely to get a stroke."
        except Exception as e:
            app.logger.error(f"Error processing form data or making prediction: {e}")
            return "An error occurred during prediction.", 500
        
        return render_template('index.html', result=result)

def preprocess_form_data(form_data):
    # Convert and preprocess form data here to match the structure of your training data
    age = float(form_data['age'])
    gender = form_data['gender']
    hypertension = form_data['hypertension']
    heart_disease = form_data['heart_disease']
    glucose_level = float(form_data['glucose_level'])
    work_type = form_data['work_type']
    residency = form_data['residency']
    married = form_data['married']
    bmi = float(form_data['bmi'])
    smoking_status = form_data['smoking_status']

    hypertension = 1 if hypertension.lower() == 'yes' else 0
    heart_disease = 1 if heart_disease.lower() == 'yes' else 0

    # One-hot encode categorical variables (adjust based on your encoding)
    gender_encoded = 1 if gender.lower() == 'male' else 0
    work_type_encoded = {'never_worked': 0, 'self_employed': 3, 'private': 2, 'children': 4, 'govt_job':0}[work_type]
    residency_encoded = 1 if residency.lower() == 'urban' else 0
    married_encoded = 1 if married.lower() == 'yes' else 0
    smoking_status_encoded = {'formerly_smoked': 1, 'never_smoked': 2, 'unknown': 0, 'smokes': 3}[smoking_status]

    # Combine all features into a single array
    features = [age, gender_encoded, hypertension, heart_disease, glucose_level,
                work_type_encoded, residency_encoded, married_encoded, bmi, smoking_status_encoded]

    return features

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
