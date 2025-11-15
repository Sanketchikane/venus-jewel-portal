from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, send_file
import io
import zipfile
import time
import hmac
import hashlib
from googleapiclient.http import MediaIoBaseUpload
from backends.utils_backend import (
    get_or_create_folder, get_unique_filename, mute_video,
    list_packet_folders, list_files_in_folder, download_file_to_bytes,
    upload_media_to_drive, generate_secure_link, verify_secure_link, _drive_service
)
import config  # ensure SECRET_SHARE_KEY exists in config (bytes or str)

file_bp = Blueprint("file", __name__)

# ---------------------------
# PAGE ROUTES
# ---------------------------
@file_bp.route("/files")
def files_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))

@file_bp.route("/admin-files")
def admin_files():
    if not session.get("is_admin"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))


# ---------------------------
# API ROUTES
# ---------------------------
@file_bp.route("/api/packet-folders")
def packet_folders_api():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"folders": list_packet_folders()})


@file_bp.route("/api/folder/<folder_id>/files")
def folder_files_api(folder_id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    return jsonify({"files": list_files_in_folder(folder_id)})


# ---------------------------
# DOWNLOAD SINGLE FILE
# ---------------------------
@file_bp.route("/download/file/<file_id>")
def download_file_route(file_id):
    if not session.get("username"):
        return abort(401)
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)


# ---------------------------
# PREVIEW FILE
# ---------------------------
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


# ---------------------------
# SHARE PAGE (single file)
# ---------------------------
@file_bp.route("/share.html")
def share_file_page():
    file_id = request.args.get("id")
    return render_template("share.html", file_id=file_id)


@file_bp.route("/api/share-link")
def api_share_link():
    file_id = request.args.get("id")
    link = generate_secure_link(file_id)
    full_url = request.url_root.rstrip("/") + link
    return jsonify({"link": full_url})


# ---------------------------
# DOWNLOAD SINGLE FOLDER ZIP
# ---------------------------
@file_bp.route("/download/folder/<folder_id>")
def download_single_folder(folder_id):
    if not session.get("username"):
        return abort(401)

    files = list_files_in_folder(folder_id)
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            name, mime, fh = download_file_to_bytes(f["id"])
            fh.seek(0)
            zipf.writestr(name, fh.read())
    zip_buffer.seek(0)
    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name="Packet_Folder.zip")


# ---------------------------
# DOWNLOAD MULTIPLE FOLDERS ZIP
# ---------------------------
@file_bp.route("/download/folders-zip/<folder_ids>")
def download_multiple_folders(folder_ids):
    if not session.get("username"):
        return abort(401)

    ids = [i for i in folder_ids.split(",") if i]
    if not ids:
        return abort(400)

    zip_buffer = io.BytesIO()
    folder_names = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fid in ids:
            try:
                meta = _drive_service.files().get(fileId=fid, fields="name", supportsAllDrives=True).execute()
                folder_name = meta.get("name", fid)
            except:
                folder_name = fid
            folder_names.append(folder_name)
            for f in list_files_in_folder(fid):
                name, mime, fh = download_file_to_bytes(f["id"])
                fh.seek(0)
                zipf.writestr(f"{folder_name}/{name}", fh.read())

    zip_buffer.seek(0)
    if len(folder_names) == 1:
        zipname = f"{folder_names[0]}.zip"
    else:
        zipname = f"Selected_{len(folder_names)}_Packets.zip"

    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=zipname)


# ---------------------------
# NEW: Single-folder share API (Option 1)
# Returns a secure temporary link that points to /preview/folders-zip
# ---------------------------
@file_bp.route("/api/share-folder")
def api_share_folder():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    folder_id = request.args.get("id")
    if not folder_id:
        return jsonify({"error": "missing id param"}), 400

    try:
        expire = int(request.args.get("expire", 3600))
    except:
        expire = 3600

    t = int(time.time()) + expire
    data = f"{folder_id}:{t}"
    # SECRET key from config
    secret_key = config.SECRET_SHARE_KEY if isinstance(config.SECRET_SHARE_KEY, (bytes, bytearray)) else config.SECRET_SHARE_KEY.encode()
    s = hmac.new(secret_key, data.encode(), hashlib.sha256).hexdigest()

    preview_path = f"/preview/folders-zip?ids={folder_id}&t={t}&s={s}"
    full_url = request.url_root.rstrip("/") + preview_path
    return jsonify({"link": full_url})


# ---------------------------
# PREVIEW/FOLDER ZIP (verify & stream)
# Endpoint: /preview/folders-zip?ids=<id1,id2>&t=<ts>&s=<sig>
# ---------------------------
@file_bp.route("/preview/folders-zip")
def preview_folders_zip():
    ids = request.args.get("ids", "")
    t = request.args.get("t")
    s = request.args.get("s")
    if not ids or not t or not s:
        return abort(400)

    try:
        t_int = int(t)
    except:
        return abort(400)

    if int(time.time()) > t_int:
        return abort(403)

    data = f"{ids}:{t}"
    secret_key = config.SECRET_SHARE_KEY if isinstance(config.SECRET_SHARE_KEY, (bytes, bytearray)) else config.SECRET_SHARE_KEY.encode()
    expected = hmac.new(secret_key, data.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(expected, s):
        return abort(403)

    id_list = [i for i in ids.split(",") if i]
    if not id_list:
        return abort(400)

    zip_buffer = io.BytesIO()
    folder_names = []

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
        for fid in id_list:
            try:
                meta = _drive_service.files().get(fileId=fid, fields="name", supportsAllDrives=True).execute()
                folder_name = meta.get("name", fid)
            except:
                folder_name = fid
            folder_names.append(folder_name)
            for f in list_files_in_folder(fid):
                try:
                    name, mime, fh = download_file_to_bytes(f["id"])
                    fh.seek(0)
                    zipf.writestr(f"{folder_name}/{name}", fh.read())
                except Exception as e:
                    print("preview_folders_zip: skip file", e)
                    continue

    zip_buffer.seek(0)
    if len(folder_names) == 1:
        zipname = f"{folder_names[0]}.zip"
    else:
        zipname = f"Shared_{len(folder_names)}_Packets.zip"

    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=zipname)
