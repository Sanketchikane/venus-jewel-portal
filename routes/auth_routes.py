# routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
from backends.register_backend import submit_registration
from backends.utils_backend import get_user_record
from backends.forgot_password_backend import reset_password_for_username
import config

auth_bp = Blueprint("auth", __name__)

# -------------------------
# Splash
# -------------------------
@auth_bp.route("/")
def root():
    return redirect(url_for("auth.splash"))

@auth_bp.route("/splash")
def splash():
    return render_template("splash.html")

# -------------------------
# Login
# -------------------------
@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":

        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        # Admin Login
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session.clear()
            session["username"] = username
            session["is_admin"] = True
            return redirect(url_for("admin.admin_dashboard"))

        # Venus Files Account
        if username == config.VENUSFILES_USERNAME and password == config.VENUSFILES_PASSWORD:
            session.clear()
            session["username"] = username
            session["venus_user"] = True
            return redirect(url_for("file.venus_upload_dashboard"))

        # Normal User Login
        user = get_user_record(username)
        if user and user.get("Password") == password:
            session.clear()
            session["username"] = username
            session["is_admin"] = False
            return redirect(url_for("auth.dashboard"))

        flash("Invalid username or password.", "danger")

    return render_template("login.html")

# -------------------------
# Register
# -------------------------
@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            submit_registration(request.form)
            flash("Registration submitted. Admin approval pending.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash("Error: " + str(e), "danger")
    return render_template("register.html")

# -------------------------
# Dashboard
# -------------------------
@auth_bp.route("/dashboard")
def dashboard():
    if not session.get("username") or session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", user=session.get("username"))

# -------------------------
# Logout
# -------------------------
@auth_bp.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(url_for("auth.login") + "?showSplash=1"))
    resp.set_cookie("username", "", expires=0)
    resp.set_cookie("password", "", expires=0)
    return resp

# -------------------------
# Forgot Password
# -------------------------
@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        username = request.form.get("username")
        new_pass = request.form.get("new_password")
        confirm = request.form.get("confirm_password")

        if new_pass != confirm:
            flash("Passwords do not match!", "danger")
            return redirect(url_for("auth.forgot_password"))

        if reset_password_for_username(username, new_pass):
            flash("Password updated successfully!", "success")
            return redirect(url_for("auth.login"))
        else:
            flash("Username not found.", "danger")

    return render_template("forgot_password.html")
