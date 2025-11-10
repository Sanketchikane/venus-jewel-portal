# routes/admin_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from backends.register_backend import get_pending_requests
from backends.admin_backend import create_credentials_from_request
from backends.forgot_password_backend import reset_password_for_username
from backends.utils_backend import read_credentials_all_rows
import config

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

@admin_bp.route("/admin-dashboard")
def admin_dashboard():
    if not session.get("admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("auth.login"))
    return render_template("admin_dashboard.html", user=session.get("username"))

@admin_bp.route("/admin/users")
def admin_users():
    if not session.get("admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("auth.login"))

    try:
        users = read_credentials_all_rows()
        return render_template("admin_users.html", users=users)
    except Exception as e:
        flash(f"Error loading users: {e}", "danger")
        return render_template("admin_users.html", users=[])
    
@admin_bp.route("/admin/create-credential", methods=["POST"])
def admin_create_credential():
    if not session.get("admin"):
        return redirect(url_for("auth.login"))

    reg_email = request.form.get("email")
    new_username = request.form.get("username")
    new_password = request.form.get("password")
    if not (reg_email and new_username and new_password):
        flash("Missing required fields.", "danger")
        return redirect(url_for("admin.admin_users"))

    ok = create_credentials_from_request(reg_email, new_username, new_password)
    flash("✅ Credentials created & emailed to user." if ok else "❌ Failed to create credentials.", "info")
    return redirect(url_for("admin.admin_users"))

@admin_bp.route("/admin/reset-password", methods=["POST"])
def admin_reset_password():
    if not session.get("admin"):
        return redirect(url_for("auth.login"))
    target = request.form.get("target")
    new_password = request.form.get("new_password")
    if not (target and new_password):
        flash("Missing target or password.", "danger")
        return redirect(url_for("admin.admin_users"))
    ok = reset_password_for_username(target, new_password)
    flash("✅ Password reset & emailed to user." if ok else "❌ User not found.", "info")
    return redirect(url_for("admin.admin_users"))

# route to open drive folder
@admin_bp.route("/admin/venus-files")
def admin_files():
    if not session.get("admin"):
        flash("Admin access only.", "danger")
        return redirect(url_for("auth.login"))
    return redirect("https://drive.google.com/drive/folders/" + config.DRIVE_FOLDER_ID)
