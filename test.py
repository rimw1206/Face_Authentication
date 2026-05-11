import cv2
import numpy as np
from deepface import DeepFace
import mediapipe.python.solutions.face_mesh as mp_face_mesh

face_mesh = mp_face_mesh.FaceMesh(static_image_mode=True, max_num_faces=1, refine_landmarks=True)

img = np.zeros((300, 300, 3), dtype=np.uint8)
cv2.rectangle(img, (100, 100), (200, 200), (255, 255, 255), -1)

try:
    print("Testing MediaPipe...")
    results = face_mesh.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    if results.multi_face_landmarks:
        print("MediaPipe OK. Found face.")
    else:
        print("MediaPipe OK. No face found as expected.")
except Exception as e:
    print("MediaPipe Error:", e)

try:
    print("Testing DeepFace...")
    res = DeepFace.represent(img, model_name="VGG-Face", enforce_detection=False)
    print("DeepFace OK. Embedding length:", len(res[0]['embedding']))
except Exception as e:
    print("DeepFace Error:", e)

