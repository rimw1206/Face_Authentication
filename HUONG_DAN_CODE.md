# Giải Thích Chi Tiết Mã Nguồn Hệ Thống Xác Thực Khuôn Mặt (Face Authentication)

Tài liệu này giải thích chi tiết cách hoạt động của mã nguồn Python trong dự án, bao gồm xử lý hình ảnh, nhận diện khuôn mặt và kiểm tra thực thể sống (liveness detection).

---

## 1. Kiến Trúc Tổng Quan

Dự án được xây dựng dựa trên kiến trúc **Client-Server**:
- **Backend (Python):** Sử dụng Flask để tạo các API xử lý logic.
- **Frontend (HTML/JS):** Gửi frame từ webcam lên server để xử lý thông qua WebSockets hoặc HTTP POST.

Dự án chia làm 2 file chính:
1. `app.py`: Quản lý các route, session và lưu trữ dữ liệu người dùng.
2. `face_utils.py`: Chứa các hàm xử lý AI lõi (nhận diện, landmark, tính toán EAR).

---

## 2. Công Nghệ Sử Dụng

- **Flask:** Framework web nhẹ để tạo API.
- **OpenCV (cv2):** Xử lý ma trận hình ảnh, vẽ landmarks và encoding/decoding ảnh.
- **DeepFace:** Thư viện AI mạnh mẽ để trích xuất đặc trưng khuôn mặt (Face Embedding).
  - Model: `VGG-Face` (được cấu hình để phân biệt đặc điểm khuôn mặt chính xác).
  - Detector: `RetinaFace` (backend phát hiện khuôn mặt mạnh nhất hiện nay).
- **MediaPipe (Tasks API):** Phát hiện 468 điểm landmarks trên khuôn mặt để tính toán liveness trong thời gian thực.
- **NumPy & SciPy:** Hỗ trợ tính toán ma trận và khoảng cách Euclid giữa các điểm.

---

## 3. Quy Trình Xử Lý Chi Tiết

### A. Đăng ký người dùng (`/api/register`)
1. Nhận ảnh Base64 và tên người dùng từ Client.
2. Giải mã ảnh sang định dạng BGR (OpenCV).
3. Sử dụng `DeepFace.represent()` để trích xuất "vân tay khuôn mặt" (Face Embedding) - một mảng số đại diện cho các đặc điểm duy nhất của khuôn mặt.
4. Lưu dữ liệu này vào file định dạng `.pkl` (Pickle) trong thư mục `data/users/`.

### B. Đăng nhập có lỗ hổng (`/api/login/vulnerable`)
- **Quy trình:** Chỉ thực hiện so sánh khuôn mặt (Face Matching).
- **Vấn đề:** Nếu một người cầm bức ảnh hoặc điện thoại có hình người dùng chính chủ đưa trước camera, hệ thống vẫn nhận diện đúng Embedding và cho phép vào. Đây là lỗ hổng **Presentation Attack**.

### C. Đăng nhập bảo mật (`/api/login/secure`)
- **Quy trình:** Bắt buộc vượt qua bước **Kiểm tra Liveness** (người thật) thông qua hành động chớp mắt, sau đó mới so sánh khuôn mặt.
- Nếu không có hành động chớp mắt, hệ thống sẽ từ chối ngay cả khi khuôn mặt khớp 100%.

---

## 4. Cơ Chế Liveness Detection (EAR)

Đây là phần quan trọng nhất để chống giả mạo, nằm trong `face_utils.py`.

### Chỉ số EAR (Eye Aspect Ratio):
Dựa trên các tọa độ điểm (landmarks) quanh mắt do MediaPipe cung cấp.
- **Khi mắt mở:** Khoảng cách giữa mí trên và mí dưới lớn -> EAR cao (~0.25 - 0.30).
- **Khi mắt nhắm:** Khoảng cách mí trên và dưới gần bằng 0 -> EAR giảm mạnh (< 0.20).

### Lớp `BlinkDetector` (Bộ đếm chớp mắt):
Lớp này đóng vai trò như một máy trạng thái (State Machine):
- Theo dõi EAR qua từng frame.
- Nếu EAR thấp hơn ngưỡng `0.22` trong một khoảng thời gian ngắn rồi cao trở lại -> Xác nhận là **1 lần chớp mắt**.
- Người thật mới có thể thực hiện hành động này một cách tự nhiên.

---

## 5. Các Hàm Quan Trọng Trong `face_utils.py`

| Hàm | Nhiệm vụ |
| :--- | :--- |
| `extract_embedding` | Chuyển ảnh khuôn mặt thành vector số (vân tay khuôn mặt). |
| `compare_embeddings` | So sánh 2 vector bằng thuật toán **Cosine Similarity**. |
| `calculate_ear` | Tính tỉ lệ mở mắt từ các tọa độ điểm mắt. |
| `get_face_info_from_frame` | Detect mặt, tính EAR và vẽ minh họa landmarks cho người dùng thấy. |
| `decode_image` | Chuyển dữ liệu ảnh từ trình duyệt gửi lên thành định dạng Python xử lý được. |

---

## 6. Lưu Trữ Dữ Liệu
Dữ liệu người dùng được lưu dưới dạng file **Pickle** để tối ưu tốc độ đọc ghi mảng NumPy. Hệ thống tự động tải toàn bộ người dùng vào bộ nhớ khi khởi động để phản hồi API tức thì.
