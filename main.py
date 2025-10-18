import cv2
import numpy as np
import threading
import time
import sys

from gpio_control import GPIOControl
from gui_interface import SmartDoorGUI
from face_tracker import detect_and_track_face
from face_logic import recognize_and_verify

# ---- Config ----
PIN_CODE = "1234"

# ---- Camera setup ----
gst_pipeline = "gst_pipeline = rtsp://<username>:<password>@<camera_ip>:554/stream2"
video_capture = cv2.VideoCapture(gst_pipeline)

# Reduce buffering if backend supports it
try:
    video_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)
except Exception:
    pass

if not video_capture.isOpened():
    print("❌ ERROR: Could not open RTSP camera stream.")
    sys.exit(1)

# ---- Globals ----
latest_frame = None
frame_lock = threading.Lock()
stop_camera = False
shutting_down = False

recognition_active = False
state_lock = threading.Lock()
_rearm_lock = threading.Lock()


# ---- Camera loop ----
def camera_loop():
    """Continuously grab frames from the RTSP stream."""
    global latest_frame
    while not stop_camera:
        ret, frame = video_capture.read()
        if ret and frame is not None and getattr(frame, "size", 0) > 0:
            with frame_lock:
                latest_frame = frame
        else:
            time.sleep(0.05)
        time.sleep(0.005)


def get_latest_frame():
    """Return a safe cropped copy of the latest frame for GUI usage."""
    with frame_lock:
        if latest_frame is not None and getattr(latest_frame, "size", 0) > 0:
            frame = latest_frame.copy()
            h, w = frame.shape[:2]
            top, bottom = int(h * 0.08), int(h * 0.92)
            left, right = int(w * 0.08), int(w * 0.92)
            return frame[top:bottom, left:right]
    return np.zeros((480, 640, 3), dtype=np.uint8)


# ---- PIR reset helper ----
def reset_pir(gui, gpio):
    """Re-arm PIR and unlock recognition state."""
    global recognition_active

    def _rearm():
        global recognition_active
        if shutting_down:
            return

        if not _rearm_lock.acquire(blocking=False):
            print("[DEBUG] _rearm already running, skipping")
            return

        try:
            with state_lock:
                recognition_active = False
                # mirrored gpio flag cleared for extra safety
                try:
                    gpio.is_processing = False
                except Exception:
                    pass

            if getattr(gpio, "pir_enabled", False) and not getattr(gpio, "is_processing", False):
                print("[DEBUG] reset_pir: already armed — skipping re-arm")
                return

            try:
                gpio.idle()
            except Exception:
                pass

            try:
                gpio.reenable_pir(start_recognition_callback=lambda: pir_callback(gui, gpio))
            except Exception:
                pass

            print("[INFO] PIR re-armed, system idle, recognition unlocked")
            print(
                f"[DEBUG] recognition_active={recognition_active}, "
                f"gpio.pir_enabled={getattr(gpio, 'pir_enabled', None)}, "
                f"gpio.is_processing={getattr(gpio, 'is_processing', None)}"
            )

        except Exception as e:
            print("[ERROR] _rearm failed:", e)
        finally:
            _rearm_lock.release()

    if not shutting_down:
        gui.root.after(500, _rearm)


# ---- PIR callback ----
def pir_callback(gui, gpio):
    """Triggered by PIR → schedule countdown + recognition or PIN fallback."""
    global recognition_active

    with state_lock:
        print(
            f"[TRACE] pir_callback entered: recognition_active={recognition_active}, "
            f"gpio.is_processing={getattr(gpio,'is_processing',None)}"
        )
        # Only consult the main lock here. GUI/main owns the lifecycle.
        if recognition_active:
            print("[DEBUG] PIR ignored — recognition already running")
            return

        # mark busy
        recognition_active = True
        try:
            gpio.is_processing = True
        except Exception:
            pass

    try:
        gpio.disable_pir()
        print("[INFO] PIR disabled")
        print("[DEBUG] Locks set: recognition_active=True, gpio.is_processing=True")
        print("[EVENT] PIR triggered - scheduling countdown on GUI thread")

        def start_countdown_and_capture():
            countdown = 4

            def tick(sec):
                if shutting_down:
                    return
                if sec > 0:
                    gui.set_status(f"Motion detected! Align with camera... {sec}", "#F1C40F")
                    gui.root.after(1000, lambda: tick(sec - 1))
                else:
                    gui.set_status("Capturing frame...", "#F1C40F")
                    frame = get_latest_frame()

                    if frame is None or getattr(frame, "size", 0) == 0:
                        print("[ERROR] No frame available after countdown")
                        gui.set_status("No camera frame — System Idle", "#FF5252")
                        # safe to rearm here because no recognition started
                        reset_pir(gui, gpio)
                        return

                    try:
                        _, face_crop = detect_and_track_face(frame)
                    except Exception as e:
                        print(f"[ERROR] detect_and_track_face failed: {e}")
                        face_crop = None

                    if face_crop is not None and getattr(face_crop, "size", 0) > 0:
                        print("[INFO] Face detected — starting recognition")

                        # Disable buttons during recognition (same as manual start)
                        try:
                            gui.pin_button.configure(state="disabled")
                            gui.retry_button.configure(state="disabled")
                        except Exception as e:
                            print("[WARN] Could not disable buttons:", e)

                        # START recognition — do NOT call reset_pir here.
                        def process_face():
                            gui.process_face_in_background(face_crop)

                        threading.Thread(target=process_face, daemon=True).start()


                    else:
                        print("[WARN] No face detected — launching PIN fallback")
                        gui.set_status("No face detected — Try PIN", "#FF5252")

                        # Launch PIN popup through GUI thread; GUI path will call on_cycle_complete
                        def run_pin():
                            # use GUI's non-blocking PIN flow (GUI handles on_cycle_complete)
                            gui.launch_pin_popup()

                        gui.root.after(100, run_pin)


            tick(countdown)

        if not shutting_down:
            gui.root.after(0, start_countdown_and_capture)

    except Exception as e:
        print("[ERROR] pir_callback top-level error:", e)
        # emergency unlock
        reset_pir(gui, gpio)


# ---- Main ----
if __name__ == "__main__":
    try:
        gpio = GPIOControl()
        gpio.idle()

        cam_thread = threading.Thread(target=camera_loop, daemon=False)
        cam_thread.start()
        time.sleep(0.5)

        gui = SmartDoorGUI(get_latest_frame, detect_and_track_face, recognize_and_verify, gpio)

        # GUI will call this when a full cycle (recognition + liveness or PIN fallback) completes.
        gui.on_cycle_complete = lambda: reset_pir(gui, gpio)

        gpio.enable_pir(start_recognition_callback=lambda: pir_callback(gui, gpio))

        print("✅ System armed, GUI running... waiting for PIR motion.")
        gui.root.mainloop()

    except KeyboardInterrupt:
        print("\n[INFO] Keyboard interrupt detected. Exiting...")

    finally:
        shutting_down = True
        stop_camera = True
        try:
            cam_thread.join(timeout=2)
        except Exception:
            pass
        try:
            video_capture.release()
        except Exception:
            pass
        try:
            cv2.destroyAllWindows()
        except Exception:
            pass
        try:
            gpio.cleanup()
        except Exception as e:
            print("[ERROR] gpio.cleanup failed:", e)
        print("[INFO] System shutdown complete.")
