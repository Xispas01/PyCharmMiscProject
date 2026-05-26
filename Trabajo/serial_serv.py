# Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza

import socket
import pickle
import time

if __name__ == '__main__':
    # Crear un socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Obtener la dirección IP y el puerto del servidor
    server_address = ('localhost', 9001)
    # Enlazar el socket a la dirección IP y el puerto del servidor
    udp_socket.bind(server_address)
    MARGEN = 5
    udp_socket.settimeout(MARGEN)
    WatchList = {}
    while True:
        hora_actual = time.time()
        for Robot in WatchList:
            if WatchList[Robot] < hora_actual - MARGEN:
                print(f"Robot {Robot}: Inactivo")
        try:
            # Recibir los datos a través del socket
            data, client_address = udp_socket.recvfrom(4096)
            # Deserializar los datos utilizando pickle.loads()
            data_deserialized = pickle.loads(data)
            WatchList[data_deserialized["robot_id"]]=data_deserialized["timestamp"]
            # Imprimir los datos deserializados
        except socket.timeout:
            # Si el servidor no responde en 5 segundos, se imprime un mensaje
            print("Ningun robot envia datos en 5 segundos")
    # Cerrar el socket
    udp_socket.close()