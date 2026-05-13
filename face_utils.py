import cv2
import os
import numpy as np
import base64
from deepface import DeepFace
import mediapipe as mp
from scipy.spatial import distance as dist

# ─── Hằng số cấu hình ─────────────────────────────────────────────────────────
EAR_THRESHOLD    = 0.22   # Ngưỡng EAR thực tế (thường từ 0.20 - 0.26)
EAR_CONSEC_FRAMES = 1     # Số frame liên tiếp
FACE_MATCH_THRESHOLD = 0.70   # Ngưỡng so sánh Cosine Similarity cho Facenet512

# Khởi tạo MediaPipe Face Landmarker (API mới cho Python 3.13)
from mediapipe.tasks import python
from mediapipe.tasks.python import vision

# Model path (đã tải về)
MODEL_PATH = os.path.join(os.path.dirname(__file__), 'face_landmarker.task')

base_options = python.BaseOptions(model_asset_path=MODEL_PATH)
options = vision.FaceLandmarkerOptions(
    base_options=base_options,
    output_face_blendshapes=False,
    output_facial_transformation_matrixes=False,
    num_faces=1
)
landmarker = vision.FaceLandmarker.create_from_options(options)

# Landmark indices cho mắt
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]

# ══════════════════════════════════════════════════════════════════════════════
#  PHẦN 1: XỬ LÝ ẢNH
# ══════════════════════════════════════════════════════════════════════════════

def decode_image(base64_str: str) -> np.ndarray | None:
    """Giải mã ảnh từ chuỗi base64 (có hoặc không có data URL prefix)."""
    try:
        if "," in base64_str:
            base64_str = base64_str.split(",")[1]
        img_bytes  = base64.b64decode(base64_str)
        img_array  = np.frombuffer(img_bytes, dtype=np.uint8)
        img_bgr    = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        return img_bgr
    except Exception as e:
        print(f"[decode_image] Error: {e}")
        return None


def encode_image_to_base64(img_bgr: np.ndarray) -> str:
    """Mã hóa ảnh BGR sang base64 PNG để trả về client."""
    _, buffer = cv2.imencode(".png", img_bgr)
    return base64.b64encode(buffer).decode("utf-8")


# ══════════════════════════════════════════════════════════════════════════════
#  PHẦN 2: NHẬN DIỆN KHUÔN MẶT
# ══════════════════════════════════════════════════════════════════════════════

def extract_embedding(img_bgr: np.ndarray):
    """
    Trích xuất embedding sử dụng Facenet512 và RetinaFace (Mạnh nhất).
    """
    try:
        # Chuyển sang Facenet512: Phân biệt người lạ cực tốt, tốc độ và độ chính xác tối ưu
        # Sử dụng detector_backend="retinaface" để cắt mặt chính xác 100%
        res = DeepFace.represent(
            img_bgr, 
            model_name="Facenet512", 
            detector_backend="retinaface",
            enforce_detection=False
        )
        if len(res) > 0:
            return np.array(res[0]['embedding']), None
        return None, "Không tìm thấy khuôn mặt"
    except Exception as e:
        print("[extract_embedding] Error:", e)
        return None, "Lỗi AI"


def compare_embeddings(stored_emb: np.ndarray, input_emb: np.ndarray):
    """
    So sánh sử dụng Cosine Similarity với model Facenet512.
    """
    a = stored_emb / np.linalg.norm(stored_emb)
    b = input_emb / np.linalg.norm(input_emb)
    cosine_sim = np.dot(a, b)
    
    print(f">>> [DEBUG] Cosine Similarity (Facenet512): {cosine_sim:.4f}")
    
    # Với Facenet512 + Cosine:
    # - Cùng 1 người: Thường > 0.70
    # - Người khác: Thường < 0.50
    
    is_match = cosine_sim > FACE_MATCH_THRESHOLD
    
    # Điểm cosine_sim của Facenet512 đã khá chuẩn trên thang 1.0
    # Ta chỉ cần giới hạn nó trong khoảng [0, 1] để giao diện hiển thị hợp lý
    display_sim = float(max(0.0, min(1.0, cosine_sim)))
        
    return display_sim, bool(is_match)


# ══════════════════════════════════════════════════════════════════════════════
#  PHẦN 3: LIVENESS DETECTION - EAR (Eye Aspect Ratio) (REAL bằng MediaPipe)
# ══════════════════════════════════════════════════════════════════════════════

def calculate_ear(eye_landmarks, landmarks, img_w, img_h):
    """Tính Eye Aspect Ratio (EAR) dựa trên tọa độ landmarks."""
    # Lấy tọa độ (x, y) cho 6 điểm quanh mắt
    pts = []
    for idx in eye_landmarks:
        lm = landmarks[idx]
        pts.append((lm.x * img_w, lm.y * img_h))
    
    # EAR formula: (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    v1 = dist.euclidean(pts[1], pts[5])
    v2 = dist.euclidean(pts[2], pts[4])
    h  = dist.euclidean(pts[0], pts[3])
    
    return (v1 + v2) / (2.0 * h)


def get_face_info_from_frame(img_bgr: np.ndarray) -> dict:
    """
    Phân tích một frame sử dụng MediaPipe Tasks Landmarker: 
    - Phát hiện khuôn mặt
    - Tính EAR thực tế từ landmarks
    """
    result = {
        "face_detected": False,
        "ear": None,
        "eye_status": "unknown",
        "annotated_b64": None,
    }

    h, w = img_bgr.shape[:2]

    # Chuyển BGR sang MediaPipe Image object
    img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
    mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=img_rgb)
    
    # Thực hiện detect
    detection_result = landmarker.detect(mp_image)

    if not detection_result.face_landmarks:
        return result

    result["face_detected"] = True
    landmarks = detection_result.face_landmarks[0]

    # 1. Tính EAR cho cả 2 mắt và lấy trung bình
    ear_left  = calculate_ear(LEFT_EYE, landmarks, w, h)
    ear_right = calculate_ear(RIGHT_EYE, landmarks, w, h)
    ear       = (ear_left + ear_right) / 2.0

    result["ear"] = round(float(ear), 4)
    result["eye_status"] = "CLOSED" if ear < EAR_THRESHOLD else "OPEN"

    # 2. Vẽ landmarks để demo "Landmark Detection"
    annotated = img_bgr.copy()
    
    # Vẽ các điểm quanh mắt
    for idx in LEFT_EYE + RIGHT_EYE:
        lm = landmarks[idx]
        cv2.circle(annotated, (int(lm.x * w), int(lm.y * h)), 2, (0, 255, 100), -1)

    # Vẽ bounding box từ landmarks
    xs = [lm.x * w for lm in landmarks]
    ys = [lm.y * h for lm in landmarks]
    cv2.rectangle(annotated, (int(min(xs)), int(min(ys))), (int(max(xs)), int(max(ys))), (0, 255, 100), 1)

    # Hiển thị EAR
    status_color = (0, 100, 255) if ear < EAR_THRESHOLD else (0, 255, 100)
    cv2.putText(
        annotated,
        f"REAL EAR (Tasks): {ear:.3f} [{result['eye_status']}]",
        (10, 30),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.7, status_color, 2
    )

    result["annotated_b64"] = encode_image_to_base64(annotated)
    return result


# ══════════════════════════════════════════════════════════════════════════════
#  PHẦN 4: STATE MACHINE PHÁT HIỆN BLINK
# ══════════════════════════════════════════════════════════════════════════════

class BlinkDetector:
    def __init__(self):
        self.ear_history   : list[float] = []
        self.blink_count   : int         = 0
        self.consec_below  : int         = 0   
        self.eye_closed    : bool        = False

    def update(self, ear: float | None) -> bool:
        if ear is None:
            return False

        self.ear_history.append(ear)
        blink_completed = False

        if ear < EAR_THRESHOLD:
            self.consec_below += 1
            if self.consec_below >= EAR_CONSEC_FRAMES:
                self.eye_closed = True
        else:
            if self.eye_closed:
                self.blink_count += 1
                blink_completed  = True
            self.eye_closed   = False
            self.consec_below = 0

        return blink_completed

    def to_dict(self) -> dict:
        return {
            "blink_count"  : self.blink_count,
            "eye_closed"   : self.eye_closed,
            "liveness_pass": self.blink_count >= 1,
            "ear_history"  : self.ear_history[-30:],  
        }
