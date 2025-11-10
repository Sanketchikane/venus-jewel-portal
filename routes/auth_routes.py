# routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from google.oauth2 import service_account
import gspread
from datetime import datetime
import config
from backends.register_backend import submit_registration
from backends.utils_backend import get_credentials_sheet, get_registration_sheet, get_user_record

auth_bp = Blueprint("auth", __name__)

# splash
@auth_bp.route("/")
def root():
    return redirect(url_for("auth.splash"))

@auth_bp.route("/splash")
def splash():
    return render_template("splash.html")

# login
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # admin quick checks
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session.update({"username": username, "admin": True})
            return redirect(url_for("admin.admin_dashboard"))

        if username == config.VENUSFILES_USERNAME and password == config.VENUSFILES_PASSWORD:
            session.update({"username": username, "venus_user": True})
            return redirect(url_for("file.venus_upload_dashboard"))

        # regular user: check Credentials sheet
        user = get_user_record(username)
        if user and user.get("Password") == password:
            session.update({"username": username, "admin": False})
            resp = make_response(redirect(url_for("auth.dashboard")))
            return resp

        flash("Invalid credentials.", "danger")

    return render_template("login.html")

# register
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            submit_registration(request.form)
            flash("✅ Registration request sent successfully. Admin will approve your account.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"❌ Registration failed: {e}", "danger")
            return render_template("register.html")
    return render_template("register.html")

# dashboard
@auth_bp.route("/dashboard")
def dashboard():
    if not session.get("username") or session.get("admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", user=session.get("username"))

# logout
@auth_bp.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(url_for("auth.login") + "?showSplash=1"))
    resp.set_cookie("username", "", expires=0)
    resp.set_cookie("password", "", expires=0)
    return resp
