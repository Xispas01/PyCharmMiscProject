# Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza

import socket
import pickle

if __name__ == '__main__':
    # Crear un socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Obtener la dirección IP y el puerto del servidor
    server_address = ('localhost', 4096)
    # Enlazar el socket a la dirección IP y el puerto del servidor
    udp_socket.bind(server_address)
    # Recibir los datos a través del socket
    data, client_address = udp_socket.recvfrom(4096)
    # Deserializar los datos utilizando pickle.loads()
    data_deserialized = pickle.loads(data)
    # Imprimir los datos deserializados
    print("Datos recibidos:", data_deserialized)
    # Cerrar el socket
    udp_socket.close()