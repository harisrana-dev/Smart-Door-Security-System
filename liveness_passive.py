import cv2
import dlib
import time
import random
import threading
from utils import get_head_pose_direction

# ---- Load heavy models ONCE at import time ----
detector = dlib.get_frontal_face_detector()
predictor = dlib.shape_predictor("models/shape_predictor_68_face_landmarks.dat")

# ---- Shared liveness state (thread-safe access) ----
_liv_lock = threading.Lock()
liveness_state = {
    "directions": [],
    "current_index": 0,
    "start_time": 0.0,
    "max_wait": 28.0,
    "active": False,
    "last_pass_time": 0.0,
    "cooldown": 0.7,        # seconds between accepting subsequent directions
    "instruction_text": "", # latest text to show in GUI
    "worker_thread": None,
    "stop_request": False,
    # New keys for hold time logic:
    "hold_start": 0.0,
    "hold_required": 0.5,   # seconds user must hold pose before pass
    "completed": False,
}

def start_liveness_check(max_wait=28.0, cooldown=0.7, num_directions=2):
    with _liv_lock:
        dirs = ['left', 'right', 'up', 'down']
        random.shuffle(dirs)
        dirs = dirs[:num_directions]  # only pick a few directions
        liveness_state.update({
            "directions": dirs,
            "current_index": 0,
            "start_time": time.time(),
            "max_wait": float(max_wait),
            "active": True,
            "last_pass_time": 0.0,
            "cooldown": float(cooldown),
            "instruction_text": "",
            "stop_request": False,
            "hold_start": 0.0,
            "completed": False,
            "worker_thread": None,
        })
    return liveness_state["directions"]


def _liveness_worker(get_frame, on_finish, root):
    try:
        while True:
            with _liv_lock:
                if not liveness_state["active"] or liveness_state["stop_request"]:
                    break
                start_time = liveness_state["start_time"]
                max_wait = liveness_state["max_wait"]
                dirs = liveness_state["directions"]
                idx = liveness_state["current_index"]
                cooldown = liveness_state["cooldown"]
                hold_start = liveness_state["hold_start"]
                hold_required = liveness_state["hold_required"]

            # Timeout check
            if time.time() - start_time > max_wait:
                with _liv_lock:
                    liveness_state["instruction_text"] = "❌ Liveness Failed (timeout)"
                    liveness_state["active"] = False
                    liveness_state["completed"] = False
                    liveness_state["current_index"] = 0
                root.after(0, lambda: on_finish(False))
                break


            frame = get_frame()
            if frame is None:
                time.sleep(0.03)
                continue

            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            except Exception:
                time.sleep(0.03)
                continue

            faces = detector(gray)
            if not faces:
                with _liv_lock:
                    if idx < len(dirs):
                        liveness_state["instruction_text"] = f"Liveness: Move head {dirs[idx].upper()} ({idx+1}/{len(dirs)}) — face not found"
                time.sleep(0.03)
                continue

            shape = predictor(gray, faces[0])
            current_dir = get_head_pose_direction(shape, frame.shape)

            with _liv_lock:
                if idx < len(dirs):
                    expected = dirs[idx]
                    liveness_state["instruction_text"] = f"Liveness: Move head {expected.upper()} ({idx+1}/{len(dirs)})"

                now = time.time()
                if idx < len(dirs):
                    if current_dir == expected:
                        if hold_start == 0:
                            liveness_state["hold_start"] = now
                        elif (now - hold_start) >= hold_required:
                            if (now - liveness_state["last_pass_time"]) > cooldown:
                                # advance
                                liveness_state["current_index"] += 1
                                liveness_state["last_pass_time"] = now
                                liveness_state["hold_start"] = 0.0
                                # show the pass for this direction
                                liveness_state["instruction_text"] = f"{expected.upper()} ✅ Passed ({liveness_state['current_index']}/{len(dirs)})"
                                # if done, make sure GUI sees the "all ✅" state
                                if liveness_state["current_index"] >= len(dirs):
                                    liveness_state["current_index"] = len(dirs)
                                    liveness_state["completed"] = True
                                    # keep active=True for one more GUI tick so the last direction flips to ✅
                                    liveness_state["instruction_text"] = f"{expected.upper()} ✅ Passed ({liveness_state['current_index']}/{len(dirs)})"

                                    def _finish_success():
                                        with _liv_lock:
                                            liveness_state["active"] = False
                                        on_finish(True)

                                    # small delay lets GUI repaint the ✅ before we finish
                                    root.after(120, _finish_success)
                                    return
                    else:
                        # Reset hold timer if user moves away
                        liveness_state["hold_start"] = 0.0

            time.sleep(0.03)

    except Exception as e:
        with _liv_lock:
            liveness_state["active"] = False
            liveness_state["instruction_text"] = "❌ Liveness Error"
        root.after(0, lambda: on_finish(False))
        raise
    finally:
        with _liv_lock:
            liveness_state["worker_thread"] = None

def update_liveness_check(get_frame, info_label, on_finish, root):
    with _liv_lock:
        active = liveness_state.get("active", False)
        worker = liveness_state.get("worker_thread", None)

    if not active:
        if worker and worker.is_alive():
            with _liv_lock:
                liveness_state["stop_request"] = True
        return

    with _liv_lock:
        if liveness_state.get("worker_thread") is None or not liveness_state["worker_thread"].is_alive():
            th = threading.Thread(target=_liveness_worker, args=(get_frame, on_finish, root), daemon=True)
            liveness_state["worker_thread"] = th
            th.start()

    with _liv_lock:
        text = liveness_state.get("instruction_text", "Liveness: ...")
    try:
        info_label.configure(text=text)
    except Exception:
        pass

def stop_liveness_check():
    with _liv_lock:
        liveness_state["stop_request"] = True
        liveness_state["active"] = False
        liveness_state["instruction_text"] = ""
        liveness_state["hold_start"] = 0.0
        liveness_state["completed"] = False
        liveness_state["current_index"] = 0
        # do not mutate directions here; GUI uses them for rendering
        liveness_state["worker_thread"] = None
