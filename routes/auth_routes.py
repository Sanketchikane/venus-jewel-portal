# routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
import config
from backends.register_backend import submit_registration
from backends.utils_backend import get_credentials_sheet, get_registration_sheet, get_user_record
from backends.forgot_password_backend import submit_forgot_password_request, reset_password_for_username

auth_bp = Blueprint("auth", __name__)

@auth_bp.route("/")
def root():
    return redirect(url_for("auth.splash"))

@auth_bp.route("/splash")
def splash():
    return render_template("splash.html")

@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()

        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session.clear()
            session["username"] = username
            session["is_admin"] = True
            flash("Welcome, Admin!", "success")
            return redirect(url_for("admin.admin_dashboard"))

        if username == config.VENUSFILES_USERNAME and password == config.VENUSFILES_PASSWORD:
            session.clear()
            session["username"] = username
            session["venus_user"] = True
            flash("Welcome Venus File Account!", "success")
            return redirect(url_for("file.venus_upload_dashboard"))

        user = get_user_record(username)
        if user and user.get("Password") == password:
            session.clear()
            session["username"] = username
            session["is_admin"] = False
            return redirect(url_for("auth.dashboard"))

        flash("Invalid credentials.", "danger")
    return render_template("login.html")

@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        try:
            submit_registration(request.form)
            flash("✅ Registration request sent! The admin will review your details shortly.", "success")
            return redirect(url_for("auth.login"))
        except Exception as e:
            flash(f"❌ Registration failed: {e}", "danger")
            return render_template("register.html")
    return render_template("register.html")

@auth_bp.route("/dashboard")
def dashboard():
    if not session.get("username") or session.get("is_admin"):
        flash("Access denied.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("dashboard.html", user=session.get("username"))

@auth_bp.route("/logout")
def logout():
    session.clear()
    resp = make_response(redirect(url_for("auth.login") + "?showSplash=1"))
    resp.set_cookie("username", "", expires=0)
    resp.set_cookie("password", "", expires=0)
    return resp

@auth_bp.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():
    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip()
        organization = request.form.get("organization", "").strip()
        contact_number = request.form.get("contact_number", "").strip()

        if not all([full_name, username, email, organization, contact_number]):
            flash("⚠️ Please fill all fields before submitting.", "warning")
            return redirect(url_for("auth.forgot_password"))

        try:
            submit_forgot_password_request({
                "full_name": full_name,
                "username": username,
                "email": email,
                "organization": organization,
                "contact_number": contact_number,
            })
            flash("✅ Password reset request submitted. The admin will verify and reset your account soon.", "success")
            return redirect(url_for("auth.login"))
        except Exception:
            flash("⚠️ Could not submit your request. Please try again later.", "danger")
            return redirect(url_for("auth.forgot_password"))
    return render_template("forgot_password.html")
