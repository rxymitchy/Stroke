from flask import Flask, render_template, request, redirect, url_for, session, g, flash
from flask_mail import Mail, Message
from pathlib import Path

import logging
import sqlite3
import re



app = Flask(__name__)
app.secret_key = 'your_secret_key'  
DATABASE = 'database.db'

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Flask-Mail configuration
app.config['MAIL_SERVER'] = 'default_mail_server'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_DEFAULT_SENDER'] = 'default_sender_email'

mail = Mail(app)

# Create a database if it doesn't exist
Path(DATABASE).touch()

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


@app.route('/')
def home():
    username = session.get('username')
    if username:
        user = get_user(username)
        if user:
            return render_template('home.html', username=user['username'])
        else:
            flash('User not found. Please log in again.', 'error')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        user_mail_server = request.form.get('mail_server', 'default_mail_server')
        user_mail_username = request.form.get('mail_username', 'default_sender_email')
        user_mail_password = request.form.get('mail_password', 'default_mail_password')

        # Check if the username is already taken
        if is_username_taken(username):
            flash('Username is already taken. Please choose another username.', 'error')
            return render_template('register.html')

        # Check if the email is already registered
        if is_email_registered(email):
            flash('Email is already registered. Please use another email.', 'error')
            return render_template('register.html')

        # Check if passwords match
        if password != confirm_password:
            flash('Passwords do not match. Please try again.', 'error')
            return render_template('register.html')

        # Check password rules
        if not (len(password) >= 8 and re.search("[a-z]", password) and re.search("[A-Z]", password) and re.search("[!@#$%^&*(),.?\":{}|<>]", password)):
            flash('Password must be at least 8 characters and include a mix of uppercase, lowercase, and special characters.', 'error')
            return render_template('register.html')

        # Check email format
        if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
            flash('Invalid email format. Please use a valid email address.', 'error')
            return render_template('register.html')

        # Save the user to the database
        save_user(username, email, password)

        # Send confirmation message via email
        send_email_confirmation(email, user_mail_server, user_mail_username, user_mail_password)

        # Redirect to login page with a recommendation to log in
        return redirect(url_for('login', recommend_login=True))

    return render_template('register.html')

# Function to send a confirmation email
def send_email_confirmation(email, mail_server, mail_username, mail_password):
    confirmation_subject = 'Registration Confirmation'
    confirmation_body = 'Thank you for registering! Your account has been successfully created.'

    msg = Message(confirmation_subject, recipients=[email])
    msg.body = confirmation_body

    # Update the mail configuration dynamically
    app.config['MAIL_SERVER'] = mail_server
    app.config['MAIL_USERNAME'] = mail_username
    app.config['MAIL_PASSWORD'] = mail_password

    mail.init_app(app)  # Re-initialize the mail instance with updated configuration

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


def predict_stroke(features):
 
    # Extract relevant features
    age, gender_encoded, hypertension, heart_disease, glucose_level, \
    work_type_encoded, residency_encoded, married_encoded, bmi, smoking_status_encoded = features

    # Example of a simple logic to determine stroke likelihood
    if age > 60 or (gender_encoded == 1 and age > 45) or (hypertension == 1 and age > 30) or \
            (heart_disease == 1 and age > 40) or glucose_level > 200 or \
            (work_type_encoded == 2 and age > 35) or (residency_encoded == 1 and age > 50) or \
            married_encoded == 1 or (bmi > 30 and smoking_status_encoded == 3):
        result = "You are likely to get a stroke."
        prediction_proba = calculate_probability(age, gender_encoded, hypertension, heart_disease,
                                                 glucose_level, work_type_encoded, residency_encoded,
                                                 married_encoded, bmi, smoking_status_encoded)
    else:
        result = "You are not likely to get a stroke."
        prediction_proba = calculate_probability(age, gender_encoded, hypertension, heart_disease,
                                                 glucose_level, work_type_encoded, residency_encoded,
                                                 married_encoded, bmi, smoking_status_encoded)

    # Prepare the response
    response = {
        'result': result,
        'prediction_proba': float(prediction_proba)
    }
    return response

def calculate_probability(age, gender_encoded, hypertension, heart_disease,
                          glucose_level, work_type_encoded, residency_encoded,
                          married_encoded, bmi, smoking_status_encoded):
    # Replace this with your custom logic for calculating the probability
    # This is just a placeholder, you should adjust it based on your actual model or rules
    probability = 0.5  # Default probability
    probability += 0.2 if age > 50 else 0
    probability += 0.1 if hypertension == 1 else 0
    probability += 0.1 if heart_disease == 1 else 0
    probability += 0.1 if glucose_level > 150 else 0
    probability += 0.1 if bmi > 25 else 0

    return probability

@app.route('/predict', methods=['POST'])
def predict_stroke_route():
    if request.method == 'POST':
        form_data = request.form.to_dict()
        try:
            processed_features = preprocess_form_data(form_data)
            app.logger.debug(f"Processed Features: {processed_features}")  # Add this line for debugging

            # Call your prediction function directly
            response = predict_stroke(processed_features)

            # Add the prediction results to the response
            prediction_proba = response['prediction_proba']
            result = response['result']

            # Prepare the response for JSON
            json_response = {
                'prediction_proba': prediction_proba,
                'result': result
            }

            return render_template('index.html', prediction=json_response)
        except Exception as e:
            app.logger.error(f"Error processing form data or making prediction: {e}")

            # Return an error message with details
            error_message = f"An error occurred during prediction: {str(e)}"
            return render_template('index.html', error_message=error_message), 500



def preprocess_form_data(form_data):
    # Convert and preprocess form data to match the structure of your training data
    # Modify this based on your specific feature names and types
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

    gender_encoded = 1 if gender.lower() == 'male' else 0
    work_type_encoded = {'never_worked': 0, 'self_employed': 3, 'private': 2, 'children': 4, 'govt_job': 0}[work_type]
    residency_encoded = 1 if residency.lower() == 'urban' else 0
    married_encoded = 1 if married.lower() == 'yes' else 0
    smoking_status_encoded = {'formerly_smoked': 1, 'never_smoked': 2, 'unknown': 0, 'smokes': 3}[smoking_status]

    features = [age, gender_encoded, hypertension, heart_disease, glucose_level,
                work_type_encoded, residency_encoded, married_encoded, bmi, smoking_status_encoded]

    return features


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
