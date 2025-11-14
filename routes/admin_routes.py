# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from backends import admin_backend
from backends.utils_backend import get_credentials_sheet
import traceback

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


# ------------------------------------------
# ADMIN DASHBOARD
# ------------------------------------------
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


# ------------------------------------------
# ADMIN USERS PAGE
# ------------------------------------------
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


# ------------------------------------------
# FIXED: PENDING REGISTRATIONS API
# ------------------------------------------
@admin_bp.route("/api/pending-registrations")
def pending_registrations():
    try:
        pending = admin_backend.get_pending_users()
        formatted = []

        for r in pending:
            formatted.append({
                "Full Name": r.get("Full Name", ""),
                "Email": r.get("Email Address", ""),
                "Contact": r.get("Contact Number", ""),
                "Organization": r.get("Organization", ""),
                "Status": r.get("Status", "Pending")
            })

        return jsonify({"pending": formatted})

    except Exception as e:
        print("Error fetching pending registrations:", e)
        traceback.print_exc()
        return jsonify({"pending": []})


# ------------------------------------------
# CREATE CREDENTIALS
# ------------------------------------------
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
            flash("⚠️ Missing information in approval form", "warning")
            return redirect(url_for("admin.admin_users"))

        admin_backend.create_credential_entry(email, username, password)

        # show message on admin pages (we render flash in admin_dashboard)
        flash(f"✅ User '{username}' added and approved successfully.", "success")
        return redirect(url_for("admin.admin_users"))

    except Exception as e:
        print("Approval error:", e)
        traceback.print_exc()
        flash("❌ Internal Server Error during approval", "danger")
        return redirect(url_for("admin.admin_users"))


# ------------------------------------------
# VIEW USER PROFILE
# ------------------------------------------
@admin_bp.route("/view-user/<username>")
def view_user(username):
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        ws = get_credentials_sheet()
        records = ws.get_all_records()

        # Lookup username EXACTLY (case/whitespace-insensitive)
        user = next(
            (u for u in records
             if str(u.get("Username", "")).strip().lower() == username.strip().lower()),
            None
        )

        if not user:
            flash("⚠️ User not found.", "warning")
            return redirect(url_for("admin.admin_users"))

        return render_template("view_user.html", user=user)

    except Exception as e:
        print("Error loading user profile:", e)
        traceback.print_exc()
        flash("⚠️ Internal error loading profile.", "danger")
        return redirect(url_for("admin.admin_users"))


# ------------------------------------------
# UPDATE USER PROFILE
# ------------------------------------------
@admin_bp.route("/update-user/<username>", methods=["POST"])
def update_user(username):
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        ws = get_credentials_sheet()
        records = ws.get_all_records()

        for i, row in enumerate(records, start=2):
            if str(row.get("Username", "")).strip().lower() == username.strip().lower():

                # Update ONLY existing columns
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
