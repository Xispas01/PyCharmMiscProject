# Importar la biblioteca de sockets
import socket
if __name__ == '__main__':
    # Creamos un objeto socket TCP
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Definimos el puerto y la dirección IP del servidor al que nos conectaremos
    puerto = 12345
    direccion_ip = "127.0.0.1"
    # Establecemos una conexión al servidor
    conexion.connect((direccion_ip, puerto))
    # Enviamos un mensaje al servidor
    message = "¡Hola, servidor!"
    conexion.send(message.encode())
    # Recibimos una respuesta del servidor
    respuesta = conexion.recv(1024)
    print("Respuesta recibida:", respuesta.decode())
    # Cerramos la conexión
    conexion.close()