Autonomous Gantry Crane – Computer Vision & Embedded Control : 
(Raspberry Pi 4 • OpenCV • Picamera2 • ESP32 • Real-Time Robotics)


==> Project Overview : 

This project implements an autonomous gantry crane capable of detecting, approaching, picking up, and placing containers using computer vision and serial communication.
A Raspberry Pi processes camera images to understand the environment, while an ESP32 handles motor control and actuation.
The system was intentionally designed without any additional sensors—no ultrasonic, infrared, lidar, or encoders were allowed. All perception and positioning had to be performed exclusively through the camera.

The system performs its tasks automatically through a state machine that coordinates perception and movement.

==> Objectives : 

The crane is designed to:

- Detect containers and a vertical reference line using a camera
- Align its motion using visual feedback
- Move precisely toward a container and adjust its lateral position
- Pick up the container through the ESP32
- Reverse until it detects a drop zone
- Position itself accurately and place the container
  
The system runs fully autonomously once started.

==>  System Architecture : 

1️)  Image Processing (image_processing.py)

- The Raspberry Pi uses OpenCV to extract information from images captured by the Picamera2 module:
- Detection of a vertical guiding line
- Orientation estimation through linear regression
- Detection of containers based on contour geometry
- Measurement of the container’s position in centimeters
- Detection of the drop zone during backward movement




2️) Communication Layer (communication.py)

The Raspberry Pi communicates with an ESP32 through UART.
Each command sent contains:

- Position corrections in X and Y
- Orientation correction angle
- A mode defining the type of movement or action

The ESP32 returns acknowledgements when executing these commands.

3️) Autonomous Behavior – State Machine (state_machine.py)

The robot behaves according to a three-state control loop:

- State 1 – Forward Search

The crane moves forward in predefined increments while scanning for containers using the camera.

- State 2 – Approach & Alignment

Once a container is detected, the crane moves toward it while continuously adjusting its trajectory based on vision feedback.

- State 3 – Reverse & Placement

After picking up the container, the crane reverses, detects the drop zone, aligns itself, and releases the container.

The system then returns to State 1 to search for the next object.

==> Technologies Used :

Python, OpenCv,Numpy,Picamera2, Serial communication (PySerial), ESP32 microcontroller, Raspberry Pi 4









