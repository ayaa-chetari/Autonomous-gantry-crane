# Autonomous Gantry Crane – Computer Vision & Embedded Control  
*(Raspberry Pi 4 • OpenCV • Picamera2 • ESP32 • Real-Time Robotics)*

---

## Project Overview

This project implements an autonomous gantry crane capable of detecting, approaching, picking up, and placing containers using computer vision only.

A Raspberry Pi 4 performs real-time image processing, while an ESP32 handles low-level motor control.  
The system was designed under a strict constraint: no additional sensors (no ultrasonic, infrared, LiDAR, or encoders). All perception and positioning rely entirely on the camera.

The robot operates autonomously using a state machine that coordinates perception, motion, and actions.

---

## Objectives

The system is able to:

- Detect containers and a vertical reference line  
- Estimate position and orientation using vision  
- Align and move precisely toward a container  
- Pick up the container via ESP32  
- Detect a drop zone while reversing  
- Place the container accurately  

Once started, the system runs fully autonomously.

---

## System Architecture

The project is organized into three main modules:

### 1. Image Processing (`image_processing.py`)
Handles all computer vision tasks using OpenCV:

- Edge detection (Canny)  
- Contour detection  
- Vertical line detection using linear regression  
- Container detection based on geometry  
- Position estimation (pixel to cm conversion)  
- Drop zone detection during reverse motion  

---

### 2. Communication (`communication.py`)
Manages communication between Raspberry Pi and ESP32 via UART:

- Sends position corrections (X, Y)  
- Sends orientation correction (angle)  
- Sends control mode (movement or action)  
- Receives acknowledgements from ESP32  

---

### 3. Main Controller (`state_machine.py`)
Implements the state machine and system logic:

- Captures images using Picamera2  
- Calls image processing functions  
- Sends commands to ESP32  
- Controls the overall robot behavior  

---

## State Machine

The system operates with three main states:

### State 1 – Forward Search
- Moves forward step-by-step  
- Scans the environment for containers  

### State 2 – Approach and Alignment
- Moves toward the detected container  
- Continuously adjusts trajectory using visual feedback  
- Aligns precisely before pickup  

### State 3 – Reverse and Placement
- Moves backward  
- Detects the drop zone  
- Aligns and releases the container  

The system then returns to State 1.

---

## Workflow

1. Capture image from the camera  
2. Process image (line and object detection)  
3. Estimate position and orientation  
4. Send correction commands to ESP32  
5. Execute movement  
6. Repeat until task completion  

---

## Technologies Used

- Python  
- OpenCV  
- NumPy  
- Picamera2  
- PySerial (UART communication)  
- Raspberry Pi 4  
- ESP32  

---

## Project Structure

```text
project/
│
├── state_machine.py                # State machine (main controller)
├── communication.py       # UART communication with ESP32
├── image_processing.py    # Computer vision algorithms
│
├── media/                 # Captured images
├── Data.json              # Saved detection data (angle, position)
└── README.md
