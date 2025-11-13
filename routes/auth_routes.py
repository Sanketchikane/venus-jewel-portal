# routes/auth_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, make_response
import config
from backends.register_backend import submit_registration
from backends.utils_backend import get_credentials_sheet, get_registration_sheet, get_user_record, reset_password_for_username

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

        # Admin Login
        if username == config.ADMIN_USERNAME and password == config.ADMIN_PASSWORD:
            session.clear()
            session["username"] = username
            session["is_admin"] = True
            flash("Welcome, Admin!", "success")
            return redirect(url_for("admin.admin_dashboard"))

        # VenusFiles Default Account
        if username == config.VENUSFILES_USERNAME and password == config.VENUSFILES_PASSWORD:
            session.clear()
            session["username"] = username
            session["venus_user"] = True
            flash("Welcome Venus File Account!", "success")
            return redirect(url_for("file.venus_upload_dashboard"))

        # Regular User
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
    """
    Admin-reviewed password reset flow.
    """
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "").strip()
        confirm_password = request.form.get("confirm_password", "").strip()

        if not all([username, new_password, confirm_password]):
            flash("⚠️ Fill all fields.", "warning")
            return redirect(url_for("auth.forgot_password"))

        if new_password != confirm_password:
            flash("❌ Passwords do not match.", "danger")
            return redirect(url_for("auth.forgot_password"))

        try:
            ok = reset_password_for_username(username, new_password)
            if ok:
                flash("✅ Password reset successful. Please login with new password.", "success")
                return redirect(url_for("auth.login"))
            else:
                flash("❌ Username not found.", "danger")
                return redirect(url_for("auth.forgot_password"))
        except Exception as e:
            print("Error resetting password:", e)
            flash("⚠️ Could not reset password. Try later.", "danger")
            return redirect(url_for("auth.forgot_password"))

    return render_template("forgot_password.html")
