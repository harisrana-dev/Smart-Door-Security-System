import RPi.GPIO as GPIO
import time
import threading

# --- Pin Mapping ---
BUZZER = 17       # Passive buzzer instead of green LED
BLUE_LED = 19     # Heartbeat
PIR = 5
RELAY = 16

OUTPUT_PINS = [BUZZER, BLUE_LED, RELAY]


# --- Heartbeat ---
def slow_blink(pin, stop_event):
    """Blue heartbeat: HIGH briefly, LOW for 2s, until stop_event is set."""
    while not stop_event.is_set():
        GPIO.output(pin, GPIO.HIGH)
        if stop_event.wait(0.1):
            break
        GPIO.output(pin, GPIO.LOW)
        for _ in range(20):  # total ~2s
            if stop_event.wait(0.1):
                break


# --- Buzzer Melodies ---
def play_welcome_jingle(buzzer):
    """4-note success melody (access granted)."""
    notes = [2200, 2500, 3000, 2500]
    durations = [0.2, 0.2, 0.25, 0.35]
    pwm = GPIO.PWM(buzzer, 2500)
    for freq, dur in zip(notes, durations):
        pwm.ChangeFrequency(freq)
        pwm.start(90)
        time.sleep(dur)
        pwm.stop()
        time.sleep(0.05)
    pwm.stop()


def play_denied_tone(buzzer):
    """2 harsh buzzes (access denied)."""
    pwm = GPIO.PWM(buzzer, 2000)
    for _ in range(2):
        pwm.start(90)
        time.sleep(0.25)
        pwm.stop()
        time.sleep(0.15)
    pwm.stop()


# --- GPIO Control Class ---
class GPIOControl:
    def __init__(self):
        try:
            GPIO.setmode(GPIO.BCM)
        except RuntimeError as e:
            print("[WARN] GPIO mode already set:", e)

        GPIO.setwarnings(False)

        # Setup pins
        for pin in OUTPUT_PINS:
            GPIO.setup(pin, GPIO.OUT, initial=GPIO.LOW)
        GPIO.setup(PIR, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)

        # Start heartbeat
        self.heartbeat_stop = threading.Event()
        self.heartbeat_thread = threading.Thread(
            target=slow_blink, args=(BLUE_LED, self.heartbeat_stop), daemon=True
        )
        self.heartbeat_thread.start()

        self.pir_enabled = False
        self.is_processing = False

    # --- System States ---
    def idle(self):
        self.clear_non_heartbeat()

    def known_face(self):
        self.clear_non_heartbeat()
        play_welcome_jingle(BUZZER)

    def unknown_face(self):
        self.clear_non_heartbeat()
        play_denied_tone(BUZZER)

    def liveness_pass(self):
        self.clear_non_heartbeat()
        play_welcome_jingle(BUZZER)
        GPIO.output(RELAY, GPIO.HIGH)
        time.sleep(2)
        GPIO.output(RELAY, GPIO.LOW)
        self.idle()

    def liveness_running(self):
        print("[INFO] Liveness check running...")


    def liveness_fail_final(self):
        self.clear_non_heartbeat()
        play_denied_tone(BUZZER)

    # --- Utility ---
    def clear_non_heartbeat(self):
        for pin in OUTPUT_PINS:
            if pin != BLUE_LED:
                try:
                    GPIO.output(pin, GPIO.LOW)
                except Exception:
                    pass

    # --- Cleanup ---
    def cleanup(self):
        self.heartbeat_stop.set()
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join()
        self.clear_non_heartbeat()
        GPIO.cleanup()

    # --- GUI Aliases ---
    def processing(self):
        print("[INFO] Recognition running...")

    def access_granted(self):
        self.liveness_pass()

    def access_denied(self):
        self.liveness_fail_final()

    # --- PIR Handling ---
    def enable_pir(self, start_recognition_callback=None, poll_interval=0.5):
        if self.pir_enabled:
            return
        self.pir_enabled = True

        def pir_poll_loop():
            last_state = 0
            print("[INFO] PIR polling started on GPIO", PIR)
            while self.pir_enabled:
                state = GPIO.input(PIR)
                if state and not last_state:
                    print(f"[DEBUG] Motion detected on PIR pin {PIR}")
                    self._handle_pir(start_recognition_callback)
                last_state = state
                time.sleep(poll_interval)

        threading.Thread(target=pir_poll_loop, daemon=True).start()

    def _handle_pir(self, start_recognition_callback):
        try:
            print("[INFO] Motion detected")
        except Exception:
            pass

        if start_recognition_callback:
            try:
                threading.Thread(target=start_recognition_callback, daemon=True).start()
            except Exception as e:
                print("[ERROR] Failed to spawn recognition callback thread:", e)

    def disable_pir(self):
        if not self.pir_enabled:
            return
        self.pir_enabled = False
        print("[INFO] PIR disabled")

    def reenable_pir(self, start_recognition_callback=None, poll_interval=0.5):
        if self.pir_enabled:
            print("[DEBUG] PIR already enabled")
            return
        self.enable_pir(start_recognition_callback, poll_interval)
        print("[INFO] PIR re-enabled")
