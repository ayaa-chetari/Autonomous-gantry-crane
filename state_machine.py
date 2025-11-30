import os
import time
from picamera2 import Picamera2

from image_processing import process, process_track, process_back
from communication import send_data_esp

def start():
    global picam2
    picam2 = Picamera2()
    picam2.start()

    state = 1
    distance_from_start = 0.00
    step_distance = 20.00
    step_distance_feedback = 10.00
    inclination_angle = 0.00
    posx = 0.00
    posy = 0.00

    save_dir = './media/'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    while True:
        print("State =", state)

        if state == 1:
            send_data_esp(0.00, step_distance, inclination_angle, 'r')

            filename = os.path.join(save_dir, "photo.jpg")
            picam2.capture_file(filename)

            global is_processing
            is_processing = True
            is_containers, posx, posy, inclination_angle = process(filename)

            while is_processing:
                continue

            if is_containers:
                state = 2

            time.sleep(1.5)

        elif state == 2:
            initial_y = posy

            while posy < 18:
                if 10 < posy < 14:
                    send_data_esp(0.00, 5, inclination_angle, 'r')
                else:
                    send_data_esp(0.00, step_distance_feedback, inclination_angle, 'r')

                filename = os.path.join(save_dir, "photo.jpg")
                picam2.capture_file(filename)

                is_processing = True
                is_containers, posx, posy, inclination_angle = process(filename)

                while is_processing:
                    continue

                time.sleep(1)

            if 15.7 < posy < 22:
                send_data_esp(abs(posx - 3), 0.00, inclination_angle, 's')
                state = 3

            time.sleep(7)

        elif state == 3:
            send_data_esp(0.00, -10, 0.0, 'r')

            time.sleep(1.5)

            filename = os.path.join(save_dir, "photo.jpg")
            picam2.capture_file(filename)

            is_processing = True
            inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)

            while is_processing:
                continue

            while zone_detected == False:
                send_data_esp(0.00, -20, inclination_angle, 'r')

                time.sleep(1.5)

                filename = os.path.join(save_dir, "photo.jpg")
                picam2.capture_file(filename)

                is_processing = True
                inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)

                while is_processing:
                    continue

            while y_zone < 25:
                send_data_esp(0.00, -10, inclination_angle, 'r')
                time.sleep(1.5)

                filename = os.path.join(save_dir, "photo.jpg")
                picam2.capture_file(filename)

                is_processing = True
                inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)

                while is_processing:
                    continue

            send_data_esp(32 - abs(x_zone), 0.0, 0.0, 'p')
            time.sleep(10)

            state = 1
