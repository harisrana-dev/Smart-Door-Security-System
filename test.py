import RPi.GPIO as GPIO
import time

BUZZER_PIN = 17

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUZZER_PIN, GPIO.OUT)

pwm = GPIO.PWM(BUZZER_PIN, 2500)

# Notes in Hz (all loud range for passive buzzer)
notes = [2200, 2500, 3000, 2500]
durations = [0.2, 0.2, 0.25, 0.35]

try:
    for freq, dur in zip(notes, durations):
        pwm.ChangeFrequency(freq)
        pwm.start(90)   # loud duty cycle
        time.sleep(dur)
        pwm.stop()
        time.sleep(0.05)  # small gap

finally:
    GPIO.cleanup()
