# app.py
from flask import Flask
import os

# create app
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get('FLASK_SECRET', 'your_secret_key_here')

# load config early
import config  # noqa: E402

# register routes (blueprints)
from routes import register_routes  # noqa: E402
register_routes(app)

if __name__ == "__main__":
    from waitress import serve
    port = int(os.environ.get("PORT", 10000))
    serve(app, host="0.0.0.0", port=port)
