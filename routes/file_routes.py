from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify, abort, send_file
import io, zipfile, os
from googleapiclient.http import MediaIoBaseUpload
from backends.utils_backend import (
    get_or_create_folder, get_unique_filename, mute_video,
    list_packet_folders, list_files_in_folder, download_file_to_bytes,
    upload_media_to_drive, generate_secure_link, verify_secure_link
)

file_bp = Blueprint("file", __name__)

# --------------------------
# MULTIPLE FOLDER ZIP EXPORT
# --------------------------
@file_bp.route("/download/folders-zip/<folder_ids>")
def download_multiple_folders(folder_ids):
    if not session.get("username"):
        return abort(401)

    folder_list = folder_ids.split(",")
    if not folder_list:
        return abort(400)

    zip_buffer = io.BytesIO()

    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zipf:

        for folder_id in folder_list:
            # get folder name
            try:
                # fetch folder metadata
                from backends.utils_backend import _drive_service
                meta = _drive_service.files().get(
                    fileId=folder_id,
                    fields="name",
                    supportsAllDrives=True
                ).execute()
                folder_name = meta.get("name", folder_id)
            except:
                folder_name = folder_id

            # get files inside folder
            files = list_files_in_folder(folder_id)

            # add each file inside folder subdirectory
            for f in files:
                try:
                    name, mime, fh = download_file_to_bytes(f["id"])
                    fh.seek(0)

                    zip_path = f"{folder_name}/{name}"
                    zipf.writestr(zip_path, fh.read())

                except Exception as e:
                    print("Error adding file:", e)
                    continue

    zip_buffer.seek(0)

    # ZIP name: one = PacketNo.zip, many = Selected_Folders.zip
    if len(folder_list) == 1:
        zipname = f"{folder_name}.zip"
    else:
        zipname = "Selected_Folders.zip"

    return send_file(
        zip_buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=zipname
    )
