import cv2
import numpy as np

face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")

# Smoothing factor for jitter reduction
SMOOTHING = 0.3
prev_box = None

def smooth_box(current_box):
    global prev_box
    if prev_box is None:
        prev_box = current_box
    else:
        prev_box = tuple([
            int(prev_box[i] * (1 - SMOOTHING) + current_box[i] * SMOOTHING)
            for i in range(4)
        ])
    return prev_box

def draw_label_with_background(img, text, pos, bg_color, alpha=0.5):
    """Draw text with a filled background rectangle (semi-transparent)."""
    font = cv2.FONT_HERSHEY_SIMPLEX
    font_scale = 0.5
    thickness = 1

    text_size, _ = cv2.getTextSize(text, font, font_scale, thickness)
    x, y = pos
    w, h = text_size
    pad = 4

    # Create overlay for transparency
    overlay = img.copy()

    # Background rectangle
    cv2.rectangle(overlay, (x, y - h - pad), (x + w + pad * 2, y + pad), bg_color, -1)

    # Blend with original image
    cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)

    # Draw text
    cv2.putText(img, text, (x + pad, y - pad), font, font_scale, (255, 255, 255), thickness, cv2.LINE_AA)

def detect_and_track_face(frame, recognition_result=None):
    global prev_box
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    if len(faces) == 0:
        prev_box = None
        return frame, None

    # Pick largest face
    x, y, w, h = max(faces, key=lambda rect: rect[2] * rect[3])
    x, y, w, h = smooth_box((x, y, w, h))

    tracked_frame = frame.copy()

    # Determine box color
    if recognition_result == "Unknown":
        box_color = (0, 0, 255)
    elif recognition_result:
        box_color = (0, 255, 0)
    else:
        box_color = (255, 255, 255)

    # Draw sleek rectangle
    # Draw sleek rectangle
    cv2.rectangle(tracked_frame, (x, y), (x + w, y + h), box_color, 1, cv2.LINE_AA)

    # Clamp label position
    if recognition_result:
       y_label = max(y - 10, 20)
       draw_label_with_background(tracked_frame, recognition_result, (x, y_label), box_color, alpha=0.6)
    return tracked_frame, frame[y:y+h, x:x+w]



# Standalone test
if __name__ == "__main__":
    cap = cv2.VideoCapture("rtsp://tapo.project:tapo2441@192.168.100.22:554/stream2", cv2.CAP_FFMPEG)
    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)   # drop old frames

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        frame, face_crop = detect_and_track_face(frame, recognition_result="Haris")

        cv2.imshow("Smooth Tracker", frame)
        if cv2.waitKey(1) & 0xFF == ord("q"):
            break

    cap.release()
    cv2.destroyAllWindows()
