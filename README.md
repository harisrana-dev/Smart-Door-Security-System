# 🔒 Smart Door Security System

Smart Door Security System — Intelligent access control using real-time face recognition and liveness verification on a Raspberry Pi.

🔹 Detects and tracks faces using OpenCV & dlib  
🔹 Verifies liveness via randomized head-pose prompts  
🔹 Provides a GUI fallback PIN entry  
🔹 Controls real hardware (relay, PIR sensor, buzzer) using GPIO  
🔹 Built to work under performance constraints

This project was designed and implemented by me as an end-to-end prototype,
with iterative development, debugging, and system integration on Raspberry Pi.

---

## Table of Contents
- [Overview](#overview)
- [Problem → Solution → Impact](#problem--solution--impact)
- [Features](#features)
- [Core Logic](#core-logic)
- [Hardware Setup](#hardware-setup)
- [Tech Stack & Skills](#tech-stack--skills)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)
- [Limitations & Future Work](#limitations--future-work)
- [What I Learned](#what-i-learned)
  

---

## Overview
This project implements a smart door security solution that authenticates users using face recognition and liveness detection, with a PIN-based fallback mechanism. The system is optimized to run in real time on low-power hardware (Raspberry Pi).

---

## Problem → Solution → Impact

### Problem
Traditional door access systems rely on keys or static passwords, which are prone to misuse and lack verification of a real human presence.

### Solution
This system combines face recognition with liveness verification and a PIN fallback, ensuring secure and flexible authentication on embedded hardware.

### Impact
- Works in real time on Raspberry Pi
- Reduces false access using liveness checks
- Integrates vision-based security with physical door control



## Features

- 🎥 **Real-time face detection & tracking**
- 🧠 **Face recognition** using `face_recognition` encodings
- 👁️ **Passive liveness detection** via randomized head-pose verification
- 🔢 **On-screen PIN fallback keypad**
- 💡 **CustomTkinter GUI** — clean, modern dark interface
- 🧾 **Access logs** with timestamp, recognition result, and verification state
- ⚙️ **GPIO hardware control** (relay, PIR, LED, buzzer)
- 🪶 **Smooth, non-blocking threading** for camera, recognition, and liveness
- 🧰 **Modular codebase** — easily expandable


---

## Core Logic

1. **PIR Motion Detection**
   - Detects movement and activates the camera feed automatically.

2. **Face Detection & Tracking**
   - Face tracked live using OpenCV.
   - Smooth green tracking box ensures user alignment before capture.

3. **Face Recognition**
   - `face_recognition` compares the live encoding with precomputed ones from `known_faces/`.
   - Best match under confidence threshold → recognized user.

4. **Head Pose Liveness Detection**
   - User is prompted to move head randomly (left, right, up, down).
   - Verified using `dlib`’s 68-point facial landmarks and pose estimation.
   - Fails if face disappears or doesn’t follow prompts.

5. **Manual PIN Fallback**
   - If recognition/liveness fails, user can enter PIN on a secure keypad.
   - PIN stored safely in `pin_fallback.py`.

6. **Logging & Access Control**
   - Access result logged in `logs/recognition_log.csv`.
   - GPIO relay activates door lock upon success.

---

## Hardware Setup

| Component | GPIO Pin | Function |
|------------|-----------|----------|
| PIR Sensor | GPIO 5 | Motion trigger |
| Relay Lock | GPIO 16 | Door lock control |
| Buzzer | GPIO 17 | Beep indication |
| Blue LED | GPIO 19 | System status |

🧩 **Tip:** Ensure all modules share a **common ground**.  
If using 5V relay, include a transistor or level shifter for protection.

---

## Tech Stack & Skills
- Python
- OpenCV (image processing & face detection)
- Raspberry Pi (GPIO, hardware interfacing)
- Computer Vision fundamentals (face recognition, landmarks)
- Tkinter / CustomTkinter (GUI)
- Multithreading (basic concurrency, threading issues explored)


---

## Installation

### Prerequisites
- **Python 3.9+**
- **Raspberry Pi 4 Model B (recommended)**
- **OpenCV**, **dlib**, **CustomTkinter**, **face_recognition**
- Camera (USB or RTSP IP)

### Steps

1. **Clone repository**
    ```bash
    git clone https://github.com/harisrana-dev/Smart-Door-Security-System
    cd SmartDoorSecuritySystem
    ```

2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```
    ⚠️ Note: `dlib` installation on Raspberry Pi may require manual compilation.


3. **Download models**
    Place the following files in the `models/` directory:
    ```
    models/shape_predictor_68_face_landmarks.dat
    models/deploy.prototxt
    models/res10_300x300_ssd_iter_140000.caffemodel
    ```

4. **Add authorized users**
    Create a folder inside `known_faces/` for each person:
    ```
    known_faces/Haris/
    ```

5. **Generate face encodings**
    ```bash
    python generate_encoding.py
    ```

6. **(Optional) Capture new faces directly**
    ```bash
    python live_capture.py
    ```

---

## Usage

Run the main program:
```bash
python main.py
```
**Workflow**
- System waits for motion → PIR triggers camera
- Face appears → Recognition starts
- If recognized → Liveness challenge (random directions)
- If passed → Relay unlocks door + success buzzer
- If failed → User can try **PIN fallback**
- Every attempt logged in `logs/recognition_log.csv`

---

## Project Structure

```bash
SmartDoorSecuritySystem/
│
├── main.py                # Entry point
├── gui_interface.py       # GUI interface (Tkinter)
├── face_logic.py          # Recognition and verification logic
├── face_matcher.py        # Encoding comparison
├── face_tracker.py        # Face tracking and bounding box
├── liveness_passive.py    # Head-pose-based liveness
├── pin_fallback.py        # PIN fallback GUI
├── gpio_control.py        # Relay, LED, buzzer, and PIR control
├── generate_encoding.py   # Encoding generator for known faces
├── intruder_log.py        # CSV-based logging
├── utils.py               # Pose estimation helpers
├── live_capture.py        # Quick webcam capture
│
├── models/                # Shape predictor and DNN face model
├── known_faces/           # Authorized face images
├── encodings/             # Pickle encodings
├── logs/                  # Recognition logs
├── requirements.txt       # Dependencies
└── README.md
```
---

## Configuration

| **Setting** | **File** | **Description** |
|--------------|-----------|-----------------|
| **PIN Code** | `pin_fallback.py` | Change the default PIN |
| **Recognition Threshold** | `face_matcher.py` | Adjust confidence level for matching |
| **Camera Source** | `main.py` | Update RTSP URL or USB camera index |
| **Liveness Difficulty** | `liveness_passive.py` | Change required directions or hold times |

---

## Troubleshooting

| **Issue** | **Possible Fix** |
|------------|------------------|
| **Camera not detected** | Check RTSP URL or USB index in `main.py`. |
| **Face not recognized** | Use better lighting and clear, frontal images. |
| **GUI freezes** | Ensure `customtkinter` is updated and avoid blocking calls. |
| **Liveness too strict** | Lower pose thresholds in `utils.py`. |
| **GPIO error** | Run the script with `sudo` on Raspberry Pi. |
| **dlib fails to install** | Run:<br>`sudo apt install cmake build-essential python3-dev` first. |

---

## Contributing

This is a **private academic project**, and external contributions are not currently open.  
However, collaboration or code review can be arranged upon request.

---

## License

This project is intended for **personal and educational use only**.  
Unauthorized redistribution, modification, or commercial use without explicit permission is strictly prohibited.

---

## Acknowledgments

- **OpenCV** — Computer Vision & Image Processing  
- **dlib** — Facial Landmarks & Head Pose Estimation  
- **face_recognition** — Simplified Facial Embeddings  
- **CustomTkinter** — Modern Tkinter-based GUI Framework  
- **Raspberry Pi GPIO** — Hardware Interface for Sensors & Actuators  

---

## Limitations & Future Work
- PIN fallback module requires refactoring due to threading conflicts
- Haar Cascade used instead of deep models to meet Raspberry Pi performance limits
- Liveness detection is rule-based and can be improved with learning-based methods

---

## What I Learned
- Optimizing computer vision pipelines for low-power devices
- Trade-offs between accuracy and performance (Haar Cascade vs deep models)
- Integrating software logic with physical hardware
- Debugging real-time systems and concurrency issues

---
 
**Developed by:** Haris Kamal Rana  
Built with ❤️ using Python, OpenCV, dlib, and Raspberry Pi GPIO.





