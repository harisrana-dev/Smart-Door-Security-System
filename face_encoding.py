import cv2
import numpy as np
import face_recognition
import pickle
import os

def load_encoding(file_path):
    try:
        with open(file_path, "rb") as f:
            data = pickle.load(f)

        if isinstance(data, dict) and "encodings" in data and "names" in data:
            print(f"[INFO] Loaded {len(data['encodings'])} encodings from file.")
            return data["encodings"], data["names"]

        raise ValueError("⚠️ Encoding file format is invalid or missing required keys.")
    
    except (pickle.UnpicklingError, EOFError, FileNotFoundError) as e:
        raise ValueError(f"⚠️ Failed to load encoding file: {str(e)}")


def detect_faces(frame):
    if frame is None or frame.size == 0:
        return []

    small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
    rgb_small_frame = small_frame[:, :, ::-1]
    return face_recognition.face_locations(rgb_small_frame)


def ensure_uint8(image):
    if image.dtype != np.uint8:
        if image.max() <= 1.0:
            image = (image * 255).astype(np.uint8)
        else:
            image = image.astype(np.uint8)
    return image


def get_face_encodings(frame, face_locations):
    frame = ensure_uint8(frame)
    rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    return face_recognition.face_encodings(rgb_frame, face_locations)


def compare_faces(face_encoding, known_encodings, known_names, threshold=0.55):
    if face_encoding is None:
        print("[WARN] Face encoding is None.")
        return "Unknown", 0.0

    distances = face_recognition.face_distance(known_encodings, face_encoding)
    print(f"[DEBUG] Distances: {distances}")

    if len(distances) == 0:
        return "Unknown", 0.0

    best_match_index = np.argmin(distances)
    similarity = 1 - distances[best_match_index]
    print(f"[DEBUG] Best match index: {best_match_index}, Similarity: {similarity}")

    if similarity > threshold:
        return known_names[best_match_index], similarity

    return "Unknown", similarity


def recognize_face_dnn(face_img, known_encodings, known_names, threshold=0.55):
    face_img = ensure_uint8(face_img)
    padded_face = cv2.copyMakeBorder(face_img, 10, 10, 10, 10, cv2.BORDER_REPLICATE)
    face_rgb = cv2.cvtColor(padded_face, cv2.COLOR_BGR2RGB)

    face_encodings = face_recognition.face_encodings(face_rgb)

    if not face_encodings:
        print("[WARN] No encoding found in face region.")
        return "Unknown", 0.0

    encoding = face_encodings[0]
    distances = face_recognition.face_distance(known_encodings, encoding)

    if len(distances) == 0:
        print("[WARN] No known encodings to compare with.")
        return "Unknown", 0.0

    min_distance = min(distances)
    index = np.argmin(distances)
    similarity = 1 - min_distance

    print(f"[DEBUG] Match Distance: {min_distance}, Similarity: {similarity}, Name: {known_names[index]}")

    if similarity > threshold:
        return known_names[index], similarity
    else:
        return "Unknown", similarity


def load_known_faces(file_path):
    with open(file_path, 'rb') as f:
        encoding = pickle.load(f)

    known_encodings = [encoding]
    known_names = ["Haris"]
    print("[INFO] Loaded manual face encoding.")
    return known_encodings, known_names
