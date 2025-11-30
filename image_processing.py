import cv2
import numpy as np
import json
import math

is_processing = False

# ---------------------- FONCTIONS UTILITAIRES ------------------------


def get_rectangle_center(x1, y1, x2, y2):
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return cx, cy

def draw_circle(x, y, frame):
    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

def get_position_cm(x, y):
    cm_per_pixel = 0.08
    return x * cm_per_pixel, y * cm_per_pixel

def get_frame(image_path):
    frame = cv2.imread(image_path)
    if frame is None:
        print("Erreur : Impossible de charger l'image.")
    return frame

def rotate_photo_to_right(frame):
    return cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)

def rotate_photo_to_left(frame):
    return cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)

def calculate_angle(line1, line2):
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2

    if x2 - x1 == 0:
        angle1 = 90
    else:
        angle1 = np.degrees(np.arctan2(y2 - y1, x2 - x1))

    if x4 - x3 == 0:
        angle2 = 90
    else:
        angle2 = np.degrees(np.arctan2(y4 - y3, x4 - x3))

    return angle1 - angle2

def save_data_json(angle, posx, posy):
    try:
        with open("Data.json", "r") as f:
            data = json.load(f)
    except:
        data = {}

    data["angle"] = round(angle, 2)
    data["posx"] = round(posx, 2)
    data["posy"] = round(posy, 2)

    with open("Data.json", "w") as f:
        json.dump(data, f, indent=4)



def process(image_path):
   
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_left(initial_frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    cv2.imwrite("edges.jpg", edges)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00
    containers = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w,h) / float(max(w,h))
        area = w * h
        print(f"Contours :area ={area}")

        if aspect_ratio < 0.2 and h > 100:
            if h > max_line_height:
                max_line_height = h

                points = contour.reshape(-1, 2)
                x_coords = points[:, 0]
                y_coords = points[:, 1]

                A = np.vstack([x_coords, np.ones(len(x_coords))]).T
                m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]

                y1 = min(y_coords)
                y2 = max(y_coords)

                if abs(m) > 1e-6:
                    x1 = int((y1 - c) / m)
                    x2 = int((y2 - c) / m)
                else:
                    x1, x2 = np.mean(x_coords), np.mean(x_coords)

                best_line = (x1, y1, x2, y2)
                reference_line = (x1, y1, x1, y2)
                inclination_angle = calculate_angle(best_line, reference_line)

        perimeter = cv2.arcLength(contour, True)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)
        contour_area = cv2.contourArea(contour)

        if 0.5 <= aspect_ratio <= 1.2 and 2000 < area < 12000:
            if (
                contour_area != 0 and perimeter != 0 and
                (4 * np.pi * (contour_area / (perimeter**2))) <= 0.8 and
                0.5 <= (contour_area / float(area)) <= 1.0
            ):
                containers.append((x, y, w, h, area))

    # Suppression des doublons
    final_containers = []
    threshold_distance = 20

    for candidate in containers:
        x1, y1, w1, h1, area1 = candidate
        cx1 = x1 + w1 // 2
        cy1 = y1 + h1 // 2
        duplicate = False

        for accepted in final_containers:
            x2, y2, w2, h2, area2 = accepted
            cx2 = x2 + w2 // 2
            cy2 = y2 + h2 // 2
            distance = math.hypot(cx1 - cx2, cy1 - cy2)

            if distance < threshold_distance:
                duplicate = True
                break

        if not duplicate:
            final_containers.append(candidate)

    posx = posy = 0.00
    if bool(final_containers):
        x, y, w, h, area = min(final_containers, key=lambda c: c[0])
        cx, cy = get_rectangle_center(x, y, x+w, y+h)
        posx, posy = get_position_cm(cx, cy)
        save_data_json(inclination_angle, posx, posy)

    global is_processing
    is_processing = False

    return bool(final_containers), posx, posy, inclination_angle



def process_track(image_path, initial_y):
   
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_left(initial_frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    cv2.imwrite("edges.jpg", edges)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00
    containers = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w,h) / float(max(w,h))
        area = w * h

        if aspect_ratio < 0.2 and h > 100:
            if h > max_line_height:
                max_line_height = h

                points = contour.reshape(-1, 2)
                x_coords = points[:, 0]
                y_coords = points[:, 1]

                A = np.vstack([x_coords, np.ones(len(x_coords))]).T
                m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]

                y1 = min(y_coords)
                y2 = max(y_coords)

                if abs(m) > 1e-6:
                    x1 = int((y1 - c) / m)
                    x2 = int((y2 - c) / m)
                else:
                    x1, x2 = np.mean(x_coords), np.mean(x_coords)

                best_line = (x1, y1, x2, y2)
                reference_line = (x1, y1, x1, y2)
                inclination_angle = calculate_angle(best_line, reference_line)

        perimeter = cv2.arcLength(contour, True)
        contour_area = cv2.contourArea(contour)
        approx = cv2.approxPolyDP(contour, 0.02 * perimeter, True)

        if 0.5 <= aspect_ratio <= 1.2 and 2000 < area < 12000:
            if (
                4 <= len(approx) <= 6 and
                contour_area != 0 and perimeter != 0 and
                (4 * np.pi * (contour_area / (perimeter**2))) <= 0.8 and
                0.5 <= (contour_area / float(area)) <= 1.0
            ):
                containers.append((x, y, w, h, area))

    # suppression doublons
    final_containers = []
    threshold_distance = 20
    for c in containers:
        cx = c[0] + c[2]//2
        cy = c[1] + c[3]//2
        if not any(math.hypot(cx - (f[0]+f[2]//2), cy - (f[1]+f[3]//2)) < threshold_distance 
                   for f in final_containers):
            final_containers.append(c)

    posx = posy = 0
    if bool(final_containers):
        valid = [c for c in final_containers if c[1] > initial_y]
        if valid:
            x, y, w, h, area = min(valid, key=lambda c: c[0])
            cx, cy = get_rectangle_center(x, y, x+w, y+h)
            posx, posy = get_position_cm(cx, cy)
            save_data_json(inclination_angle, posx, posy)

    global is_processing
    is_processing = False
    return bool(final_containers), posx, posy, inclination_angle



def process_back(image_path):
   
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_right(initial_frame)

    height, width = frame.shape[:2]
    print(f"height : {height}, width : {width}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    inclination_angle = 0.00
    zone_detected = False
    posx = posy = 0.00

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w,h) / float(max(w,h))
        area = w * h

        if aspect_ratio < 0.2 and h > 100:
            points = contour.reshape(-1, 2)
            x_coords = points[:, 0]
            y_coords = points[:, 1]

            A = np.vstack([x_coords, np.ones(len(x_coords))]).T
            m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]

            y1 = min(y_coords)
            y2 = max(y_coords)

            if abs(m) > 1e-6:
                x1 = int((y1 - c) / m)
                x2 = int((y2 - c) / m)
            else:
                x1, x2 = np.mean(x_coords), np.mean(x_coords)

            best_line = (x1, y1, x2, y2)
            reference_line = (x1, y1, x1, y2)
            inclination_angle = calculate_angle(best_line, reference_line)

        if 0.3 <= aspect_ratio <= 1.2 and 50000 < area:
            zone_detected = True
            cx, cy = get_rectangle_center(x, y, x+w, y+h)
            posx, posy = get_position_cm(cx, cy)

    global is_processing
    is_processing = False

    return inclination_angle, zone_detected, posx, posy
