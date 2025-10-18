import cv2
import os
from datetime import datetime

# --- Settings ---
name = "Haris"
save_dir = os.path.join("known_faces", name)
os.makedirs(save_dir, exist_ok=True)

# --- Start webcam ---
cap = cv2.VideoCapture(0)
print("[INFO] Press SPACE to take snapshot, ESC to cancel.")

while True:
    ret, frame = cap.read()
    if not ret:
        print("❌ Failed to grab frame.")
        break

    cv2.imshow("Capture Face - Press SPACE", frame)

    key = cv2.waitKey(1)
    if key == 32:  # SPACE
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_path = os.path.join(save_dir, f"{name}_{timestamp}.jpg")
        cv2.imwrite(file_path, frame)
        print(f"[✅] Saved snapshot to {file_path}")
        break
    elif key == 27:  # ESC
        print("🚪 Exit without saving.")
        break

cap.release()
cv2.destroyAllWindows()
