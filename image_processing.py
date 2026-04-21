import cv2
import numpy as np
import json


def get_rectangle_center(x1, y1, x2, y2):
    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    return cx, cy


def draw_circle(x, y, frame):
    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)


def get_position_cm(x, y):
    cm_per_pixel = 0.08
    x_cm = x * cm_per_pixel
    y_cm = y * cm_per_pixel
    return x_cm, y_cm


def get_frame(image_path):
    frame = cv2.imread(image_path)
    if frame is None:
        raise ValueError(f"Erreur : impossible de charger l'image {image_path}")
    print("Image shape:", frame.shape)
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


def save_data_json(angle, posx, posy, filename="Data.json"):
    try:
        with open(filename, "r") as json_file:
            data = json.load(json_file)
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}

    data["angle"] = round(angle, 2)
    data["posx"] = round(posx, 2)
    data["posy"] = round(posy, 2)

    with open(filename, "w") as json_file:
        json.dump(data, json_file, indent=4)


def _detect_line_and_containers(frame):
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00
    containers = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w, h) / float(max(w, h))
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
                    x1 = int(np.mean(x_coords))
                    x2 = int(np.mean(x_coords))

                best_line = (x1, y1, x2, y2)
                reference_line = (x1, y1, x1, y2)
                inclination_angle = calculate_angle(best_line, reference_line)

        elif 0.5 <= aspect_ratio <= 1.2 and 2000 < area < 12000:
            containers.append((x, y, w, h, area))

    return edges, best_line, inclination_angle, containers


def process(image_path):
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_left(initial_frame)

    edges, best_line, inclination_angle, containers = _detect_line_and_containers(frame)

    cv2.imwrite("edges.jpg", edges)

    output_classified = frame.copy()

    if best_line:
        x1, y1, x2, y2 = best_line
        cv2.line(output_classified, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.line(output_classified, (x1, y1), (x1, y2), (255, 255, 0), 2)
        print(
            f"Ligne détectée de ({x1}, {y1}) à ({x2}, {y2}) "
            f"- Inclinaison réelle: {inclination_angle:.2f}°"
        )

    posx = 0.00
    posy = 0.00

    if containers:
        x, y, w, h, area = min(containers, key=lambda c: c[0])
        cv2.rectangle(output_classified, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cx, cy = get_rectangle_center(x, y, x + w, y + h)
        draw_circle(cx, cy, output_classified)
        posx, posy = get_position_cm(cx, cy)
        save_data_json(inclination_angle, posx, posy)
        print(f"Conteneur détecté - Surface: {area}")

    cv2.imwrite("output_final.jpg", output_classified)

    return bool(containers), posx, posy, inclination_angle


def process_track(image_path, initial_y):
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_left(initial_frame)

    edges, best_line, inclination_angle, containers = _detect_line_and_containers(frame)

    cv2.imwrite("edges.jpg", edges)

    output_classified = frame.copy()

    if best_line:
        x1, y1, x2, y2 = best_line
        cv2.line(output_classified, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.line(output_classified, (x1, y1), (x1, y2), (255, 255, 0), 2)
        print(
            f"Ligne détectée de ({x1}, {y1}) à ({x2}, {y2}) "
            f"- Inclinaison réelle: {inclination_angle:.2f}°"
        )

    posx = 0.00
    posy = 0.00
    valid_containers = [c for c in containers if c[1] > initial_y]

    if valid_containers:
        x, y, w, h, area = min(valid_containers, key=lambda c: c[0])
        cv2.rectangle(output_classified, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cx, cy = get_rectangle_center(x, y, x + w, y + h)
        draw_circle(cx, cy, output_classified)
        posx, posy = get_position_cm(cx, cy)
        save_data_json(inclination_angle, posx, posy)
        print(f"Conteneur détecté - Surface: {area}")

    cv2.imwrite("output_final.jpg", output_classified)
    cv2.imwrite("edges_final.jpg", edges)

    return bool(valid_containers), posx, posy, inclination_angle


def process_back(image_path):
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_right(initial_frame)

    height, width = frame.shape[:2]
    print(f"height : {height}, width : {width}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    cv2.imwrite("edges.jpg", edges)

    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00
    zone_detected = False
    posx = 0.00
    posy = 0.00

    output_classified = frame.copy()

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w, h) / float(max(w, h))
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
                    x1 = int(np.mean(x_coords))
                    x2 = int(np.mean(x_coords))

                best_line = (x1, y1, x2, y2)
                reference_line = (x1, y1, x1, y2)
                inclination_angle = calculate_angle(best_line, reference_line)

        if 0.3 <= aspect_ratio <= 1.2 and area > 50000:
            zone_detected = True
            cx, cy = get_rectangle_center(x, y, x + w, y + h)
            draw_circle(cx, cy, output_classified)
            posx, posy = get_position_cm(cx, cy)
            print("zone détectée")

    if best_line:
        x1, y1, x2, y2 = best_line
        cv2.line(output_classified, (x1, y1), (x2, y2), (0, 0, 255), 2)
        cv2.line(output_classified, (x1, y1), (x1, y2), (255, 255, 0), 2)
        print(
            f"Ligne détectée de ({x1}, {y1}) à ({x2}, {y2}) "
            f"- Inclinaison réelle: {inclination_angle:.2f}°"
        )

    cv2.imwrite("output_final.jpg", output_classified)
    print(f"Inclination angle: {inclination_angle}")

    return inclination_angle, zone_detected, posx, posy
