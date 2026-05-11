# 🛡️ Project Report: Face Authentication Spoofing & Liveness Defense

## 1. Project Metadata
*   **Project topic:** Biometric Security: Face Authentication Spoofing and EAR-based Liveness Defense.
*   **Group Members:** 
    *   Dương Chí Chung - 52300011
    *   Tôn Lê Gia Bảo - 52300009
    *   Ngô Xuân Quang - 52300055
*   **Repository Link:** [Insert your GitHub/GitLab link here]

---

## 2. Executive Summary
For this project, we built a comprehensive web-based **Face Authentication System** using Flask and state-of-the-art AI models. We demonstrate a **Spoofing Attack** scenario where an attacker bypasses a vulnerable system using a high-resolution printed photo of the victim. To mitigate this threat, we implemented a **Liveness Detection** defense mechanism based on **Eye Aspect Ratio (EAR)** using **MediaPipe Face Mesh**. The demo proves that while a static photo can trick simple facial recognition, our secured system successfully blocks unauthorized access by detecting the absence of natural eye movement (blinking).

---

## 3. Lab Environment and Tools Setup
*   **Hardware:** Standard PC/Laptop with a 720p/1080p Webcam.
*   **Software and Libraries:**
    *   **Python 3.13:** Primary programming language.
    *   **Flask & Flask-CORS:** Web framework and cross-origin resource sharing.
    *   **DeepFace (VGG-Face + RetinaFace):** For high-accuracy face embedding and detection.
    *   **MediaPipe (Tasks API):** For real-time 468 facial landmark detection.
    *   **OpenCV:** Image processing and camera stream handling.
    *   **Numpy & Scipy:** Vector calculations and Euclidean/Cosine distance.
*   **Network Configuration:** Localhost environment (Port 5000).

### 🛠️ Installation & Quick Start
If you are cloning this repository for the first time, follow these steps:

1.  **Install Python Dependencies:**
    ```bash
    pip install flask flask-cors deepface mediapipe opencv-python numpy scipy tf-keras retina-face
    ```
2.  **Download AI Models:**
    The system uses several AI models that will be downloaded automatically on the first run (approx. 500MB). 
    Additionally, ensure the `face_landmarker.task` file is present in the root directory. If missing, the system or you can download it from [Google's MediaPipe Models](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task).

3.  **Run the Application:**
    ```bash
    python app.py
    ```
4.  **Access the UI:**
    Open your browser and go to `http://127.0.0.1:5000`.

---

## 4. Core Implementation and Code Analysis

### a. Architecture / Flow Logic
The system follows a Client-Server architecture:
1.  **Frontend (JS):** Captures webcam frames and sends them as Base64 strings to the backend.
2.  **Backend (Flask):** 
    *   **Vulnerable Mode:** Directly extracts face embeddings using `DeepFace` and compares them with stored data using Cosine Similarity.
    *   **Secure Mode:** First processes the frame through a `BlinkDetector`. It calculates the **EAR** for each frame. Only if a valid blink is detected (EAR dropping below threshold and rising back) does the system proceed to face recognition.

### b. Key Code Snippets & Explanation

**Snippet 1: EAR Calculation (Liveness Defense)**
```python
def calculate_ear(eye_landmarks, landmarks, img_w, img_h):
    # pts: 6 landmarks around the eye
    v1 = dist.euclidean(pts[1], pts[5]) # Vertical distance 1
    v2 = dist.euclidean(pts[2], pts[4]) # Vertical distance 2
    h  = dist.euclidean(pts[0], pts[3]) # Horizontal distance
    return (v1 + v2) / (2.0 * h)
```
*Explanation:* This code implements the mathematical formula for **Eye Aspect Ratio**. From a security perspective, it translates physiological movement into a numerical value. A static photo will have a constant EAR, whereas a real human eye will show a sharp dip during a blink, allowing the system to verify liveness.

**Snippet 2: Face Comparison (Identity Verification)**
```python
def compare_embeddings(stored_emb, input_emb):
    a = stored_emb / np.linalg.norm(stored_emb)
    b = input_emb / np.linalg.norm(input_emb)
    cosine_sim = np.dot(a, b)
    return cosine_sim, cosine_sim > 0.35
```
*Explanation:* We use **Cosine Similarity** instead of Euclidean distance. This measures the angle between two face feature vectors. It is more robust against lighting changes. The threshold `0.35` (for VGG-Face) ensures that even if two people look similar, they are rejected unless the AI is highly confident.

### c. Algorithms / Cryptography Used
*   **VGG-Face:** Chosen for its superior ability to discriminate between different individuals compared to standard Facenet.
*   **RetinaFace:** Used as the detector backend to ensure precise face cropping, even in challenging angles.
*   **Cosine Similarity:** Used for matching because it normalizes vector magnitude, focusing purely on facial features.

---

## 5. Step-by-Step Demonstration Walkthrough

*   **Step 1: Initialization & Registration**
    *   Description: Start the Flask server and navigate to `/register`. The victim registers their face.
*   **Step 2: The Attack (Vulnerable Login)**
    *   Description: The attacker holds a printed photo of the victim in front of the camera at `/login/vulnerable`.
    *   Result: The system identifies the face in the photo and grants access (Success).
*   **Step 3: The Defense (Secure Login)**
    *   Description: The attacker uses the same photo at `/login/secure`.
    *   Result: The system monitors the EAR. Since the photo cannot blink, the **Blink Count** remains `0`, and the system refuses authentication (Liveness Fail).
*   **Step 4: Verification**
    *   Description: The actual victim presents their face and blinks.
    *   Result: Access granted after the liveness check passes.

---

## 6. Vulnerability Patch / Defense Mechanism
The vulnerability in simple face recognition is the lack of **Temporal Analysis**. We patched this by adding a **State Machine (BlinkDetector)** that tracks the EAR over time. 
*   **Bypass possibility:** An advanced attacker could use a "Deepfake" video or a high-resolution screen playing a video of the victim blinking. To counter this, future versions could implement **Challenge-Response** (e.g., asking the user to turn their head or smile).

---

## 7. Conclusion and Limitations
*   **Hardest Challenges:** Handling the transition to MediaPipe Tasks API on Python 3.13 and fine-tuning the EAR threshold to avoid False Rejections while maintaining security.
*   **Limitations:** The current EAR check can be fooled by high-quality video playback on a screen. It also requires decent lighting for the landmarks to be detected accurately.
*   **Real-world improvement:** Integrate **Depth Sensing** (IR Camera) or **Texture Analysis** to distinguish between a flat 2D screen/paper and a 3D human face.

---

## 8. References & Attributions
*   [DeepFace Library](https://github.com/serengil/deepface) - Used for VGG-Face and RetinaFace implementation.
*   [MediaPipe Face Mesh](https://developers.google.com/mediapipe/solutions/vision/face_landmarker) - Used for landmark detection.
*   [PyImageSearch EAR Tutorial](https://pyimagesearch.com/2017/04/24/eye-blink-detection-opencv-python-dlib/) - Concept for EAR calculation.
*   AI Assistant (Antigravity): Assisted in refactoring code for Python 3.13 compatibility and drafting this documentation.
