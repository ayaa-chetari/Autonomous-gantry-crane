import cv2
import numpy as np
import matplotlib.pyplot as plt
from picamera2 import Picamera2
import time
import os
import json
import serial
import time

is_processing = False

# (x1, y1) coordinates of top left corner, (x2, y2) coordinates of bottom right corner
def get_rectangle_center(x1, y1, x2, y2):
    cx = (x1 + x2) // 2 
    cy = (y1 + y2) // 2 
    return cx, cy

def draw_circle(x, y, frame):
    cv2.circle(frame, (x, y), 5, (0, 0, 255), -1)

def get_position_cm(x,y):
    cm_per_pixel = 0.08
    x_cm = x * cm_per_pixel
    y_cm = y * cm_per_pixel
    return x_cm, y_cm

def get_frame(image_path):
    # Charger l'image
    frame = cv2.imread(image_path)
    if frame is None:
        print("Erreur : Impossible de charger l'image.")
        return
    
    print("Image shape:", frame.shape)
    return frame

def rotate_photo_to_right(frame):
    rotated = cv2.rotate(frame, cv2.ROTATE_90_CLOCKWISE)
    return rotated

def rotate_photo_to_left(frame):
    rotated = cv2.rotate(frame, cv2.ROTATE_90_COUNTERCLOCKWISE)
    return rotated

def calculate_angle(line1, line2):
    """
    Calcule l'angle entre deux lignes en utilisant l'arctangente de leurs pentes.
    """
    x1, y1, x2, y2 = line1
    x3, y3, x4, y4 = line2

    # Calcul des pentes
    if x2 - x1 == 0:  # Cas d'une ligne verticale (référence)
        angle1 = 90
    else:
        angle1 = np.degrees(np.arctan2(y2 - y1, x2 - x1))

    if x4 - x3 == 0:
        angle2 = 90  # Ligne de référence est parfaitement verticale
    else:
        angle2 = np.degrees(np.arctan2(y4 - y3, x4 - x3))

    return angle1 - angle2  # Retourne la différence d'angle avec son signe

def save_data_json(angle, posx, posy):
     # Charger ou créer le fichier JSON
    try:
        with open("Data.json", "r") as json_file:
            data = json.load(json_file)  # Charger les données existantes
    except (FileNotFoundError, json.JSONDecodeError):
        data = {}  # Si le fichier n'existe pas ou est vide, on crée un nouvel objet
    
    # Mettre à jour les données avec le nouvel angle
    data["angle"] = round(angle, 2)  # Stocker l'angle avec 2 décimales
    #data.setdefault("position", {})  # Préparer la section "position" pour plus tard

    data["posx"] = round(posx, 2)
    data["posy"] = round(posy, 2)

    # Enregistrer les données mises à jour
    with open("Data.json", "w") as json_file:
        json.dump(data, json_file, indent=4)

def process(image_path):
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_left(initial_frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    cv2.imwrite("edges.jpg", edges)
    
    # Détection des contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00  # Stocker l'angle de la ligne détectée
    containers = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w,h) / float(max(w,h))
        area = w * h
        print(f"Contours :area ={area}")

        # Détection des lignes verticales inclinées avec une régression linéaire
        if aspect_ratio < 0.2 and h > 100:
            if h > max_line_height:
                max_line_height = h

                # Récupérer tous les points du contour pour mesurer son inclinaison
                points = contour.reshape(-1, 2)  # Conversion en liste de points (x, y)
                x_coords = points[:, 0]
                y_coords = points[:, 1]

                # Régression linéaire pour trouver l'orientation réelle de la ligne
                A = np.vstack([x_coords, np.ones(len(x_coords))]).T
                m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]  # Ajustement de droite y = mx + c

                # Calcul des points extrêmes (ligne détectée) pour couvrir toute la hauteur
                y1 = min(y_coords)
                y2 = max(y_coords)

                if abs(m) > 1e-6:  # Éviter la division par zéro
                    x1 = int((y1 - c) / m)  # Calculer x pour y1
                    x2 = int((y2 - c) / m)  # Calculer x pour y2
                else:
                    x1, x2 = np.mean(x_coords), np.mean(x_coords)  # Si la pente est proche de zéro, prendre une moyenne

                best_line = (x1, y1, x2, y2)  # Ligne inclinée détectée

                # Définir la ligne de référence verticale avec le même point de départ
                reference_line = (x1, y1, x1, y2)  # Ligne verticale pure

                # Calcul de l'angle d'inclinaison par rapport à cette ligne verticale
                inclination_angle = calculate_angle(best_line, reference_line)
            
        elif 0.5 <= aspect_ratio <= 1.2 and 2000 <area < 12000:  # Petit carré (conteneur)
            containers.append((x, y, w, h, area))
            print(f"x = {x}, y = {y}, w = {w}, h = {h}")

    output_classified = frame.copy()

    # Tracer la ligne inclinée détectée
    if best_line:
        x1, y1, x2, y2 = best_line
        cv2.line(output_classified, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Ligne rouge inclinée réelle
        cv2.line(output_classified, (x1, y1), (x1, y2), (255, 255, 0), 2)  # Ligne verticale en cyan
        print(f"Ligne détectée de ({x1}, {y1}) à ({x2}, {y2}) - Inclinaison réelle: {inclination_angle:.2f}°")

    # Dessiner les conteneurs en bleu et leurs centres en rouge
    posx = 0.00
    posy = 0.00
    if(bool(containers)):
        x, y, w, h, area = min(containers, key=lambda c: c[0])
        cv2.rectangle(output_classified, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cx, cy = get_rectangle_center(x, y, (x+w), (y+h))
        draw_circle(cx, cy, output_classified)
        posx, posy = get_position_cm(cx,cy)
        save_data_json(inclination_angle, posx, posy)
        print(f"Conteneur détecté - Surface: {area}")

    output_path = "output_final.jpg"
    cv2.imwrite(output_path, output_classified)
    global is_processing
    is_processing = False

    return bool(containers), posx, posy, inclination_angle

def process_track(image_path, initial_y):
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_left(initial_frame)

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    cv2.imwrite("edges.jpg", edges)
    
    # Détection des contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00  # Stocker l'angle de la ligne détectée
    containers = []

    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w,h) / float(max(w,h))
        area = w * h


        # Détection des lignes verticales inclinées avec une régression linéaire
        if aspect_ratio < 0.2 and h > 100:
            if h > max_line_height:
                max_line_height = h

                # Récupérer tous les points du contour pour mesurer son inclinaison
                points = contour.reshape(-1, 2)  # Conversion en liste de points (x, y)
                x_coords = points[:, 0]
                y_coords = points[:, 1]

                # Régression linéaire pour trouver l'orientation réelle de la ligne
                A = np.vstack([x_coords, np.ones(len(x_coords))]).T
                m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]  # Ajustement de droite y = mx + c

                # Calcul des points extrêmes (ligne détectée) pour couvrir toute la hauteur
                y1 = min(y_coords)
                y2 = max(y_coords)

                if abs(m) > 1e-6:  # Éviter la division par zéro
                    x1 = int((y1 - c) / m)  # Calculer x pour y1
                    x2 = int((y2 - c) / m)  # Calculer x pour y2
                else:
                    x1, x2 = np.mean(x_coords), np.mean(x_coords)  # Si la pente est proche de zéro, prendre une moyenne

                best_line = (x1, y1, x2, y2)  # Ligne inclinée détectée

                # Définir la ligne de référence verticale avec le même point de départ
                reference_line = (x1, y1, x1, y2)  # Ligne verticale pure

                # Calcul de l'angle d'inclinaison par rapport à cette ligne verticale
                inclination_angle = calculate_angle(best_line, reference_line)
            
        elif 0.5 <= aspect_ratio <= 1.2 and 2000 <area < 12000:  # Petit carré (conteneur)
            containers.append((x, y, w, h, area))
            print(f"x = {x}, y = {y}, w = {w}, h = {h}")

    output_classified = frame.copy()

    # Tracer la ligne inclinée détectée
    if best_line:
        x1, y1, x2, y2 = best_line
        cv2.line(output_classified, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Ligne rouge inclinée réelle
        cv2.line(output_classified, (x1, y1), (x1, y2), (255, 255, 0), 2)  # Ligne verticale en cyan
        print(f"Ligne détectée de ({x1}, {y1}) à ({x2}, {y2}) - Inclinaison réelle: {inclination_angle:.2f}°")

    # Dessiner les conteneurs en bleu et leurs centres en rouge
    posx = 0.00
    posy = 0.00
    if(bool(containers)):
        x, y, w, h, area = min(
            (c for c in containers if c[1] > initial_y),
            key=lambda c: c[0]
        )

        cv2.rectangle(output_classified, (x, y), (x + w, y + h), (255, 0, 0), 2)
        cx, cy = get_rectangle_center(x, y, (x+w), (y+h))
        draw_circle(cx, cy, output_classified)
        posx, posy = get_position_cm(cx,cy)
        save_data_json(inclination_angle, posx, posy)
        print(f"Conteneur détecté - Surface: {area}")

    output_path = "output_final.jpg"
    output_edges = "edges_final.jpg"
    cv2.imwrite(output_path, output_classified)
    cv2.imwrite(output_edges,edges)
    global is_processing
    is_processing = False

    return bool(containers), posx, posy, inclination_angle

def process_back(image_path):
    initial_frame = get_frame(image_path)
    frame = rotate_photo_to_right(initial_frame)

    height, width = frame.shape[:2]
    print(f"height : {height}, width : {width}")

    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    filtered = cv2.GaussianBlur(gray, (5, 5), cv2.BORDER_DEFAULT)
    edges = cv2.Canny(filtered, 30, 100)

    cv2.imwrite("edges.jpg", edges)
    
    # Détection des contours
    contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    best_line = None
    max_line_height = 0
    inclination_angle = 0.00  # Stocker l'angle de la ligne détectée
    zone_detected = False
    best_h = 0
    posx = 0.00
    posy = 0.00
    output_classified = frame.copy()
    for contour in contours:
        x, y, w, h = cv2.boundingRect(contour)
        aspect_ratio = min(w,h) / float(max(w,h))
        area = w * h

        # Détection des lignes verticales inclinées avec une régression linéaire
        if aspect_ratio < 0.2 and h > 100:
            if h > max_line_height:
                max_line_height = h

                # Récupérer tous les points du contour pour mesurer son inclinaison
                points = contour.reshape(-1, 2)  # Conversion en liste de points (x, y)
                x_coords = points[:, 0]
                y_coords = points[:, 1]

                # Régression linéaire pour trouver l'orientation réelle de la ligne
                A = np.vstack([x_coords, np.ones(len(x_coords))]).T
                m, c = np.linalg.lstsq(A, y_coords, rcond=None)[0]  # Ajustement de droite y = mx + c

                # Calcul des points extrêmes (ligne détectée) pour couvrir toute la hauteur
                y1 = min(y_coords)
                y2 = max(y_coords)

                if abs(m) > 1e-6:  # Éviter la division par zéro
                    x1 = int((y1 - c) / m)  # Calculer x pour y1
                    x2 = int((y2 - c) / m)  # Calculer x pour y2
                else:
                    x1, x2 = np.mean(x_coords), np.mean(x_coords)  # Si la pente est proche de zéro, prendre une moyenne

                best_line = (x1, y1, x2, y2)  # Ligne inclinée détectée
                best_h = h

                # Définir la ligne de référence verticale avec le même point de départ
                reference_line = (x1, y1, x1, y2)  # Ligne verticale pure

                # Calcul de l'angle d'inclinaison par rapport à cette ligne verticale
                inclination_angle = calculate_angle(best_line, reference_line)
        if 0.3 <= aspect_ratio <= 1.2 and 50000 <area :  # grand carré (zone)
            zone_detected = True
            cx, cy = get_rectangle_center(x, y, (x+w), (y+h))
            draw_circle(cx, cy, output_classified)
            posx, posy = get_position_cm(cx,cy)
            print("zone détectée")
    
    #output_classified = frame.copy()
    # Tracer la ligne inclinée détectée
    if best_line:
        x1, y1, x2, y2 = best_line
        cv2.line(output_classified, (x1, y1), (x2, y2), (0, 0, 255), 2)  # Ligne rouge inclinée réelle
        cv2.line(output_classified, (x1, y1), (x1, y2), (255, 255, 0), 2)  # Ligne verticale en cyan
        print(f"Ligne détectée de ({x1}, {y1}) à ({x2}, {y2}) - Inclinaison réelle: {inclination_angle:.2f}°")

        #if best_h < height:
        #    zone_detected = True

    output_path = "output_final.jpg"
    cv2.imwrite(output_path, output_classified)
    global is_processing
    is_processing = False

    print(f"Inclination angle: {inclination_angle}")

    return inclination_angle, zone_detected, posx, posy

def make_connection_esp():
    # Définir le port série (modifie si nécessaire)
    SERIAL_PORT = '/dev/ttyUSB0'  # Change selon ton port (ex: /dev/ttyACM0 ou COM5 sur Windows)
    BAUD_RATE = 115200  # Vitesse de communication

    # Attendre que le port série soit prêt
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
    time.sleep(2)  # Laisser l'ESP32 se stabiliser
    return ser

# Définir le port série (modifie si nécessaire)
SERIAL_PORT = '/dev/ttyUSB0'  # Change selon ton port (ex: /dev/ttyACM0 ou COM5 sur Windows)
BAUD_RATE = 115200  # Vitesse de communication

# Attendre que le port série soit prêt
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

def send_data_esp(x, y, angle, mode):
    data_to_send = f"positionX = {x} ; positionY = {y} ; angle = {angle} ; mode = {mode}\n"  # Format d'envoi
    ser.write(data_to_send.encode())  # Envoyer au port série
    print(f"Données envoyées : {data_to_send.strip()}")

    # Lire la réponse de l'ESP32 si disponible
    if ser.in_waiting > 0:
        response = ser.readline().decode('utf-8').strip()
        print(f"Réponse reçue de l'ESP32 : {response}")
    
    time.sleep(2)  # Envoyer toutes les 2 secondes

def start():
    #ser = make_connection_esp()

    # state 1 : on avance de la distance programmée constante
    # state 2 : on avance vers le conteneur détecté
    # state 3 : on recule vers la zone de dépôt
    
    state = 1
    distance_from_start = 0.00
    step_distance = 20.00
    step_distance_feedback = 10.00
    inclination_angle = 0.00
    posx = 0.00
    posy = 0.00
    is_first_step = False

    save_dir = './media/'
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    
    while True:
        # -------------------------------------------------
        # -------------------- State 1 --------------------
        # -------------------------------------------------
        if state == 1:
            send_data_esp(0.00, step_distance, inclination_angle, 'r')

            # Traiter
            filename = os.path.join(save_dir, f"photo.jpg")
            picam2.capture_file(filename)
            print(f"Captured {filename}")
            global is_processing
            is_processing = True
            is_containers, posx, posy, inclination_angle = process(filename)
            while(is_processing):
                continue
            print(is_containers, posx, posy, inclination_angle)

            # Si conteneurs détectés -> state 2
            if is_containers:
                state = 2

            time.sleep(1)
            # Sinon -> state 1

        # -------------------------------------------------
        # -------------------- State 2 --------------------
        # -------------------------------------------------
        elif state == 2:
            # Avancer de distance y jusqu'au conteneur
            # Avancer de distance x jusqu'au conteneur
            # Récupérer conteneur

            #distance_from_start += posy
            initial_y = posy

            while posy < 18 : #16.4 avant et 15.7
             # Marge d'erreur de 2.5 cm
                if (10<posy<14):
                    send_data_esp(0.00, 5, inclination_angle, 'r')
                else:
                    send_data_esp(0.00, step_distance_feedback, inclination_angle, 'r')
                # Traiter
                filename = os.path.join(save_dir, f"photo.jpg")
                picam2.capture_file(filename)
                print(f"Captured {filename}")
                is_processing = True
                is_containers, posx, posy, inclination_angle = process(filename)
                while(is_processing):
                    continue
                print(is_containers, posx, posy, inclination_angle)
                time.sleep(1)
            if (15.7 < posy < 22) :
                send_data_esp(abs(posx-4), 0.00, inclination_angle, 's')
                state = 3
                time.sleep(7)
            else:
                state = 1

        # -------------------------------------------------
        # -------------------- State 3 --------------------
        # -------------------------------------------------
        elif state == 3:
            # Reculer de distance y' jusqu'à zone de dépôt (divisé en plusieurs reculs pour l'asservissement)
            # Reculer de distance x' jusqu'à zone de dépôt (divisé en plusieurs reculs pour l'asservissement)
            # Déposer conteneur
            
            ## Traiter pour récupérer angle et detection de zone de depot
            filename = os.path.join(save_dir, f"photo.jpg")
            picam2.capture_file(filename)
            print(f"Captured {filename}")
            is_processing = True
            inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)
            while(is_processing):
                continue
            print(inclination_angle, zone_detected)

            is_first_step_back = True

            while zone_detected == False:
                if (is_first_step_back):
                    send_data_esp(0.00, 0.00, inclination_angle, 'r')
                    time.sleep(5)
                    send_data_esp(0.00, 0.00, inclination_angle, 'r')
                    is_first_step_back = False
                    time.sleep(1)
                else:
                    send_data_esp(0.00, -20, inclination_angle, 'r')
                
                time.sleep(1)

                ## Traiter pour récupérer angle et detection de zone de depot
                filename = os.path.join(save_dir, f"photo.jpg")
                picam2.capture_file(filename)
                print(f"Captured {filename}")
                is_processing = True
                inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)
                while(is_processing):
                    continue
                print(inclination_angle, zone_detected)
            print(f"Y ZONE : {y_zone}\n")
            print(f"X ZONE : {x_zone}\n")
            time.sleep(1.5)
            while y_zone < 25 : #16.4 avant
             # Marge d'erreur de 2.5 cm
                send_data_esp(0.00, -10, inclination_angle, 'r')
                time.sleep(1.5)
                filename = os.path.join(save_dir, f"photo.jpg")
                picam2.capture_file(filename)
                print(f"Captured {filename}")
                is_processing = True
                inclination_angle, zone_detected, x_zone, y_zone = process_back(filename)
                while(is_processing):
                    continue
                print(inclination_angle, zone_detected)
            
            time.sleep(5)
            #send_data_esp(0.00,0.0, 0.0, 'p')
            send_data_esp(31-abs(x_zone), 0.0, 0.0, 'p')
            time.sleep(10)

            # -> state 1 (si jamais il y a des conteneurs oubliés)*
            state = 1
            send_data_esp(0.00, 0.00, inclination_angle, 'r')
            time.sleep(5)
            send_data_esp(0.00, 0.00, inclination_angle, 'r')
        
        print("End of loop, state = ", state)

        

picam2 = Picamera2()
picam2.start()

#save_dir = './media/'
#if not os.path.exists(save_dir):
#    os.makedirs(save_dir)
#
#try:
#    filename = os.path.join(save_dir, f"photo.jpg")
#    picam2.capture_file(filename)
#    print(f"Captured {filename}")
#    is_processing = True
#    is_containers, posx, posy, inclination_angle = process(filename)
#    while(is_processing):
#        continue
#    print(is_containers, posx, posy, inclination_angle)
#except KeyboardInterrupt:
#    print("Image capture stopped.")
start()

picam2.stop()

# FIXME: 
# Cas où 2 conteneurs possèdent le même x
# Cas où 1 conteneur est détecté au plus petit X, 
# mais plus tard dans le mouvement, il détecte un autre à un x
# encore plus petit
