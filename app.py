"""
app.py - Face Authentication Demo
Môn: Introduction to Information Security
Nhóm 10 - Lớp 01
"""

import os
import sys
import io

# Force UTF-8 encoding for stdout/stderr to prevent crash when deepface prints emojis on Windows
if sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
if sys.stderr.encoding.lower() != 'utf-8':
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import time
import pickle
import uuid

from flask import Flask, render_template, request, jsonify
from flask_cors import CORS

import face_utils

# ─── Khởi tạo Flask ───────────────────────────────────────────────────────────
app = Flask(__name__)
app.secret_key = "face_auth_demo_2024_uis_nhom10"
CORS(app)

# ─── Lưu trữ dữ liệu (in-memory + file) ──────────────────────────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), "data", "users")
os.makedirs(DATA_DIR, exist_ok=True)

# users: { username -> { embedding, registered_at, username } }
users: dict = {}

# liveness_sessions: { session_id -> BlinkDetector }
liveness_sessions: dict = {}


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _load_users():
    """Tải dữ liệu người dùng từ file pickle khi khởi động."""
    global users
    if not os.path.exists(DATA_DIR):
        return
    for fname in os.listdir(DATA_DIR):
        if fname.endswith(".pkl"):
            username = fname[:-4]
            try:
                with open(os.path.join(DATA_DIR, fname), "rb") as f:
                    users[username] = pickle.load(f)
            except Exception as e:
                print(f"[load_users] Skipped {fname}: {e}")


def _save_user(username: str, data: dict):
    """Lưu dữ liệu người dùng ra file."""
    path = os.path.join(DATA_DIR, f"{username}.pkl")
    with open(path, "wb") as f:
        pickle.dump(data, f)


def _delete_user(username: str):
    """Xóa người dùng khỏi bộ nhớ và file."""
    users.pop(username, None)
    path = os.path.join(DATA_DIR, f"{username}.pkl")
    if os.path.exists(path):
        os.remove(path)


_load_users()


# ══════════════════════════════════════════════════════════════════════════════
#  TRANG HTML
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/")
def index():
    return render_template("index.html", users=list(users.keys()))


@app.route("/register")
def register_page():
    return render_template("register.html")


@app.route("/login/vulnerable")
def login_vulnerable_page():
    return render_template("login_vulnerable.html", users=list(users.keys()))


@app.route("/login/secure")
def login_secure_page():
    return render_template("login_secure.html", users=list(users.keys()))


# ══════════════════════════════════════════════════════════════════════════════
#  API: ĐĂNG KÝ
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/register", methods=["POST"])
def api_register():
    data     = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    img_b64  = data.get("image")

    if not username:
        return jsonify({"success": False, "message": "Tên người dùng không được để trống."})
    if username in users:
        return jsonify({"success": False, "message": f'Người dùng "{username}" đã tồn tại.'})
    if not img_b64:
        return jsonify({"success": False, "message": "Không nhận được hình ảnh."})

    img = face_utils.decode_image(img_b64)
    if img is None:
        return jsonify({"success": False, "message": "Không thể giải mã hình ảnh."})

    embedding, error = face_utils.extract_embedding(img)
    if embedding is None:
        return jsonify({"success": False, "message": error})

    user_data = {
        "username"     : username,
        "embedding"    : embedding,
        "registered_at": time.time(),
    }
    users[username] = user_data
    _save_user(username, user_data)

    return jsonify({"success": True, "message": f'✅ Đăng ký thành công cho "{username}"!'})


@app.route("/api/users/delete", methods=["POST"])
def api_delete_user():
    data     = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    if username not in users:
        return jsonify({"success": False, "message": "Người dùng không tồn tại."})
    _delete_user(username)
    return jsonify({"success": True, "message": f'Đã xóa người dùng "{username}".'})


@app.route("/api/users", methods=["GET"])
def api_users():
    return jsonify({"users": list(users.keys())})


# ══════════════════════════════════════════════════════════════════════════════
#  API: ĐĂNG NHẬP - HỆ THỐNG CÓ LỖ HỔNG (không có liveness)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/login/vulnerable", methods=["POST"])
def api_login_vulnerable():
    """
    VULNERABLE ENDPOINT: Chỉ so sánh embedding, KHÔNG kiểm tra liveness.
    Kẻ tấn công có thể dùng ảnh in để vượt qua.
    """
    data     = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    img_b64  = data.get("image")

    if not username or username not in users:
        return jsonify({"success": False, "message": f'Người dùng "{username}" không tồn tại.'})

    img = face_utils.decode_image(img_b64)
    if img is None:
        return jsonify({"success": False, "message": "Không thể giải mã hình ảnh."})

    # Bước 1: Phát hiện khuôn mặt + trích xuất embedding
    embedding, error = face_utils.extract_embedding(img)
    if embedding is None:
        return jsonify({"success": False, "message": error})

    # Bước 2: So sánh embedding
    stored_emb         = users[username]["embedding"]
    similarity, is_match = face_utils.compare_embeddings(stored_emb, embedding)

    # ⚠️  KHÔNG CÓ LIVENESS CHECK ─ đây là lỗ hổng
    steps = [
        {"step": 1, "name": "Thu nhận hình ảnh",           "status": "ok", "detail": "Frame nhận được từ camera"},
        {"step": 2, "name": "Phát hiện khuôn mặt",         "status": "ok", "detail": "Khuôn mặt được phát hiện thành công"},
        {"step": 3, "name": "Trích xuất Face Embedding",   "status": "ok", "detail": "CNN đã tạo vector 128 chiều"},
        {"step": 4, "name": "Kiểm tra Liveness",           "status": "skip", "detail": "⚠️  BƯỚC NÀY BỊ BỎ QUA — Đây là lỗ hổng!"},
        {"step": 5, "name": "So sánh Embedding",           "status": "ok" if is_match else "fail",
         "detail": f"Cosine similarity = {similarity:.4f} | Threshold = {1 - face_utils.FACE_MATCH_THRESHOLD:.2f}"},
    ]

    return jsonify({
        "success"         : is_match,
        "similarity"      : round(similarity, 4),
        "distance"        : round(1.0 - similarity, 4),
        "threshold"       : 1 - face_utils.FACE_MATCH_THRESHOLD,
        "liveness_checked": False,
        "steps"           : steps,
        "message"         : (
            f"🔓 AUTHENTICATION SUCCESSFUL! Kẻ tấn công đã đăng nhập thành công. Similarity = {similarity:.4f}"
            if is_match else
            f"❌ Xác thực thất bại. Similarity = {similarity:.4f} (quá thấp)"
        ),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  API: LIVENESS DETECTION SESSION
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/liveness/start", methods=["POST"])
def api_liveness_start():
    """Tạo session liveness detection mới."""
    session_id = str(uuid.uuid4())
    liveness_sessions[session_id] = face_utils.BlinkDetector()
    return jsonify({"session_id": session_id, "message": "Session liveness đã bắt đầu. Hãy chớp mắt!"})


@app.route("/api/liveness/frame", methods=["POST"])
def api_liveness_frame():
    """
    Nhận một frame từ webcam, phân tích EAR và cập nhật trạng thái blink.
    """
    data       = request.get_json(force=True)
    session_id = data.get("session_id")
    img_b64    = data.get("image")

    if session_id not in liveness_sessions:
        return jsonify({"success": False, "message": "Session không hợp lệ hoặc đã hết hạn."})

    img = face_utils.decode_image(img_b64)
    if img is None:
        return jsonify({"face_detected": False, "ear": None})

    # Phân tích frame: lấy EAR + ảnh annotated
    info = face_utils.get_face_info_from_frame(img)

    # Cập nhật blink detector
    detector       = liveness_sessions[session_id]
    blink_now      = detector.update(info["ear"])
    detector_state = detector.to_dict()

    return jsonify({
        "face_detected" : info["face_detected"],
        "ear"           : info["ear"],
        "eye_status"    : info["eye_status"],
        "annotated_b64" : info["annotated_b64"],
        "blink_now"     : blink_now,
        **detector_state,
    })


# ══════════════════════════════════════════════════════════════════════════════
#  API: ĐĂNG NHẬP - HỆ THỐNG BẢO MẬT (có liveness detection)
# ══════════════════════════════════════════════════════════════════════════════

@app.route("/api/login/secure", methods=["POST"])
def api_login_secure():
    """
    SECURE ENDPOINT: Kiểm tra liveness trước, rồi mới so sánh embedding.
    """
    data       = request.get_json(force=True)
    username   = (data.get("username") or "").strip()
    img_b64    = data.get("image")
    session_id = data.get("session_id")

    if not username or username not in users:
        return jsonify({"success": False, "message": f'Người dùng "{username}" không tồn tại.'})

    # ── Bước 1: Kiểm tra liveness session ─────────────────────────────────────
    if session_id not in liveness_sessions:
        return jsonify({
            "success"        : False,
            "liveness_failed": True,
            "message"        : "🚫 Không có session liveness hợp lệ. Hãy bắt đầu lại.",
        })

    detector = liveness_sessions[session_id]
    state    = detector.to_dict()

    if not state["liveness_pass"]:
        # Dọn session
        del liveness_sessions[session_id]
        steps = [
            {"step": 1, "name": "Thu nhận hình ảnh",         "status": "ok"},
            {"step": 2, "name": "Phát hiện khuôn mặt",       "status": "ok"},
            {"step": 3, "name": "Trích xuất Face Embedding",  "status": "ok"},
            {"step": 4, "name": "Kiểm tra Liveness (EAR)",   "status": "fail",
             "detail": f"Blink count = {state['blink_count']} (cần ≥ 1). Phát hiện ảnh giả mạo!"},
            {"step": 5, "name": "So sánh Embedding",         "status": "skip",
             "detail": "Bị chặn do liveness thất bại"},
        ]
        return jsonify({
            "success"        : False,
            "liveness_failed": True,
            "blink_count"    : state["blink_count"],
            "steps"          : steps,
            "message"        : f"🛡️ LIVENESS CHECK FAILED! Blink count = {state['blink_count']}. Hệ thống phát hiện đây có thể là ảnh giả mạo và TỪ CHỐI xác thực.",
        })

    # ── Bước 2: Liveness đã qua → so sánh khuôn mặt ─────────────────────────
    img = face_utils.decode_image(img_b64)
    if img is None:
        del liveness_sessions[session_id]
        return jsonify({"success": False, "message": "Không thể giải mã hình ảnh cuối."})

    embedding, error = face_utils.extract_embedding(img)
    if embedding is None:
        del liveness_sessions[session_id]
        return jsonify({"success": False, "message": error})

    stored_emb           = users[username]["embedding"]
    similarity, is_match = face_utils.compare_embeddings(stored_emb, embedding)

    # Dọn session
    del liveness_sessions[session_id]

    steps = [
        {"step": 1, "name": "Thu nhận hình ảnh",         "status": "ok", "detail": "Frame webcam nhận được"},
        {"step": 2, "name": "Phát hiện khuôn mặt",       "status": "ok", "detail": "Khuôn mặt được xác định"},
        {"step": 3, "name": "Trích xuất Face Embedding",  "status": "ok", "detail": "CNN tạo vector 128 chiều"},
        {"step": 4, "name": "Kiểm tra Liveness (EAR)",   "status": "ok",
         "detail": f"✅ Phát hiện {state['blink_count']} lần chớp mắt — Người thật xác nhận!"},
        {"step": 5, "name": "So sánh Embedding",
         "status": "ok" if is_match else "fail",
         "detail": f"Similarity = {similarity:.4f} | Threshold = {1 - face_utils.FACE_MATCH_THRESHOLD:.2f}"},
    ]

    return jsonify({
        "success"         : is_match,
        "similarity"      : round(similarity, 4),
        "liveness_passed" : True,
        "blink_count"     : state["blink_count"],
        "steps"           : steps,
        "message"         : (
            f"✅ Xác thực thành công! Liveness OK ({state['blink_count']} blink), Similarity = {similarity:.4f}"
            if is_match else
            f"❌ Liveness OK nhưng khuôn mặt không khớp. Similarity = {similarity:.4f}"
        ),
    })


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    print("=" * 60)
    print("  Face Authentication Demo  - Group 10, Class 01")
    print("  URL: http://127.0.0.1:5000")
    print("=" * 60)
    app.run(debug=True, port=5000, threaded=True)
