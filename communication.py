import serial
import time

SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200

ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
time.sleep(2)

def send_data_esp(x, y, angle, mode):
    data_to_send = f"positionX = {x} ; positionY = {y} ; angle = {angle} ; mode = {mode}\n"
    ser.write(data_to_send.encode())
    print("Données envoyées :", data_to_send.strip())

    if ser.in_waiting > 0:
        response = ser.readline().decode().strip()
        print("Réponse ESP32 :", response)

    time.sleep(2)
