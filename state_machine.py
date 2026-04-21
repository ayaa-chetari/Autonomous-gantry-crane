import os
import time
from picamera2 import Picamera2

from communication import ESP32Communication
from image_processing import process, process_back, process_track


def capture_image(picam2, save_dir, filename="photo.jpg"):
    path = os.path.join(save_dir, filename)
    picam2.capture_file(path)
    print(f"Captured {path}")
    return path


def run_state_machine():
    picam2 = Picamera2()
    picam2.start()

    esp = ESP32Communication()

    state = 1
    step_distance = 20.00
    step_distance_feedback = 10.00
    inclination_angle = 0.00
    posx = 0.00
    posy = 0.00

    save_dir = "./media/"
    os.makedirs(save_dir, exist_ok=True)

    try:
        while True:
            if state == 1:
                esp.send(0.00, step_distance, inclination_angle, 'r')

                filename = capture_image(picam2, save_dir)
                is_containers, posx, posy, inclination_angle = process(filename)
                print(is_containers, posx, posy, inclination_angle)

                if is_containers:
                    state = 2

                time.sleep(1)

            elif state == 2:
                initial_y = posy

                while posy < 18:
                    if 10 < posy < 14:
                        esp.send(0.00, 5, inclination_angle, 'r')
                    else:
                        esp.send(0.00, step_distance_feedback, inclination_angle, 'r')

                    filename = capture_image(picam2, save_dir)
                    is_containers, posx, posy, inclination_angle = process(filename)
                    print(is_containers, posx, posy, inclination_angle)
                    time.sleep(1)

                if 15.7 < posy < 22:
                    esp.send(abs(posx - 4), 0.00, inclination_angle, 's')
                    state = 3
                    time.sleep(7)
                else:
                    state = 1

            elif state == 3:
                filename = capture_image(picam2, save_dir)
                inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)
                print(inclination_angle, zone_detected)

                is_first_step_back = True

                while zone_detected is False:
                    if is_first_step_back:
                        esp.send(0.00, 0.00, inclination_angle, 'r')
                        time.sleep(5)
                        esp.send(0.00, 0.00, inclination_angle, 'r')
                        is_first_step_back = False
                        time.sleep(1)
                    else:
                        esp.send(0.00, -20, inclination_angle, 'r')

                    time.sleep(1)

                    filename = capture_image(picam2, save_dir)
                    inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)
                    print(inclination_angle, zone_detected)

                print(f"Y ZONE : {y_zone}")
                print(f"X ZONE : {x_zone}")

                time.sleep(1.5)

                while y_zone < 25:
                    esp.send(0.00, -10, inclination_angle, 'r')
                    time.sleep(1.5)

                    filename = capture_image(picam2, save_dir)
                    inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)
                    print(inclination_angle, zone_detected)

                time.sleep(5)
                esp.send(31 - abs(x_zone), 0.0, 0.0, 'p')
                time.sleep(10)

                state = 1
                esp.send(0.00, 0.00, inclination_angle, 'r')
                time.sleep(5)
                esp.send(0.00, 0.00, inclination_angle, 'r')

            print("End of loop, state = ", state)

    except KeyboardInterrupt:
        print("Arrêt du programme.")

    finally:
        picam2.stop()
        esp.close()


if __name__ == "__main__":
    run_state_machine()
