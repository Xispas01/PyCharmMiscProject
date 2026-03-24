# Importar la biblioteca de sockets
import socket
if __name__ == '__main__':
    # Creamos un objeto socket TCP
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Definimos el puerto y la dirección IP en la que el servidor escuchará
    puerto = 12345
    direccion_ip = "127.0.0.1"
    # Enlazamos el objeto socket al puerto y dirección IP
    servidor.bind((direccion_ip, puerto))
    # Ponemos el servidor en modo escucha para aceptar conexiones entrantes
    servidor.listen(1)
    print("Esperando conexiones entrantes...")
    # Aceptamos una conexión entrante
    conexion, direccion = servidor.accept()
    print("Conexión establecida desde", direccion)
    # Recibimos datos del cliente
    datos_recibidos = conexion.recv(1024)
    print("Datos recibidos:", datos_recibidos.decode())
    # Enviamos una respuesta al cliente
    respuesta = "¡Hola, cliente!"
    conexion.send(respuesta.encode())
    # Cerramos la conexión aceptada y el servidor
    conexion.close()
    servidor.close()