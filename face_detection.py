# face_detection.py

import cv2
import numpy as np
import os
import dlib

def ensure_uint8(frame):
    if frame.dtype != np.uint8:
        if frame.max() <= 1.0:
            frame = (frame * 255).astype(np.uint8)
        else:
            frame = frame.astype(np.uint8)
    return frame

# Load the DNN model
MODEL_PATH = os.path.join('models/res10_300x300_ssd_iter_140000.caffemodel')
CONFIG_PATH = os.path.join('models/deploy.prototxt')
net = cv2.dnn.readNetFromCaffe(CONFIG_PATH, MODEL_PATH)
print("✅ DNN model loaded:", net is not None)

def detect_faces_dnn(frame, net=net, conf_threshold=0.5):
    frame = ensure_uint8(frame)  # 🔐 ensure valid dtype
    (h, w) = frame.shape[:2]

    blob = cv2.dnn.blobFromImage(frame, 1.0, (300, 300),
                                 (104.0, 177.0, 123.0))

    net.setInput(blob)
    detections = net.forward()

    boxes = []
    for i in range(detections.shape[2]):
        confidence = detections[0, 0, i, 2]

        if confidence > conf_threshold:
            box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
            (x1, y1, x2, y2) = box.astype("int")
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w - 1, x2), min(h - 1, y2)
            boxes.append((x1, y1, x2, y2))

    return boxes


detector = dlib.get_frontal_face_detector()

def detect_faces_dlib(frame):
    frame = ensure_uint8(frame)  # 🔐 ensure valid dtype
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = detector(gray)
    return faces
