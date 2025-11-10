@admin_bp.route("/create-credential", methods=["POST"])
def create_credential():
    try:
        email = request.form.get("email")
        username = request.form.get("username")
        password = request.form.get("password")

        if not all([email, username, password]):
            return "Missing data", 400

        from backends import admin_backend
        admin_backend.create_credential_entry(email, username, password)

        flash(f"✅ {username} approved successfully!", "success")
        return redirect(url_for("admin.admin_users"))
    except Exception as e:
        print("Approval error:", e)
        return "Internal Server Error", 500
