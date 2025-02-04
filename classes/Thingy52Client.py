import sys
import os
import socket
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import asyncio
from bleak import BleakClient, BLEDevice
from datetime import datetime
import struct
import onnxruntime as ort
from utils.UUIDs import TMS_RAW_DATA_UUID, TMS_CONF_UUID
from utils.utility import motion_characteristics, change_status, scan, find
import numpy as np


class Thingy52Client(BleakClient):

    def __init__(self, device: BLEDevice):
        super().__init__(device.address)
        self.mac_address = device.address

        # variabili per il modello AI
        self.model = ort.InferenceSession('training/CNN_60.onnx')
        self.classes = ["skiing", "still"]
        self.prediction = "None"

        # Data buffer
        self.buffer_size = 60
        self.data_buffer = []

        # Recording information
        self.recording_name = None

        # variabili per la connessione al telefono
        self.server_socket = None
        self.client_socket = None
        self.client_address = None
        self.host = '0.0.0.0'
        self.port = 12345

    # funzione di connessione al telefono
    def connect_to_phone(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(1)
        print(f"Listening for connections on {self.host}:{self.port}")
        self.client_socket, self.client_address = self.server_socket.accept()
        print(f"Connected to {self.client_address}")
        self.client_socket.setblocking(False)

    # funzione di connessione al Thingy52
    async def connect(self, **kwargs) -> bool:
        print(f"Connecting to {self.mac_address}")
        await super().connect(**kwargs)

        try:
            print(f"Connected to {self.mac_address}")
            # se si connette con successo, cambia il colore del LED
            await change_status(self, "connected")
            return True
        except Exception as e:
            print(f"Failed to connect to {self.address}: {e}")
            return False

    # funzione di disconnessione al Thingy52
    async def disconnect(self) -> bool:
        print(f"\nDisconnecting from {self.mac_address}")
        return await super().disconnect()

    # funzione per ricevere i dati IMU
    async def receive_inertial_data(self, sampling_frequency: int = 60):
        # Set the sampling frequency
        payload = motion_characteristics(motion_processing_unit_freq=sampling_frequency)
        await self.write_gatt_char(TMS_CONF_UUID, payload)
        # call per chiedere la trasmissione dei dati
        await self.start_notify(TMS_RAW_DATA_UUID, self.raw_data_callback)
        # Change the LED color to red, recording status
        await change_status(self, "recording")
        # loop che dura fino allo stop del programma
        try:
            while True:
                await asyncio.sleep(0.1)
        # in caso di errore / cancellazione
        except asyncio.CancelledError:
            await self.stop_notify(TMS_RAW_DATA_UUID)
            await self.disconnect()
            print("Stopped notification")
            self.client_socket.close()
            self.server_socket.close()
            print("stopped server")

    # cambia il file dove salva i dati
    def save_to(self, file_name):
        self.recording_name = f"{self.mac_address.replace(':', '-')}_{file_name}.csv"

    # Callbacks
    def raw_data_callback(self, sender, data):
        # Handle the incoming accelerometer data here
        receive_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        # Accelerometer
        acc_x = (struct.unpack('h', data[0:2])[0] * 1.0) / 2 ** 10
        acc_y = (struct.unpack('h', data[2:4])[0] * 1.0) / 2 ** 10
        acc_z = (struct.unpack('h', data[4:6])[0] * 1.0) / 2 ** 10

        # Gyroscope
        gyro_x = (struct.unpack('h', data[6:8])[0] * 1.0) / 2 ** 5
        gyro_y = (struct.unpack('h', data[8:10])[0] * 1.0) / 2 ** 5
        gyro_z = (struct.unpack('h', data[10:12])[0] * 1.0) / 2 ** 5

        # Compass
        comp_x = (struct.unpack('h', data[12:14])[0] * 1.0) / 2 ** 4
        comp_y = (struct.unpack('h', data[14:16])[0] * 1.0) / 2 ** 4
        comp_z = (struct.unpack('h', data[16:18])[0] * 1.0) / 2 ** 4

        # Save the data to a file
        # anche sta parte la posso fare solo con self. penso... uguale che self.prediction
        # se riceve un messaggio contenente il nome della registrazione:
        try:
            new_name = self.client_socket.recv(1024).decode('utf-8')
            new_name_bool = True
            print(f"\nnew command: {new_name}")
        except BlockingIOError:
            new_name_bool = False
        if new_name_bool:
            # cambia il file di salvataggio in quel nome
            self.save_to(new_name)
        # se il nome è valido (non è stop_recording)
        if self.recording_name != f"{self.mac_address.replace(':', '-')}_stop_recording.csv":
            # append al file l'ultima riga
            with open(f"training/data/{self.recording_name}", "a+") as file:
                file.write(f"{receive_time},{acc_x},{acc_y},{acc_z},{gyro_x},{gyro_y},{gyro_z}\n")

        # Update the data buffer
        if len(self.data_buffer) == self.buffer_size:
            input_data = np.array(self.data_buffer, dtype=np.float32).reshape(1, self.buffer_size, 6)
            input_ = self.model.get_inputs()[0].name
            cls_index = np.argmax(self.model.run(None, {input_: input_data})[0], axis=1)[0]
            self.prediction = self.classes[cls_index]
            self.data_buffer.clear()
        self.data_buffer.append([acc_x, acc_y, acc_z, gyro_x, gyro_y, gyro_z])

        # invia la previsione al telefono
        self.client_socket.sendall(self.prediction.encode('utf-8'))
        # stampa i valori
        print(f"\r{self.mac_address} | {receive_time} - Accelerometer: X={acc_x: 2.3f},"
              f" Y={acc_y: 2.3f}, ...Z={acc_z: 2.3f}, prediction: {self.prediction}", end="", flush=True)