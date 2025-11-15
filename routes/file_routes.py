from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, send_file
import io, zipfile

from backends.utils_backend import (
    list_packet_folders, list_files_in_folder,
    download_file_to_bytes, upload_media_to_drive,
    mute_video, get_unique_filename, get_or_create_folder,
    generate_secure_link, verify_secure_link, _drive_service
)

file_bp = Blueprint("file", __name__, url_prefix="/file")

# -----------------------------------------
# PAGE ROUTES
# -----------------------------------------
@file_bp.route("/files")
def files_page():
    if not session.get("username"):
        return redirect(url_for("auth.login"))
    return render_template("files.html", user=session.get("username"))


# -----------------------------------------
# API: PACKET FOLDERS
# -----------------------------------------
@file_bp.route("/api/packet-folders")
def api_folders():
    if not session.get("username"):
        return abort(401)
    return jsonify({"folders": list_packet_folders()})


# -----------------------------------------
# API: FILES IN FOLDER
# -----------------------------------------
@file_bp.route("/api/folder/<folder_id>/files")
def api_folder_files(folder_id):
    if not session.get("username"):
        return abort(401)
    return jsonify({"files": list_files_in_folder(folder_id)})


# -----------------------------------------
# DOWNLOAD SINGLE FILE (NORMAL)
# -----------------------------------------
@file_bp.route("/download/file/<file_id>")
def download_single_file(file_id):
    name, mime, fh = download_file_to_bytes(file_id)
    return send_file(fh, mimetype=mime, as_attachment=True, download_name=name)


# -----------------------------------------
# DOWNLOAD MULTIPLE FOLDERS AS ZIP
# -----------------------------------------
@file_bp.route("/download/folders-zip/<folder_ids>")
def download_folders_zip(folder_ids):
    if not session.get("username"):
        return abort(401)

    folder_ids = folder_ids.split(",")

    zip_buf = io.BytesIO()

    with zipfile.ZipFile(zip_buf, "w", zipfile.ZIP_DEFLATED) as zipf:

        for fid in folder_ids:
            try:
                meta = _drive_service.files().get(
                    fileId=fid, fields="name", supportsAllDrives=True
                ).execute()
                folder_name = meta.get("name", fid)
            except:
                folder_name = fid

            files = list_files_in_folder(fid)

            for f in files:
                name, mime, fh = download_file_to_bytes(f["id"])
                fh.seek(0)
                zipf.writestr(f"{folder_name}/{name}", fh.read())

    zip_buf.seek(0)

    zipname = (
        f"{folder_name}.zip" if len(folder_ids)==1 else "Selected_Folders.zip"
    )

    return send_file(
        zip_buf,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zipname
    )
