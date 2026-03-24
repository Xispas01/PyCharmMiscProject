# Importar la biblioteca de sockets
import socket
import pickle

if __name__ == '__main__':
    # Creamos un objeto socket TCP
    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Definimos el puerto y la dirección IP del servidor al que nos conectaremos
    puerto = 12345
    direccion_ip = "127.0.0.1"

    # Establecer timeout para la conexión
    conexion.settimeout(5)
    # Conectar con el host
    try:
        conexion.connect((direccion_ip, puerto))
    except socket.timeout:
        print("La conexión ha expirado")
    except socket.error as err:
        print(f"Error al conectar: {err}")
    else:
        # Enviamos un datos al servidor
        # Datos a enviar (una lista de números)
        data = [1, 2, 3, 4, 5]
        # Serializar los datos utilizando pickle.dumps()
        data_serialized = pickle.dumps(data)
        conexion.sendall(data_serialized)
        # Establecer timeout para el mensaje
        conexion.settimeout(10)
        # Recibir datos
        try:
            respuesta = conexion.recv(1024)
            print(f"Datos recibidos: {respuesta}")
        except socket.timeout:
            print("La recepción de datos ha expirado")
        except socket.error as err:
            print(f"Error al recibir datos: {err}")
        else:
            print("Respuesta recibida:", respuesta.decode())

        # Cerramos la conexión
        conexion.close()