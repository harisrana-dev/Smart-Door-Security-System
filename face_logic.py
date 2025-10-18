import numpy as np
import cv2
import face_recognition
from face_encoding import load_encoding
from face_matcher import match_face

# Load known encodings
known_encodings, known_names = load_encoding("encodings/haris_encoding.pkl")

def recognize_and_verify(face_crop):
    if face_crop is None or face_crop.size == 0:
        print("[ERROR] Empty frame passed to recognize_and_verify.")
        return "Unknown Face\nAccess Denied"

    # Ensure uint8 type
    if face_crop.dtype != np.uint8:
        if face_crop.max() <= 1.0:
            face_crop = (face_crop * 255).astype(np.uint8)
        else:
            face_crop = np.clip(face_crop, 0, 255).astype(np.uint8)

    # Convert to RGB
    rgb = cv2.cvtColor(face_crop, cv2.COLOR_BGR2RGB)

    # Detect face locations inside the crop
    boxes = face_recognition.face_locations(rgb, model="hog")
    encodings = face_recognition.face_encodings(rgb, boxes)

    if not encodings:
        print("[ERROR] Face encoding failed.")
        return "Unknown Face\nAccess Denied"

    # Match with known encodings
    matched_name = match_face(encodings[0], known_encodings, known_names, conf_threshold=0.6)

    if matched_name:
        print(f"[SUCCESS] Match found: {matched_name}")
        return f"Recognized: {matched_name}\nAccess Granted"
    else:
        print("[FAILURE] No matching face found.")
        return "Unknown Face\nAccess Denied"
