# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
import traceback
from backends import admin_backend
from backends.utils_backend import get_credentials_sheet

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("is_admin"):
        flash("Unauthorized access.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("admin_dashboard.html", user=session.get("username"))

@admin_bp.route("/admin-users")
def admin_users():
    if not session.get("is_admin"):
        return redirect(url_for("auth.login"))
    users = admin_backend.get_approved_users()
    return render_template("admin_users.html", users=users)

@admin_bp.route("/api/pending-registrations")
def pending_regs():
    try:
        pending = admin_backend.get_pending_users()
        return jsonify({"pending": pending})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/create-credential", methods=["POST"])
def create_credential():
    if not session.get("is_admin"):
        return redirect(url_for("auth.login"))

    email = request.form.get("email")
    username = request.form.get("username")
    password = request.form.get("password")

    try:
        admin_backend.create_credential_entry(email, username, password)
        flash("User approved", "success")
    except Exception as e:
        flash("Error approving: " + str(e), "danger")

    return redirect(url_for("admin.admin_users"))

@admin_bp.route("/view-user/<username>")
def view_user(username):
    if not session.get("is_admin"):
        return redirect(url_for("auth.login"))

    ws = get_credentials_sheet()
    records = ws.get_all_records()
    user = next((u for u in records if u["Username"].lower() == username.lower()), None)

    return render_template("view_user.html", user=user)

@admin_bp.route("/update-user/<username>", methods=["POST"])
def update_user(username):
    if not session.get("is_admin"):
        return redirect(url_for("auth.login"))

    ws = get_credentials_sheet()
    records = ws.get_all_records()

    for i, row in enumerate(records, start=2):
        if row["Username"].lower() == username.lower():
            for key in row.keys():
                if key in request.form:
                    ws.update_cell(i, list(row.keys()).index(key) + 1, request.form[key])
            flash("Updated!", "success")
            return redirect(url_for("admin.view_user", username=username))

    flash("User not found.", "warning")
    return redirect(url_for("admin.admin_users"))
