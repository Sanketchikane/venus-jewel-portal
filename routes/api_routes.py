# routes/api_routes.py
from flask import Blueprint, jsonify, request
from backends.register_backend import get_pending_requests
from backends.utils_backend import list_packet_folders, list_files_in_folder, generate_secure_link
api_bp = Blueprint("api", __name__)

@api_bp.route("/api/pending-registrations")
def api_pending_registrations():
    try:
        pending = get_pending_requests()
        return jsonify({"pending": pending})
    except Exception:
        return jsonify({"pending": []})

@api_bp.route("/api/packet-folders")
def api_packet_folders():
    sort = request.args.get("sort", "newest")
    order = "modifiedTime desc" if sort == "newest" else "name"
    try:
        folders = list_packet_folders(order=order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"folders": folders})

@api_bp.route("/api/folder/<folder_id>/files")
def api_folder_files(folder_id):
    sort = request.args.get("sort", "newest")
    order = "modifiedTime desc" if sort == "newest" else "name"
    try:
        files = list_files_in_folder(folder_id, order=order)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    return jsonify({"files": files})

@api_bp.route("/api/share-link")
def api_share_link():
    file_id = request.args.get("id")
    if not file_id:
        return jsonify({"error": "missing id"}), 400
    link = generate_secure_link(file_id)
    full_url = request.url_root.rstrip("/") + link
    return jsonify({"link": full_url})
