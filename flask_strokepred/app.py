from flask import Flask, render_template, request
import joblib
import logging
import numpy as np
from sklearn.base import BaseEstimator

app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

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
    app.run(debug=True)
