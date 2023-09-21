from flask import Flask, request, render_template, flash, jsonify
import pickle

app = Flask(__name__)

@app.route("/")
def index():
    return render_template('index.html')

@app.route("/output", methods=["POST", "GET"])
def output():
    if request.method == 'POST':
        g = convert_to_numeric(request.form['gender'], {"male": 1, "female": 0}, default=2)
        a = convert_to_range(request.form['age'], 0.08, 82)
        hyt = convert_to_numeric(request.form['hypertension'], {"yes": 1, "no": 0})
        ht = convert_to_numeric(request.form['heart-disease'], {"yes": 1, "no": 0})
        m = convert_to_numeric(request.form['marriage'], {"yes": 1, "no": 0})
        w = convert_work_type(request.form['worktype'])
        r = convert_residency_type(request.form['residency'], {"urban": 1, "rural": 0})
        gl = convert_to_range(request.form['glucose'], 55, 271)
        b = convert_to_range(request.form['bmi'], 10.3, 97.6)
        s = convert_to_numeric(request.form['smoking'], {"unknown": 0, "never smoked": 1, "formerly smoked": 2, "smokes": 3}, default=0)

        try:
            prediction = stroke_pred(g, a, hyt, ht, m, w, r, gl, b, s)
            return render_template('output.html', prediction=prediction)

        except ValueError:
            return "Please Enter Valid Values"

# prediction-model
def stroke_pred(g, a, hyt, ht, m, w, r, gl, b, s):
    # load model
    model = pickle.load(open('model.pkl', 'rb'))

    # predictions
    result = model.predict([[g, a, hyt, ht, m, w, r, gl, b, s]])

    # output
    if result[0] == 1:
        pred = 'You are likely to have a stroke'
    else:
        pred = 'You have no risk of having a stroke'

    return pred

def convert_to_numeric(value, mapping, default=None):
    return mapping.get(value, default)

def convert_to_range(value, min_value, max_value):
    try:
        value = int(value)
        return (value - min_value) / (max_value - min_value)
    except ValueError:
        return None

def convert_work_type(value):
    work_types = {"government": 0, "student": 1, "private": 2, "self-employed": 3}
    return work_types.get(value.lower(), 4)

def convert_residency_type(value, mapping):
    return mapping.get(value.lower(), 0)

if __name__ == '__main__':
	app.run(debug=True)