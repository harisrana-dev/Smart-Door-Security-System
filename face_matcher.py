import cv2
import numpy as np
import face_recognition

def ensure_uint8(image):
    if image is None or image.size == 0:
        return None
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        else:
            image = np.clip(image, 0, 255).astype(np.uint8)
    return image

def match_face(face_encoding, known_encodings, known_names, conf_threshold=0.6):
    try:
        if face_encoding is None:
            print("[ERROR] No encoding provided.")
            return None

        # Compare with known faces
        face_distances = face_recognition.face_distance(known_encodings, face_encoding)
        best_match_index = np.argmin(face_distances)
        similarity = 1 - face_distances[best_match_index]

        print(f"[DEBUG] Distances: {face_distances}")
        print(f"[DEBUG] Best match index: {best_match_index}, Similarity: {similarity}")

        if face_distances[best_match_index] < conf_threshold:
            return known_names[best_match_index]

        return None  # not "Unknown" – return None and let caller decide

    except Exception as e:
        print("[ERROR] Exception during face match:", e)
        return None
