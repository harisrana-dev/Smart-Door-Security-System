# 🔒 Smart Door Security System

A secure and intelligent door access system built with **real-time face recognition**, **head-pose–based liveness detection**, and a **manual PIN fallback** — powered by **OpenCV**, **dlib**, **CustomTkinter**, and **Raspberry Pi GPIO**.

---

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Core Logic](#core-logic)
- [Hardware Setup](#hardware-setup)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Acknowledgments](#acknowledgments)

---

## Overview
The **Smart Door Security System** enhances entry authentication by combining **face recognition** with **passive head-pose–based liveness detection**, ensuring only live, authorized users are granted access.  
If recognition fails or spoofing is detected, the system falls back to a **PIN keypad** for manual authentication.

The system integrates:
- **Real-time camera feed** (USB or RTSP IP camera)
- **PIR motion sensor trigger**
- **Relay-controlled door lock**
- **Buzzer and LED indicators**
- **Graphical interface** for status, prompts, and logs

All access attempts — successful or denied — are stored in structured **CSV logs**.

---

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

## Installation

### Prerequisites
- **Python 3.9+**
- **Raspberry Pi 4 Model B (recommended)**
- **OpenCV**, **dlib**, **CustomTkinter**, **face_recognition**
- Camera (USB or RTSP IP)

### Steps

1. **Clone repository**
    ```bash
    git clone <your-github-repo-url>
    cd SmartDoorSecuritySystem
    ```

2. **Install dependencies**
    ```bash
    pip install -r requirements.txt
    ```

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



**Version:** 1.0  
**Last Updated:** October 2025  
**Developed by:** Haris Kamal Rana  
Built with ❤️ using Python, OpenCV, dlib, and Raspberry Pi GPIO.





