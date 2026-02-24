#Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza

import socket
if __name__ == '__main__':
    # Crear un socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Obtener la dirección IP y el puerto del servidor
    server_address = ('localhost', 10000)
    udp_socket.settimeout(5)
    try:
        # Enviar un mensaje al servidor
        message = "Hola, servidor".encode()
        udp_socket.sendto(message, server_address)
        # Recibir una respuesta del servidor
        data, server = udp_socket.recvfrom(4096)
        print("Recibido del servidor:", data.decode())
    except socket.timeout:
        # Si el servidor no responde en 5 segundos, se imprime un mensaje
        print("El servidor no ha respondido en 5 segundos")
    # Cerrar el socket
    udp_socket.close()