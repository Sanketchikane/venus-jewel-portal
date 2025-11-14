# routes/file_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, send_file
import io
from googleapiclient.http import MediaIoBaseUpload
from backends.utils_backend import (
    get_or_create_folder, get_unique_filename, mute_video,
    list_packet_folders, list_files_in_folder, download_file_to_bytes,
    upload_media_to_drive, generate_secure_link, verify_secure_link
)

file_bp = Blueprint("file", __name__)

# Admin-facing files page alias expected by templates
@file_bp.route("/admin-files")
def admin_files():
    if not session.get("is_admin"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))

# Files page for regular users
@file_bp.route("/files")
def files_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))

# API: packet folders
@file_bp.route("/api/packet-folders")
def packet_folders_api():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        folders = list_packet_folders()
        return jsonify({"folders": folders})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# API: files in folder
@file_bp.route("/api/folder/<folder_id>/files")
def folder_files_api(folder_id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        files = list_files_in_folder(folder_id)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Upload handler
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
                        media = MediaIoBaseUpload(file_stream, mimetype=mimetype)
                    else:
                        file_stream = io.BytesIO(file.read())
                        mimetype = file.mimetype or "application/octet-stream"
                        file_stream.seek(0)
                        media = MediaIoBaseUpload(file_stream, mimetype=mimetype)
                    upload_media_to_drive(final_filename, folder_id, media)
        return jsonify({"success": True, "message": "✅ All files uploaded and stored successfully."})
    except Exception as e:
        return jsonify({"success": False, "message": f"Upload failed: {e}"}), 500

# Download
@file_bp.route("/download/file/<file_id>")
def download_file_route(file_id):
    if not session.get("username"):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)

# Preview (secure link support)
@file_bp.route("/preview/file/<file_id>")
def preview_file(file_id):
    t = request.args.get("t")
    s = request.args.get("s")
    if t and s:
        if not verify_secure_link(file_id, t, s):
            return abort(403)
    elif not session.get("username"):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=False, download_name=name)

# Share page
@file_bp.route("/share.html")
def share_file_page():
    file_id = request.args.get("id")
    if not file_id:
        return "File ID not provided", 400
    return render_template("share.html", file_id=file_id)

# Share link API
@file_bp.route("/api/share-link")
def api_share_link():
    file_id = request.args.get("id")
    if not file_id:
        return jsonify({"error": "missing id"}), 400
    link = generate_secure_link(file_id)
    full_url = request.url_root.rstrip("/") + link
    return jsonify({"link": full_url})

# Venus upload dashboard
@file_bp.route("/venus-upload")
def venus_upload_dashboard():
    if not session.get("venus_user"):
        return redirect(url_for("auth.login"))
    return render_template("Venus_Upload.html", user=session.get("username", ""))
