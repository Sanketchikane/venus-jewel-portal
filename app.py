from flask import Flask, redirect, url_for
from routes.auth_routes import auth_bp
from routes.admin_routes import admin_bp
from routes.file_routes import file_bp

app = Flask(__name__)
app.secret_key = "venus_secret_key_2025"

# ✅ Register all blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(file_bp)

@app.route("/")
def home():
    return redirect(url_for("auth.login"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
