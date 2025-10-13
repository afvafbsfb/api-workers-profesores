from flask import Flask, jsonify

app = Flask(__name__)

@app.route('/usuarios', strict_slashes=False)
def usuarios():
    # Handle the /usuarios endpoint without redirection
    return jsonify({'message': 'Usuarios endpoint reached'})