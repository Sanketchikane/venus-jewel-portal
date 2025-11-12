from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from backends import admin_backend
from backends.utils_backend import get_credentials_sheet
import traceback

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

# -------------------------
# Admin Dashboard
# -------------------------
@admin_bp.route("/admin-dashboard")
def admin_dashboard():
    try:
        if not session.get("admin"):  # Check for the admin session key
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
        if not session.get("admin"):  # Check for the admin session key
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
# Approve User / Create Credential
# -------------------------
@admin_bp.route("/create-credential", methods=["POST"])
def create_credential():
    try:
        if not session.get("admin"):  # Check for the admin session key
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if not all([email, username, password]):
            flash("⚠️ Missing information in approval form", "warning")
            return redirect(url_for("admin.admin_users"))

        # Create credential entry (approve user and add to credentials)
        admin_backend.create_credential_entry(email, username, password)
        flash(f"✅ User '{username}' added and approved successfully.", "success")
        return redirect(url_for("admin.admin_users"))

    except Exception as e:
        print("Approval error:", e)
        traceback.print_exc()
        flash("❌ Internal Server Error during approval", "danger")
        return redirect(url_for("admin.admin_users"))


# -------------------------
# View Single User Profile
# -------------------------
@admin_bp.route("/view-user/<username>")
def view_user(username):
    try:
        if not session.get("admin"):  # Check for the admin session key
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        ws = get_credentials_sheet()
        records = ws.get_all_records()
        user = next((u for u in records if str(u.get("Username", "")).lower() == username.lower()), None)

        if not user:
            flash("⚠️ User not found.", "warning")
            return redirect(url_for("admin.admin_users"))

        return render_template("view_user.html", user=user)
    except Exception as e:
        print("Error loading user profile:", e)
        traceback.print_exc()
        flash("⚠️ Internal error loading profile.", "danger")
        return redirect(url_for("admin.admin_users"))


# -------------------------
# Update User Profile
# -------------------------
@admin_bp.route("/update-user/<username>", methods=["POST"])
def update_user(username):
    try:
        if not session.get("admin"):  # Check for the admin session key
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        ws = get_credentials_sheet()
        records = ws.get_all_records()

        for i, row in enumerate(records, start=2):
            if str(row.get("Username", "")).lower() == username.lower():
                for key in row.keys():
                    if key in request.form:
                        ws.update_cell(i, list(row.keys()).index(key) + 1, request.form[key])
                flash("✅ User profile updated successfully.", "success")
                return redirect(url_for("admin.view_user", username=username))

        flash("⚠️ Failed to update user.", "danger")
        return redirect(url_for("admin.admin_users"))

    except Exception as e:
        print("Error updating user:", e)
        traceback.print_exc()
        flash("❌ Internal Server Error while updating user.", "danger")
        return redirect(url_for("admin.admin_users"))
