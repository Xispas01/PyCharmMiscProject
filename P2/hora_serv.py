import socket
from datetime import datetime

if __name__ == '__main__':
    # Crear un socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Obtener la dirección IP y el puerto del servidor
    server_address = ('localhost', 10000)
    # Enlazar el socket a la dirección y puerto del servidor
    udp_socket.bind(server_address)
    # Recibir un mensaje del cliente
    data, client = udp_socket.recvfrom(4096)
    print("Recibido del cliente:", data.decode())
    # Enviar una respuesta al cliente
    # Obtener la hora actual
    hora_actual = datetime.now().time()
    # Convertir la hora actual en un string con formato hh:mm:ss
    respuesta = hora_actual.strftime('%H:%M:%S').encode()
    #message = "Hola, cliente".encode()
    udp_socket.sendto(respuesta, client)
    # Cerrar el socket
    udp_socket.close()