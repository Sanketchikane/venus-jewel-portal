# routes/file_routes.py
from flask import Blueprint, render_template, request, jsonify, send_file, abort, session, redirect, url_for
import io
from googleapiclient.http import MediaIoBaseUpload
from backends.utils_backend import (
    get_or_create_folder, get_unique_filename, mute_video,
    list_packet_folders, list_files_in_folder, download_file_to_bytes,
    upload_media_to_drive
)

file_bp = Blueprint("file", __name__)

@file_bp.route("/api/packet-folders")
def packet_folders():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"folders": list_packet_folders()})

@file_bp.route("/files")
def files_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))

@file_bp.route("/share")
def share_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("share.html", user=session.get("username"))

@file_bp.route("/upload", methods=["POST"])
def upload():
    try:
        packet_no = request.form.get("packetNo")
        folder_id = get_or_create_folder(packet_no)

        for key in request.files:
            sub = key.replace("file_", "")
            for file in request.files.getlist(key):

                ext = file.filename.split(".")[-1] if "." in file.filename else ""
                base = f"{sub}.{ext}" if ext else sub
                final = get_unique_filename(base, folder_id)

                if final.lower().endswith((".mp4", ".mov", ".mkv", ".avi", ".webm")):
                    stream = mute_video(file, final)
                    mime = "video/mp4"
                else:
                    stream = io.BytesIO(file.read())
                    mime = file.mimetype

                stream.seek(0)
                media = MediaIoBaseUpload(stream, mimetype=mime)
                upload_media_to_drive(final, folder_id, media)

        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)})

@file_bp.route("/download/file/<file_id>")
def download_file_route(file_id):
    if not session.get("username"):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)

@file_bp.route("/preview/file/<file_id>")
def preview_file(file_id):
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=False, download_name=name)

@file_bp.route("/venus-upload")
def venus_upload_dashboard():
    if not session.get("venus_user"):
        return redirect(url_for("auth.login"))
    return render_template("Venus_Upload.html", user=session.get("username"))
