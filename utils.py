import cv2
import numpy as np
import math
import dlib

# -------------------- Head-Pose Globals --------------------
yaw_avg = 0.0
pitch_avg = 0.0
alpha = 0.3  # smoothing factor for EMA
prev_direction = "center"

calib_frames = []
calib_needed_frames = 20
pitch_offset = None
yaw_offset = None

# -------------------- Head-Pose / Liveness --------------------
def get_head_pose_direction(face_landmarks, frame_shape):
    global yaw_avg, pitch_avg, prev_direction
    global calib_frames, pitch_offset, yaw_offset

    # 3D model points
    model_points = np.array([
        (0.0, 0.0, 0.0),          # Nose tip
        (0.0, -330.0, -65.0),     # Chin
        (-225.0, 170.0, -135.0),  # Left eye corner
        (225.0, 170.0, -135.0),   # Right eye corner
        (-150.0, -150.0, -125.0), # Left mouth
        (150.0, -150.0, -125.0)   # Right mouth
    ], dtype=np.float64)

    image_points = np.array([
        (face_landmarks.part(30).x, face_landmarks.part(30).y),
        (face_landmarks.part(8).x,  face_landmarks.part(8).y),
        (face_landmarks.part(36).x, face_landmarks.part(36).y),
        (face_landmarks.part(45).x, face_landmarks.part(45).y),
        (face_landmarks.part(48).x, face_landmarks.part(48).y),
        (face_landmarks.part(54).x, face_landmarks.part(54).y)
    ], dtype=np.float64)

    h, w = frame_shape[:2]
    focal_length = w
    center = (w / 2, h / 2)
    camera_matrix = np.array([[focal_length, 0, center[0]],
                              [0, focal_length, center[1]],
                              [0, 0, 1]], dtype=np.float64)
    dist_coeffs = np.zeros((4, 1))

    ok, rvec, tvec = cv2.solvePnP(model_points, image_points, camera_matrix, dist_coeffs)
    if not ok:
        return prev_direction

    R, _ = cv2.Rodrigues(rvec)
    sy = math.sqrt(R[0,0]**2 + R[1,0]**2)
    singular = sy < 1e-6

    if not singular:
        pitch = math.atan2(R[2,1], R[2,2])
        yaw   = math.atan2(-R[2,0], sy)
    else:
        pitch = math.atan2(-R[1,2], R[1,1])
        yaw   = math.atan2(-R[2,0], sy)

    pitch = -math.degrees(pitch)  # invert to match GUI
    yaw   = math.degrees(yaw)

    # Clamp angles
    pitch = (pitch + 180) % 360 - 180
    yaw   = (yaw + 180) % 360 - 180

    # Non-blocking calibration
    if pitch_offset is None or yaw_offset is None:
        calib_frames.append((pitch, yaw))
        if len(calib_frames) >= calib_needed_frames:
            pitch_offset = np.mean([p for p, _ in calib_frames])
            yaw_offset   = np.mean([y for _, y in calib_frames])
        return prev_direction  # do not freeze GUI

    pitch -= pitch_offset
    yaw   -= yaw_offset

    # Smooth with EMA
    yaw_avg = alpha * yaw + (1 - alpha) * yaw_avg
    pitch_avg = alpha * pitch + (1 - alpha) * pitch_avg

    # Direction thresholds
    LEFT_T, RIGHT_T = -15, 15
    UP_T, DOWN_T = -10, 10

    if yaw_avg < LEFT_T:
        direction = "left"
    elif yaw_avg > RIGHT_T:
        direction = "right"
    elif pitch_avg < UP_T:
        direction = "up"
    elif pitch_avg > DOWN_T:
        direction = "down"
    else:
        direction = "center"

    prev_direction = direction
    return direction
