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
    while True:
        # Serializar los datos utilizando pickle.dumps()
        hora_actual = time.time()
        data_serialized = pickle.dumps({ 'robot_id': "R1", 'seq': 142, 'timestamp': hora_actual, 'battery': f"{100.00}" })
        # Enviar los datos serializados a través del socket
        udp_socket.sendto(data_serialized, server_address)
    # Cerrar el socket
    udp_socket.close()