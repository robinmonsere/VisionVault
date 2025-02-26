from flask import Flask, render_template, send_from_directory
import os

app = Flask(__name__)

# Serve the main page
@app.route('/')
def index():
    return render_template('index.html')

# Serve static files (CSS, JS)
@app.route('/static/<path:filename>')
def static_files(filename):
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=True)