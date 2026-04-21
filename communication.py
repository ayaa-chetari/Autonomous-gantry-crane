import serial
import time

class ESP32Communication:
    def __init__(self, port='/dev/ttyUSB0', baudrate=115200):
        self.ser = serial.Serial(port, baudrate, timeout=1)
        time.sleep(2)

    def send(self, x, y, angle, mode):
        data = f"positionX={x};positionY={y};angle={angle};mode={mode}\n"
        self.ser.write(data.encode())
        print(f"[SEND] {data.strip()}")

        if self.ser.in_waiting > 0:
            response = self.ser.readline().decode().strip()
            print(f"[ESP32] {response}")

        time.sleep(1)
