import cv2
import numpy as np
import threading
import customtkinter as ctk
from customtkinter import CTkImage
from PIL import Image
from datetime import datetime
import traceback
import time

import liveness_passive as lp
from pin_fallback import PinPopup
from intruder_log import log_entry
from utils import get_head_pose_direction
from gpio_control import GPIOControl

# Appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

ACCENT = "#00E676"
FAIL = "#FF5252"
PROCESS = "#F1C40F"
PANEL = "#0f1113"
INNER_PANEL = "#0b0c0d"
BORDER = "#1f1f1f"

def font(name, size, weight=None):
    return (name, size, weight) if weight else (name, size)


class SmartDoorGUI:
    def __init__(self, get_frame, detect_and_track_face, recognize_and_verify, gpio: GPIOControl):
        self.get_frame = get_frame
        self.detect_and_track_face = detect_and_track_face
        self.recognize_and_verify = recognize_and_verify
        self.gpio = gpio

        # GUI state
        self.system_active = False
        self.recognition_result = None
        self.processing_done = False
        self.latest_face_crop = None
        self.liveness_active = False
        self.similarity = None
        self.cooldown_after_id = None
        self.liveness_recognition_results = []
        self.is_processing = False
        self._last_liveness_idx = -1
        self.allow_recognition_after_countdown = False
        self.on_cycle_complete = None
        self.locked_face_encoding = None
        self._liveness_validation_enabled = False
        self._liveness_validation_grace = 0.5
        self._last_face_check = 0.0
        self._last_face_check_result = True  # assume true initially
        self._face_check_interval = 0.4 
        self.pin_active = False     # seconds (400 ms)



        # ---------- Root ----------
        self.root = ctk.CTk()
        self.root.title("Smart Door Security System")
        self.root.geometry("980x560")
        self.root.resizable(False, False)
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_columnconfigure(1, weight=0)

        # ---------- Video Panel ----------
        self.video_outer = ctk.CTkFrame(self.root, corner_radius=18, fg_color=PANEL, border_width=4, border_color=BORDER)
        self.video_outer.grid(row=0, column=0, padx=(20, 10), pady=20, sticky="nsew")
        video_frame = ctk.CTkFrame(self.video_outer, corner_radius=14, fg_color=INNER_PANEL)
        video_frame.pack(expand=True, fill="both", padx=6, pady=6)
        self.video_label = ctk.CTkLabel(video_frame, text="", fg_color=INNER_PANEL, corner_radius=8)
        self.video_label.pack(expand=True, fill="both", padx=12, pady=12)
        ctk.CTkLabel(self.video_outer, text="Camera Feed", font=font("Segoe UI", 10)).pack(side="bottom", pady=(6, 10))
        ctk.CTkFrame(self.video_outer, corner_radius=6, fg_color="#04130b", height=6).pack(fill="x", padx=12, pady=(0, 12))

        # ---------- Info Panel ----------
        info_panel = ctk.CTkFrame(self.root, corner_radius=18, fg_color=PANEL, border_width=2, border_color=BORDER)
        info_panel.grid(row=0, column=1, padx=(10, 20), pady=20, sticky="ns")
        ctk.CTkLabel(info_panel, text="Smart Door", font=font("Segoe UI", 18, "bold")).pack(pady=(18, 6))
        self.clock_label = ctk.CTkLabel(info_panel, text="", font=font("Segoe UI", 14, "bold"), text_color=ACCENT)
        self.clock_label.pack(pady=(0, 6))
        self.date_label = ctk.CTkLabel(info_panel, text="", font=font("Segoe UI", 9))
        self.date_label.pack(pady=(0, 8))
        self.status_label = ctk.CTkLabel(info_panel, text="Waiting for face...", font=font("Segoe UI", 13),
                                         wraplength=240, justify="center")
        self.status_label.pack(padx=12, pady=(6, 12))

        # ---------- Compass ----------
        progress_frame = ctk.CTkFrame(info_panel, fg_color="#151515", corner_radius=12, width=220, height=160)
        progress_frame.pack(padx=12, pady=(6, 12))
        progress_frame.pack_propagate(False)
        compass_grid = ctk.CTkFrame(progress_frame, fg_color="#151515")
        compass_grid.pack(expand=True, fill="both", padx=8, pady=8)
        self.up_lab = ctk.CTkLabel(compass_grid, text="UP ❌", font=font("Segoe UI", 11))
        self.left_lab = ctk.CTkLabel(compass_grid, text="LEFT ❌", font=font("Segoe UI", 11))
        center_lab = ctk.CTkLabel(compass_grid, text=" ", font=font("Segoe UI", 11))
        self.right_lab = ctk.CTkLabel(compass_grid, text="RIGHT ❌", font=font("Segoe UI", 11))
        self.down_lab = ctk.CTkLabel(compass_grid, text="DOWN ❌", font=font("Segoe UI", 11))
        compass_grid.grid_rowconfigure((0,1,2), weight=1)
        compass_grid.grid_columnconfigure((0,1,2), weight=1)
        self.up_lab.grid(row=0, column=1, sticky="s")
        self.left_lab.grid(row=1, column=0, sticky="e")
        center_lab.grid(row=1, column=1)
        self.right_lab.grid(row=1, column=2, sticky="w")
        self.down_lab.grid(row=2, column=1, sticky="n")
        self.directions_labels = {"left": self.left_lab, "right": self.right_lab, "up": self.up_lab, "down": self.down_lab}

        # ---------- Buttons ----------
        self.pin_button = ctk.CTkButton(info_panel, text="Try PIN", corner_radius=10,
                                        command=self.launch_pin_popup)
        self.pin_button.pack(fill="x", padx=18, pady=(12, 6))

        self.retry_button = ctk.CTkButton(info_panel, text="Start Manually", corner_radius=10,
                                          command=self.try_again)
        self.retry_button.pack(fill="x", padx=18, pady=(6, 18))

        ctk.CTkLabel(info_panel, text="Logs saved to logs/recognition_log.csv", font=font("Segoe UI", 9)).pack(side="bottom", pady=(0, 12))


        # ---------- Start GUI ----------
        self.update_clock()
        self.go_idle()
        self.update_gui_loop()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    # -------------------- Methods --------------------
    def update_clock(self):
        now = datetime.now()
        self.clock_label.configure(text=now.strftime("%H:%M:%S"))
        self.date_label.configure(text=now.strftime("%a, %b %d %Y"))
        self.clock_label.configure(text_color=ACCENT if now.second % 2 == 0 else "#66ff99")
        self.root.after(2000, self.update_clock)

    def on_close(self):
        try:
            self.gpio.cleanup()
        except Exception as e:
            print("[ERROR] Cleanup failed:", e)
        self.root.destroy()

    def set_status(self, text, color=None):
        def _set():
            self.status_label.configure(text=text)
            if color:
                self.status_label.configure(text_color=color)
            else:
                if "granted" in text.lower():
                    self.status_label.configure(text_color=ACCENT)
                elif any(x in text.lower() for x in ["failed", "rejected", "unknown"]):
                    self.status_label.configure(text_color=FAIL)
                else:
                    self.status_label.configure(text_color=ACCENT)
        self.root.after(0, _set)

    def reset_progress(self):
        for k, lab in self.directions_labels.items():
            lab.configure(text=f"{k.upper()} ❌", text_color="#bdbdbd")

    def animate_glow(self, target_color, duration=800):
        self.video_outer.configure(border_color=target_color)
        self.root.after(duration, lambda: self.video_outer.configure(border_color=BORDER))


    def launch_pin_popup(self):
        self.pin_active = True
        self.system_active = False
        self.allow_recognition_after_countdown = False
        self.liveness_active = False
        self.is_processing = False

        # disable both buttons
        self.pin_button.configure(state="disabled")
        self.retry_button.configure(state="disabled")

        popup = PinPopup(self.root, correct_pin="1234")
        popup.focus_set()
        popup.grab_set()

        def check_result():
            if popup.winfo_exists():  # still open
                self.root.after(100, check_result)
            else:
                self.pin_active = False
                success = popup.result
                if success:
                    self.set_status("PIN Accepted ✅", ACCENT)
                    log_entry("PIN Fallback", None, verified=True)
                    self.gpio.access_granted()
                else:
                    self.set_status("PIN Rejected ❌", FAIL)
                    log_entry("PIN Fallback", None, verified=False)
                    self.gpio.access_denied()

                if self.on_cycle_complete:
                    self.on_cycle_complete()

                # re-enable buttons
                self.pin_button.configure(state="normal")
                self.retry_button.configure(state="normal")

                self.root.after(5000, self.go_idle)

        check_result()


    def try_again(self):
        if self.pin_active:  # 🚫 block while PIN popup is open
            return

        self.cancel_cooldown()
        self.processing_done = False
        self.liveness_active = False
        self.recognition_result = None
        self.similarity = None
        lp.stop_liveness_check()
        self.reset_progress()
        self.allow_recognition_after_countdown = False
        self.system_active = True
        self.set_status("Starting... Please align with camera", PROCESS)

        countdown = 3
        def countdown_loop(sec):
            if sec > 0:
                self.set_status(f"Starting... Please align with camera... {sec}", PROCESS)
                self.root.after(1000, lambda: countdown_loop(sec - 1))
            else:
                self.allow_recognition_after_countdown = True
                self.system_active = True
                self.set_status("Waiting for face...", PROCESS)

        countdown_loop(countdown)




    def cancel_cooldown(self):
        if self.cooldown_after_id:
            self.root.after_cancel(self.cooldown_after_id)
            self.cooldown_after_id = None

    def go_idle(self):
        self.system_active = False
        self.processing_done = False
        self.liveness_active = False
        self.recognition_result = None
        self.similarity = None
        self.latest_face_crop = None
        self.is_processing = False
        self.allow_recognition_after_countdown = False

        lp.stop_liveness_check()
        self.reset_progress()
        self.set_status("System Idle – waiting for motion...", None)
        self.gpio.idle()


    def on_motion_detected(self):
        if self.pin_active:  # 🚫 ignore motion while PIN window is open
            return
        # Reset stale processing flags so PIR can trigger even if system thought it was busy
        self.processing_done = False
        self.is_processing = False
        self.liveness_active = False
        self.recognition_result = None
        self.similarity = None
        self.latest_face_crop = None
        lp.stop_liveness_check()
        self.reset_progress()
        self.allow_recognition_after_countdown = False

        if getattr(self, "_motion_cooldown", False):
            return
        #self.system_active = True
        self._motion_cooldown = True
        self.root.after(1000, lambda: setattr(self, "_motion_cooldown", False))

        self.set_status("Motion detected! Please align with camera...", PROCESS)
        self.gpio.motion_detected()

        countdown = 5
        def countdown_loop(sec):
            if sec > 0:
                self.set_status(f"Motion detected! Align with camera... {sec}", PROCESS)
                self.root.after(1000, lambda: countdown_loop(sec - 1))
            else:
                self.allow_recognition_after_countdown = True
                self.system_active = True
                self.set_status("Waiting for face...", PROCESS)


        countdown_loop(countdown)


    def get_current_frame(self):
        try:
            frame = self.get_frame()
            if frame is not None and frame.size > 0:
                return frame.copy()
        except Exception as e:
            print("[ERROR] get_current_frame failed:", e)
        return None

    # -------------------- Recognition & Liveness --------------------
    def process_face_in_background(self, face_crop):
        if self.is_processing:
            print("[DEBUG] Recognition already running, skipping new request")
            return
        self.is_processing = True
        try:
            if face_crop is None or getattr(face_crop, "size", 0) == 0:
                raise ValueError("Empty face crop")
            if face_crop.dtype != np.uint8:
                if face_crop.max() <= 1.0:
                    face_crop = (face_crop * 255).astype(np.uint8)
                else:
                    face_crop = np.clip(face_crop, 0, 255).astype(np.uint8)

            self.gpio.processing()

            # ---- Step 1: Face recognition ----
            result_text = self.recognize_and_verify(face_crop)
            first_line = result_text.split("\n")[0].strip()
            if first_line.lower().startswith("recognized:"):
                self.recognition_result = first_line.replace("Recognized:", "").strip()
            else:
                self.recognition_result = "Unknown"

            self.similarity = None
            for line in result_text.split("\n"):
                if "Similarity:" in line:
                    try:
                        self.similarity = float(line.split(":")[1].strip())
                    except Exception as e:
                        print("[WARN] Could not parse similarity:", e)


            if self.recognition_result.lower() not in ("", "unknown"):
                self.set_status("Recognition done, checking liveness...")
            else:
                self.set_status(result_text, FAIL)

        except Exception as e:
            print("[ERROR] recognize_and_verify failed:", e)
            traceback.print_exc()
            self.set_status("Recognition failed.", FAIL)
            self.processing_done = True
            self.liveness_active = False
            self.recognition_result = None
            self.is_processing = False
            self.reset_progress()
            lp.stop_liveness_check()
            self.recognition_result = "Unknown"
            log_entry("Unknown", None, verified=True)
            self.gpio.access_denied()
            return

        # ---- Step 2: Liveness tied to recognition ----
        if self.recognition_result.lower() not in ("", "unknown"):
            self.lock_face_region(face_crop)
            self.reset_progress()
            self.liveness_active = True
            self.gpio.liveness_running()
            lp.start_liveness_check(num_directions=2)
            self.root.after(50, self.start_liveness_loop)
        else:
            self.recognition_result = ""
            self.set_status("Unknown face — Try manually", FAIL)
            self.pin_button.configure(state="normal")
            self.retry_button.configure(state="normal")

            self.processing_done = True
            self.liveness_active = False
            self.reset_progress()
            lp.stop_liveness_check()
            try:
                self.root.after(500, self.launch_pin_popup)

            except Exception as e:
                print("[ERROR] Could not launch PIN fallback:", e)
    
    def lock_face_region(self, face_crop):
        """Store the face region encoding to ensure liveness uses the same face.
        Tries crop first, then falls back to encoding on the latest full frame if available.
        """
        self.locked_face_encoding = None
        try:
            import face_recognition
            # Try encoding the crop first
            encodings = face_recognition.face_encodings(face_crop)
            if encodings:
                self.locked_face_encoding = encodings[0]
            else:
                # fallback: try encode on full frame area (if available)
                frame = self.get_current_frame()
                if frame is not None:
                    # try to find face locations in the full frame and encode first found
                    locations = face_recognition.face_locations(frame)
                    encs = face_recognition.face_encodings(frame, locations)
                    if encs:
                        self.locked_face_encoding = encs[0]
        except Exception as e:
            print("[WARN] Could not encode face for lock:", e)

        print(f"[DEBUG] lock_face_region: locked_face_encoding={'present' if self.locked_face_encoding is not None else 'none'}")


    def validate_face_still_present(self, frame):
        """Check if the same face is still in frame during liveness.
        Returns True = OK (face still present / matched), False = swapped/missing.
        Runs heavy face recognition in a background thread to avoid freezing GUI.
        """
        if self.locked_face_encoding is None:
            return True

        # Throttle
        now = time.time()
        if not hasattr(self, "_last_face_check"):
            self._last_face_check = 0.0
            self._last_face_check_result = True
            self._face_check_interval = 0.5  # seconds
            self._face_check_thread = None

        if now - self._last_face_check < self._face_check_interval:
            return self._last_face_check_result

        self._last_face_check = now

        # If thread is already running, just return last result
        if self._face_check_thread and self._face_check_thread.is_alive():
            return self._last_face_check_result

        def _face_check_worker(frame_copy):
            try:
                import face_recognition
                face_locations = face_recognition.face_locations(frame_copy)
                if not face_locations:
                    result = False
                    print("[DEBUG] validate_face_still_present: no faces detected in frame")
                else:
                    encodings = face_recognition.face_encodings(frame_copy, face_locations)
                    result = any(face_recognition.compare_faces([self.locked_face_encoding], enc, tolerance=0.5)[0]
                                 for enc in encodings)
                    if result:
                        print("[DEBUG] validate_face_still_present: found matching face")
                    else:
                        print("[DEBUG] validate_face_still_present: faces found but none matched")
            except Exception as e:
                print("[WARN] validate_face_still_present failed:", e)
                result = True  # fail-safe

            self._last_face_check_result = result

        # Copy frame to avoid race conditions
        frame_copy = frame.copy()
        self._face_check_thread = threading.Thread(target=_face_check_worker, args=(frame_copy,), daemon=True)
        self._face_check_thread.start()

        return self._last_face_check_result



    def start_liveness_loop(self):
        if not self.liveness_active:
            return

        # Ensure liveness module has a short grace period before enforcement
        if not self._liveness_validation_enabled:
            # schedule enabling of validation after grace delay (one-shot)
            self._liveness_validation_enabled = True
            self._liveness_validation_started_at = time.time()

        # update liveness module and get its state
        lp.update_liveness_check(self.get_frame, None, lambda passed: self.on_liveness_finish(passed), self.root)

        # If lp reports state, show progress; but enforce face lock only if:
        # - validation has been enabled (grace period passed), and
        # - lp.liveness_state reports active (so module is running prompts)
        dirs = lp.liveness_state.get("directions", [])
        idx = lp.liveness_state.get("current_index", 0)
        lp_active = lp.liveness_state.get("active", False)

        for i, d in enumerate(dirs):
            if i < idx:
                self.directions_labels[d.lower()].configure(text=f"{d.upper()} ✅", text_color=ACCENT)
            elif i == idx:
                self.directions_labels[d.lower()].configure(text=f"{d.upper()} ⏳", text_color=PROCESS)
            else:
                self.directions_labels[d.lower()].configure(text=f"{d.upper()} ❌", text_color="#bdbdbd")

        # Only enforce validation when lp is active and grace period passed
        if lp_active and self._liveness_validation_enabled:
            elapsed = time.time() - getattr(self, "_liveness_validation_started_at", 0)
            if elapsed >= self._liveness_validation_grace:
                # check face presence in current frame and fail early if swapped
                frame = self.get_current_frame()
                if frame is not None and not self.validate_face_still_present(frame):
                    print("[WARN] face missing or swapped during liveness -> failing liveness")
                    # directly call on_liveness_finish(False)
                    self.on_liveness_finish(False)
                    return

        # continue loop
        self.root.after(50, self.start_liveness_loop)


    def update_gui_loop(self):
        try:
            frame = self.get_current_frame()
            if self.liveness_active and frame is not None and not self.validate_face_still_present(frame):
                self.on_liveness_finish(False)
                return

            try:
                tracked_frame, face_crop = self.detect_and_track_face(frame, self.recognition_result)
                if face_crop is not None:
                    self.latest_face_crop = face_crop
            except Exception as e:
                print("[ERROR] detect_and_track_face failed:", e)
                traceback.print_exc()
                tracked_frame, face_crop = frame, None

            if self.system_active and self.allow_recognition_after_countdown and not self.processing_done and face_crop is not None and not self.is_processing:
                self.set_status("Recognizing...", PROCESS)
                self.processing_done = True
                self.pin_button.configure(state="disabled")
                self.retry_button.configure(state="disabled")

                threading.Thread(target=self.process_face_in_background, args=(face_crop,), daemon=True).start()
                self.allow_recognition_after_countdown = False

            # Liveness progress update
            if self.liveness_active and lp.liveness_state.get("active", False):
                dirs = lp.liveness_state.get("directions", [])
                idx = lp.liveness_state.get("current_index", 0)
                if getattr(self, "_last_liveness_idx", -1) != idx:
                    self._last_liveness_idx = idx
                    for di, label in self.directions_labels.items():
                        label.configure(text=f"{di.upper()} ❌", text_color="#bdbdbd")
                    for i, d in enumerate(dirs):
                        text = f"{d.upper()} "
                        if i < idx or idx >= len(dirs):
                            self.directions_labels[d.lower()].configure(text=text + "✅", text_color=ACCENT)
                        elif i == idx:
                            self.directions_labels[d.lower()].configure(text=text + "⏳", text_color=PROCESS)

            # Render video
            try:
                rgb = cv2.cvtColor(tracked_frame, cv2.COLOR_BGR2RGB)

                # Get label dimensions dynamically
                label_width = self.video_label.winfo_width()
                label_height = self.video_label.winfo_height()

                # Only resize if we have valid widget size, otherwise fallback
                if label_width > 0 and label_height > 0:
                    rgb = cv2.resize(rgb, (label_width, label_height), interpolation=cv2.INTER_AREA)
                else:
                    rgb = cv2.resize(rgb, (800, 480), interpolation=cv2.INTER_AREA)  # fallback

                img = Image.fromarray(rgb)

                # Force CTkImage to fit label
                img_tk = CTkImage(light_image=img, size=(label_width, label_height))
                self.video_label.configure(image=img_tk)
                self.video_label.image = img_tk  # keep reference

            except Exception as e:
                print("[ERROR] Video render failed:", e)

        except Exception as e:
            print("[ERROR] update_gui_loop:", e)

        self.root.after(33, self.update_gui_loop)


    def on_liveness_finish(self, success):
        self.liveness_active = False
        if success:
            self.set_status("Liveness confirmed ✅ Access granted", ACCENT)
            self.gpio.access_granted()
            log_entry(self.recognition_result or "Unknown", self.similarity, verified=True)
        else:
            self.set_status("Liveness failed ❌ Access denied", FAIL)
            self.gpio.access_denied()
            log_entry(self.recognition_result or "Unknown", self.similarity, verified=False)

        self.pin_button.configure(state="normal")
        self.retry_button.configure(state="normal")

        # ⏳ wait until system goes idle, then re-arm PIR
        self.cooldown_after_id = self.root.after(4000, self.finish_cycle)


    def finish_cycle(self):
        """Reset GUI and notify main to re-arm PIR after cycle fully ends."""
        self.go_idle()
        self.locked_face_encoding = None  # clear locked face
        if self.on_cycle_complete:
            self.on_cycle_complete()




def run_gui(get_frame, detect_and_track_face, recognize_and_verify, gpio):
    return SmartDoorGUI(get_frame, detect_and_track_face, recognize_and_verify, gpio)
