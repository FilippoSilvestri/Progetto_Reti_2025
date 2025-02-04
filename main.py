from classes.Thingy52Client import Thingy52Client
from utils.utility import scan, find
import asyncio


async def main():
    # indirizzo MAC del Thingy52
    my_thingy_addresses = ["DC:82:24:3D:29:80"]
    # scannerizzazione dei dispositivi disponibili
    discovered_devices = await scan()
    # lista che filtra tra i dispositivi disponibili e quelli conosciuti
    my_devices = find(discovered_devices, my_thingy_addresses)

    # creazione classe
    thingy52 = Thingy52Client(my_devices[0])
    # connessione WiFi al telefono
    thingy52.connect_to_phone()
    # connessione BLE al Thingy52
    await thingy52.connect()
    thingy52.save_to("stop_recording")
    # call per ricevere i dati IMU
    await thingy52.receive_inertial_data()

if __name__ == '__main__':
    asyncio.run(main())