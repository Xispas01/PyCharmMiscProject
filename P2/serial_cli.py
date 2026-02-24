import socket
import pickle

if __name__ == '__main__':
    # Crear un socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Obtener la dirección IP y el puerto del servidor
    server_address = ('localhost', 4096)
    # Datos a enviar (una lista de números)
    data = [4, 3, 5, 1, 2]
    udp_socket.settimeout(5)
    try:
        # Serializar los datos utilizando pickle.dumps()
        data_serialized = pickle.dumps(data)
        # Enviar los datos serializados a través del socket
        udp_socket.sendto(data_serialized, server_address)
    except socket.timeout:
        # Si el servidor no responde en 5 segundos, se imprime un mensaje
        print("El servidor no ha respondido en 5 segundos")
    # Cerrar el socket
    udp_socket.close()