# file_routes.py
from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, send_file
import io
import zipfile
import time
import hmac
import hashlib
from googleapiclient.http import MediaIoBaseUpload

from backends.utils_backend import (
    get_or_create_folder,
    get_unique_filename,
    mute_video,
    list_packet_folders,
    list_files_in_folder,
    download_file_to_bytes,
    upload_media_to_drive,
    generate_secure_link,
    verify_secure_link,
    _drive_service
)

import config  # ensure SECRET_SHARE_KEY exists (bytes or str)

file_bp = Blueprint("file", __name__)

# -----------------------
# PAGE ROUTES
# -----------------------
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

@file_bp.route("/venus-upload")
def venus_upload_dashboard():
    # Upload page kept as-is (your working page)
    if not session.get("venus_user"):
        return redirect(url_for("auth.login"))
    return render_template("Venus_Upload.html", user=session.get("username", ""))


# -----------------------
# API: Listing / Files
# -----------------------
@file_bp.route("/api/packet-folders")
def packet_folders_api():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        folders = list_packet_folders()
        return jsonify({"folders": folders})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@file_bp.route("/api/folder/<folder_id>/files")
def folder_files_api(folder_id):
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401
    try:
        files = list_files_in_folder(folder_id)
        return jsonify({"files": files})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# -----------------------
# UPLOAD (working logic preserved)
# POST /upload
# form:
#  - packetNo
#  - file_<subpoint> (can be multiple)
# -----------------------
@file_bp.route("/upload", methods=["POST"])
def upload():
    try:
        packet_no = request.form.get("packetNo", "").strip()
        if not packet_no:
            return jsonify({"success": False, "message": "Packet number is required."}), 400
        folder_id = get_or_create_folder(packet_no)
        
        for key in request.files:
            # keys are expected as file_<subpoint>
            subpoint = key.replace("file_", "")
            for file in request.files.getlist(key):
                if file and file.filename:
                    # create unique filename using subpoint + extension
                    ext = file.filename.rsplit(".", 1)[-1] if "." in file.filename else ""
                    base_filename = f"{subpoint}.{ext}" if ext else subpoint
                    final_filename = get_unique_filename(base_filename, folder_id)
                    
                    # if video -> mute via mute_video helper (should return file-like)
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


# -----------------------
# DOWNLOAD single file
# -----------------------
@file_bp.route("/download/file/<file_id>")
def download_file_route(file_id):
    if not session.get("username"):
        return abort(401)
    try:
        name, mime, fh = download_file_to_bytes(file_id)
        fh.seek(0)
        return send_file(
            fh, mimetype=mime,
            as_attachment=True,
            download_name=name
        )
    except Exception as e:
        return abort(404)


# -----------------------
# PREVIEW single file (supports secure token or session)
# GET /preview/file/<file_id>?t=<ts>&s=<sig>  OR session
# -----------------------
@file_bp.route("/preview/file/<file_id>")
def preview_file(file_id):
    t = request.args.get("t")
    s = request.args.get("s")

    if t and s:
        # token preview allowed without session if verify passes
        if not verify_secure_link(file_id, t, s):
            return abort(403)
    elif not session.get("username"):
        return abort(401)

    try:
        name, mime, fh = download_file_to_bytes(file_id)
        fh.seek(0)
        return send_file(
            fh, mimetype=mime,
            as_attachment=False,
            download_name=name
        )
    except Exception:
        return abort(404)


# -----------------------
# SHARE single file (page)
# -----------------------
@file_bp.route("/share.html")
def share_file_page():
    file_id = request.args.get("id")
    if not file_id:
        return "File ID not provided", 400
    return render_template("share.html", file_id=file_id)


@file_bp.route("/api/share-link")
def api_share_link():
    file_id = request.args.get("id")
    if not file_id:
        return jsonify({"error": "missing id"}), 400
    link = generate_secure_link(file_id)
    full_url = request.url_root.rstrip("/") + link
    return jsonify({"link": full_url})


# -----------------------
# DOWNLOAD single folder as ZIP
# /download/folder/<folder_id>
# -----------------------
@file_bp.route("/download/folder/<folder_id>")
def download_folder_zip(folder_id):
    if not session.get("username"):
        return abort(401)

    try:
        files = list_files_in_folder(folder_id)
        if not files:
            return abort(404)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:
            for f in files:
                try:
                    name, mime, fh = download_file_to_bytes(f["id"])
                    fh.seek(0)
                    zipf.writestr(name, fh.read())
                except Exception as e:
                    # skip problematic files but continue
                    continue

        zip_buffer.seek(0)
        return send_file(
            zip_buffer,
            mimetype="application/zip",
            as_attachment=True,
            download_name=f"{folder_id}.zip"
        )
    except Exception as e:
        return abort(500)


# -----------------------
# DOWNLOAD multiple folders as a single ZIP (secure preview available)
# /download/folders-zip/<folder_ids>  (used by front-end direct link)
# --- Also we provide /preview/folders-zip?ids=<ids>&t=<ts>&s=<sig> for secure shared links
# -----------------------
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
            # Get folder name
            try:
                meta = _drive_service.files().get(
                    fileId=fid,
                    fields="name",
                    supportsAllDrives=True
                ).execute()
                folder_name = meta.get("name", fid)
            except Exception:
                folder_name = fid

            folder_names.append(folder_name)

            # Add files inside folder
            for f in list_files_in_folder(fid):
                try:
                    name, mime, fh = download_file_to_bytes(f["id"])
                    fh.seek(0)
                    zipf.writestr(f"{folder_name}/{name}", fh.read())
                except Exception:
                    continue

    zip_buffer.seek(0)
    if len(folder_names) == 1:
        zipname = f"{folder_names[0]}.zip"
    else:
        zipname = f"Selected_{len(folder_names)}_Packets.zip"

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zipname
    )


# -----------------------
# MOVE MULTIPLE FOLDERS TO TRASH (POST)
# /api/delete-folders  body: {"ids": ["id1","id2", ...]}
# -----------------------
@file_bp.route("/api/delete-folders", methods=["POST"])
def api_delete_folders():
    if not session.get("username"):
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json(silent=True) or {}
    ids = data.get("ids") or []
    if isinstance(ids, str):
        ids = [i for i in ids.split(",") if i]

    if not ids:
        return jsonify({"error": "Missing folder ids"}), 400

    results = {"deleted": [], "failed": []}
    for fid in ids:
        try:
            _drive_service.files().update(
                fileId=fid,
                body={"trashed": True},
                supportsAllDrives=True
            ).execute()
            results["deleted"].append(fid)
        except Exception as e:
            results["failed"].append({"id": fid, "error": str(e)})

    return jsonify(results)


# -----------------------
# API: Create secure folder share link (preview folders zip)
# /api/share-folder?id=<folderId>&expire=<seconds>
# -----------------------
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
    secret_key = config.SECRET_SHARE_KEY if isinstance(config.SECRET_SHARE_KEY, (bytes, bytearray)) else config.SECRET_SHARE_KEY.encode()
    s = hmac.new(secret_key, data.encode(), hashlib.sha256).hexdigest()

    preview_path = f"/preview/folders-zip?ids={folder_id}&t={t}&s={s}"
    full_url = request.url_root.rstrip("/") + preview_path
    return jsonify({"link": full_url})


# -----------------------
# PREVIEW FOLDERS ZIP (verify token and stream ZIP)
# /preview/folders-zip?ids=<id1,id2>&t=<ts>&s=<sig>
# -----------------------
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
            except Exception:
                folder_name = fid
            folder_names.append(folder_name)
            for f in list_files_in_folder(fid):
                try:
                    name, mime, fh = download_file_to_bytes(f["id"])
                    fh.seek(0)
                    zipf.writestr(f"{folder_name}/{name}", fh.read())
                except Exception:
                    continue

    zip_buffer.seek(0)
    if len(folder_names) == 1:
        zipname = f"{folder_names[0]}.zip"
    else:
        zipname = f"Shared_{len(folder_names)}_Packets.zip"

    return send_file(zip_buffer, mimetype="application/zip", as_attachment=True, download_name=zipname)
