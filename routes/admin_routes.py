# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from backends import admin_backend
import traceback

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/admin-dashboard")
def admin_dashboard():
    return render_template("admin_dashboard.html", user=session.get("username"))

@admin_bp.route("/admin-users")
def admin_users():
    try:
        users = admin_backend.get_approved_users()
        return render_template("admin_users.html", users=users)
    except Exception as e:
        print("Error loading users:", e)
        return "Internal Server Error", 500

@admin_bp.route("/create-credential", methods=["POST"])
def create_credential():
    try:
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if not all([email, username, password]):
            return "Missing data", 400

        # Create credential in Sheet and mark user approved
        admin_backend.create_credential_entry(email, username, password)

        flash(f"User {username} approved successfully!", "success")
        return redirect(url_for("admin.admin_users"))
    except Exception as e:
        print("Approval error:", e)
        traceback.print_exc()
        return "Internal Server Error", 500
