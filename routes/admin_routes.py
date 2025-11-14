from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from backends import admin_backend
from backends.utils_backend import get_credentials_sheet, reset_password_for_username, get_registration_sheet
import traceback

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

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

# Pending registrations (AJAX)
@admin_bp.route("/api/pending-registrations")
def pending_registrations():
    try:
        pending = admin_backend.get_pending_users()
        formatted = []
        for r in pending:
            formatted.append({
                "Full Name": r.get("Full Name", ""),
                "Email": r.get("Email Address", "") or r.get("Email", ""),
                "Contact": r.get("Contact Number", "") or r.get("Contact", ""),
                "Organization": r.get("Organization", ""),
                "Status": r.get("Status", "Pending")
            })
        return jsonify({"pending": formatted})
    except Exception as e:
        print("Error fetching pending registrations:", e)
        traceback.print_exc()
        return jsonify({"pending": []})

# Pending forgot-password requests (AJAX)
@admin_bp.route("/api/pending-forgot-passwords")
def pending_forgot_requests():
    try:
        ws = get_registration_sheet("Forgot_Password_Requests")
        rows = ws.get_all_records()
        pending = [r for r in rows if str(r.get("Status", "")).strip().lower().startswith("pending")]
        return jsonify({"pending": pending})
    except Exception as e:
        print("Error fetching forgot-password requests:", e)
        traceback.print_exc()
        return jsonify({"pending": []})

# Approve a registration (create credentials + update registration row)
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
        flash(f"✅ User '{username}' added and approved successfully.", "success")
        return redirect(url_for("admin.admin_users"))
    except Exception as e:
        print("Approval error:", e)
        traceback.print_exc()
        flash("❌ Internal Server Error during approval", "danger")
        return redirect(url_for("admin.admin_users"))

# View user profile (Credentials)
@admin_bp.route("/view-user/<username>")
def view_user(username):
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))

        ws = get_credentials_sheet()
        records = ws.get_all_records()
        user = next(
            (u for u in records if str(u.get("Username", "")).strip().lower() == str(username).strip().lower()),
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

# Update user profile (Credentials)
@admin_bp.route("/update-user/<username>", methods=["POST"])
def update_user(username):
    try:
        if not session.get("is_admin"):
            flash("Unauthorized access", "danger")
            return redirect(url_for("auth.login"))
        ws = get_credentials_sheet()
        records = ws.get_all_records()
        for i, row in enumerate(records, start=2):
            if str(row.get("Username", "")).strip().lower() == str(username).strip().lower():
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

# Admin action: reset password for a username (from forgot requests)
@admin_bp.route("/reset-forgot-password", methods=["POST"])
def admin_reset_forgot_password():
    try:
        if not session.get("is_admin"):
            return redirect(url_for("auth.login"))
        username = request.form.get("username", "").strip()
        new_password = request.form.get("new_password", "").strip()
        request_row_idx = request.form.get("request_row", None)  # optional: position in forgot sheet
        if not username or not new_password:
            flash("⚠️ Missing username or new password.", "warning")
            return redirect(url_for("admin.admin_users"))
        ok = reset_password_for_username(username, new_password)
        if ok:
            # optionally mark the forgot request as processed if request_row provided
            if request_row_idx:
                try:
                    ws = get_registration_sheet("Forgot_Password_Requests")
                    ws.update_cell(int(request_row_idx), 6, "Processed")
                except Exception:
                    pass
            flash("✅ Password reset successfully.", "success")
        else:
            flash("❌ Username not found in Credentials.", "danger")
        return redirect(url_for("admin.admin_users"))
    except Exception as e:
        print("Error resetting password (admin):", e)
        traceback.print_exc()
        flash("⚠️ Could not reset password. Try later.", "danger")
        return redirect(url_for("admin.admin_users"))
