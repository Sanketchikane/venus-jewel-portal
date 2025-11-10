# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from backends import admin_backend
import traceback

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# -------------------------
# Admin Dashboard
# -------------------------
@admin_bp.route("/admin-dashboard")
def admin_dashboard():
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))
        return render_template("admin_dashboard.html", user=session.get("username"))
    except Exception as e:
        print("Error loading admin dashboard:", e)
        traceback.print_exc()
        return "Internal Server Error", 500


# -------------------------
# Admin → View all approved users
# -------------------------
@admin_bp.route("/admin-users")
def admin_users():
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        users = admin_backend.get_approved_users()
        return render_template("admin_users.html", users=users)
    except Exception as e:
        print("Error loading approved users:", e)
        traceback.print_exc()
        return "Internal Server Error", 500


# -------------------------
# API → Pending Registrations for AJAX
# -------------------------
@admin_bp.route("/api/pending-registrations")
def pending_registrations():
    try:
        pending = admin_backend.get_pending_users()
        return jsonify({"pending": pending})
    except Exception as e:
        print("Error fetching pending registrations:", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


# -------------------------
# Approve User / Create Credential (No Email)
# -------------------------
@admin_bp.route("/create-credential", methods=["POST"])
def create_credential():
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if not all([email, username, password]):
            flash("Missing information in approval form", "warning")
            return redirect(url_for("admin.admin_users"))

        # Call backend to approve user
        admin_backend.create_credential_entry(email, username, password)

        flash(f"✅ User '{username}' approved successfully!", "success")
        return redirect(url_for("admin.admin_users"))
    except Exception as e:
        print("Approval error:", e)
        traceback.print_exc()
        flash("Internal Server Error during approval", "danger")
        return redirect(url_for("admin.admin_users"))
