# Importar la biblioteca de sockets
import socket
from datetime import datetime
from time import sleep
import pickle
from warnings import catch_warnings
import threading
import cv2

Work = True

def showIMG(imgArray):
    cv2.imshow("Cat S",imgArray)
    cv2.waitKey(0)

def ServiceConection(conexion):
    # Recibimos datos del cliente

    # Recibir datos utilizando recv()
    dataSize = pickle.loads(conexion.recv(1024))
    datos_recibidos = b''
    while datos_recibidos.__sizeof__() != dataSize:
        data = conexion.recv(1024)
        print("actual Data size:", datos_recibidos.__sizeof__())
        print("objective Data size:", dataSize)
        if not data:
            break
        datos_recibidos += data

    data_deserialized = pickle.loads(datos_recibidos)

    print("Datos recibidos:", data_deserialized)
    # print("antes de send")
    try:
        if data_deserialized == "CERRAR":
            Work = False
            respuesta = "¡Cerrando Servidor!"
        elif data_deserialized == "HORA":
            # Obtener la hora actual
            hora_actual = datetime.now().time()
            # Convertir la hora actual en un string con formato hh:mm:ss
            respuesta = "Hora actual: " + hora_actual.strftime('%H:%M:%S')
        else:
            # Enviamos una respuesta al cliente
            respuesta = "¡Hola, cliente!"
        conexion.send(respuesta.encode())
    except ValueError:
        t = threading.Thread(target=showIMG, args=(data_deserialized,))
        t.start()
        # Enviamos una respuesta al cliente
        respuesta = "Array Recieved"
        conexion.send(respuesta.encode())

    # Cerramos la conexión aceptada y el servidor
    conexion.close()

if __name__ == '__main__':
    # Creamos un objeto socket TCP
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # Definimos el puerto y la dirección IP en la que el servidor escuchará
    puerto = 12345
    direccion_ip = "127.0.0.1"
    # Enlazamos el objeto socket al puerto y dirección IP
    servidor.bind((direccion_ip, puerto))
    while Work:
        # Ponemos el servidor en modo escucha para aceptar conexiones entrantes
        servidor.listen(1)
        print("Esperando conexiones entrantes...")

        # Aceptamos una conexión entrante
        conexion, direccion = servidor.accept()
        print("Conexión establecida desde", direccion)

        servicio = threading.Thread(target=ServiceConection, args=(conexion,))
        servicio.start()

    servidor.close()