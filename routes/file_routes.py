# routes/file_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, send_file
import io
from googleapiclient.http import MediaIoBaseUpload
from backends.utils_backend import (
    get_or_create_folder, get_unique_filename, mute_video,
    list_packet_folders, list_files_in_folder, download_file_to_bytes
)

file_bp = Blueprint("file", __name__)

# API Route for Fetching Folders
@file_bp.route("/api/packet-folders")
def packet_folders():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        # Fetch folders from Google Drive
        folders = list_packet_folders()  # This function will call Google Drive API
        return jsonify({"folders": folders})  # Return folders in JSON format
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Files Page (Frontend)
@file_bp.route("/files")
def files_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))

# Share Page
@file_bp.route("/share")
def share_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("share.html", user=session.get("username"))

# Upload Route
@file_bp.route("/upload", methods=["POST"])
def upload():
    try:
        packet_no = request.form.get("packetNo", "").strip()
        if not packet_no:
            return jsonify({"success": False, "message": "Packet number is required."}), 400
        folder_id = get_or_create_folder(packet_no)
        for key in request.files:
            subpoint = key.replace("file_", "")
            for file in request.files.getlist(key):
                if file and file.filename:
                    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
                    base_filename = f"{subpoint}.{ext}" if ext else subpoint
                    final_filename = get_unique_filename(base_filename, folder_id)
                    if final_filename.lower().endswith((".mp4", ".mov", ".avi", ".mkv", ".webm")):
                        file_stream = mute_video(file, final_filename)
                        mimetype = "video/mp4"
                    else:
                        file_stream = io.BytesIO(file.read())
                        mimetype = file.mimetype or "application/octet-stream"
                    file_stream.seek(0)
                    media = MediaIoBaseUpload(file_stream, mimetype=mimetype)
                    # Upload media to Google Drive
                    from backends.utils_backend import upload_media_to_drive
                    upload_media_to_drive(final_filename, folder_id, media)
        return jsonify({"success": True, "message": "✅ All files uploaded and muted successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Upload failed: {e}"}), 500

# Download File Route
@file_bp.route("/download/file/<file_id>")
def download_file_route(file_id):
    if not session.get("username"):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)

# Preview File Route
@file_bp.route("/preview/file/<file_id>")
def preview_file(file_id):
    t = request.args.get("t")
    s = request.args.get("s")
    if t and s:
        from backends.utils_backend import verify_secure_link
        if not verify_secure_link(file_id, t, s):
            return abort(403)
    elif not session.get("username"):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=False, download_name=name)

# Venus Upload Dashboard Route
@file_bp.route("/venus-upload")
def venus_upload_dashboard():
    if not session.get("venus_user"):
        return redirect(url_for("auth.login"))
    return render_template("Venus_Upload.html", user=session.get("username", ""))
