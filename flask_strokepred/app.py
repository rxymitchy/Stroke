from flask import Flask, render_template, request, jsonify
import pickle

app = Flask(__name__)

# Load the trained stroke prediction model
with open('model.pkl', 'rb') as f:
    model = pickle.load(f)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Get user input from the form
        age = float(request.form['age'])
        gender = request.form['gender']
        hypertension = request.form['hypertension']
        heart_disease = request.form['heart_disease']
        glucose_level = float(request.form['glucose_level'])
        work_type = request.form['work_type']
        residency = request.form['residency']
        married = request.form['married']
        bmi = float(request.form['bmi'])
        smoking_status = request.form['smoking_status']

        hypertension = 1 if hypertension.lower() == 'yes' else 0
        heart_disease = 1 if heart_disease.lower() == 'yes' else 0

        prediction = model.predict([[age, gender, hypertension, heart_disease, glucose_level,
                                     work_type, residency, married, bmi, smoking_status]])
        
        return render_template('result.html', prediction=prediction)

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
