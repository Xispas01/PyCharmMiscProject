import socket
import threading

import tkinter as tk
from sys import exception
from tkinter import scrolledtext

import pickle
import time
import json

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client

'''
REVISA LA PARTE DE TCP PARA QUE AL ENVIAR MENSAJES 
SE PUEDA ENVIAR POR MQTT EL TARGET A LOS DEMAS PROCESOS

YA TIENES EL CLIENTE MQTT (SE LLAMA "MQTTC") Y ES ACCESIBLE
DESDE UDP Y DEBERIA SERLO POR TCP

SE ME OCURRE QUE LA CUANDO SE LE CONECTEN SOLICITE UN GET_STATUS
Y ALMACENE IP JUNTO CON LA ID DEL ROBOT TOCARA DES PICKLE


'''
# Estado global
dicc_conexiones_establecidas = {'None': None}
dicc_nombres = {'None': None}  # Nuevo mapa para la Interfaz (ID -> Nombre legible)
mapa_robottcp = {}  # Mapa inverso: RobotID -> direccion_puerto

UDPPORT = 9001
UDPHOST = 'localhost'

TCPPORT = 12345
TCPHOST = 'localhost'

MQBROKER = "localhost"
MQPORT = 1883

# Referencias a widgets (se asignan en main())
ventana = None
texto_mensajes = None
opcion_seleccionada = None
desplegable_seleccion_conexion = None
entry_puerto_servidor = None
entry_ip_destino = None
entry_puerto_destino = None
entry_mensaje = None


# Metodos de Utilidades
def mostrar_mensaje(msg: str):
    #Añade una lí­nea al área de texto de forma thread-safe.

    def _insert():
        texto_mensajes.config(state=tk.NORMAL)
        texto_mensajes.insert(tk.END, msg + '\n')
        texto_mensajes.see(tk.END)
        texto_mensajes.config(state=tk.DISABLED)

    ventana.after(0, _insert)


def actualizar_opciones_desplegable(): #Caso de conexión sin nombre
    #Reconstruye el menú desplegable con las conexiones actuales

    def _update():
        desplegable_seleccion_conexion['menu'].delete(0, 'end')
        for opcion in list(dicc_conexiones_establecidas.keys()):
            etiqueta = dicc_nombres.get(opcion, opcion)

            desplegable_seleccion_conexion['menu'].add_command(
                label=etiqueta,
                command=tk._setit(opcion_seleccionada, etiqueta)
            )
    #print('valores inversos: ',mapa_robottcp)

    if ventana:
        ventana.after(0, _update)

# Lógica de red TCP
def hilo_recibir_mensajes(conexion: socket.socket, direccion_puerto: str):
    #Variables de filtro de mensajes
    ultimo_msg = None
    ultimo_remitente = None

    # Bucle de recepción continua para una conexión activa.
    while True:
        try:
            datos = conexion.recv(1024)
            if not datos:
                mostrar_mensaje(f"Conexión {direccion_puerto} cerrada por el remoto.")
                break

            # SOLUCIÓN AL PROBLEMA 1: Sistema de identificación robusto en cascada de 3 capas
            r_id = None

            # Capa A: Intento de deserialización por Pickle
            try:
                obj = pickle.loads(datos)
                if isinstance(obj, dict) and 'robot_id' in obj:
                    r_id = obj['robot_id']
            except Exception:
                pass

            # Capa B: Intento por JSON si viene estructurado como string
            if not r_id:
                try:
                    msg_str = datos.decode('utf-8', errors='ignore').strip()
                    if msg_str.startswith('{'):
                        obj = json.loads(msg_str)
                        if isinstance(obj, dict) and 'robot_id' in obj:
                            r_id = obj['robot_id']
                except Exception:
                    pass

            # Capa C: Escaneo heurí­stico en Texto Plano (busca R1, R2, R3 en el mensaje)
            if not r_id:
                try:
                    msg_str = datos.decode('utf-8', errors='ignore')
                    for posible in ["R1", "R2", "R3"]:
                        if posible in msg_str:
                            r_id = posible
                            break
                except Exception:
                    pass

            # Si se descubrió la identidad del robot por cualquier canal, actualizamos la GUI
            if r_id:
                ip = direccion_puerto
                nombre_amigable = f"robot {r_id}({ip})"
                print("Caso robot",nombre_amigable,"\n")

                if dicc_nombres.get(direccion_puerto) != nombre_amigable:
                    dicc_nombres[direccion_puerto] = nombre_amigable
                    mapa_robottcp[r_id] = direccion_puerto

                    mostrar_mensaje(f"[{r_id}] Registrado como {nombre_amigable}")
                    actualizar_opciones_desplegable()

                    # Forzar visualización inmediata en el campo de selección
                    ventana.after(0, lambda name=nombre_amigable: opcion_seleccionada.set(name))

                # Si el paquete era un pickle puro de estado interno, evitamos imprimir binario ruidoso en consola
                try:
                    pickle.loads(datos)
                    continue
                except Exception:
                    pass

            # Procesar y mostrar mensajes de texto estándar recibidos
            msg_str = datos.decode('utf-8', errors='replace')
            remitente = dicc_nombres.get(direccion_puerto, direccion_puerto)
            mostrar_mensaje(f"Mensaje de {remitente}: {msg_str}")

        except socket.error:
            mostrar_mensaje(f"Error en conexión {direccion_puerto}. Conexión cerrada.")
            break

    # Limpieza limpia de diccionarios tras desconexión
    if direccion_puerto in dicc_conexiones_establecidas:
        del dicc_conexiones_establecidas[direccion_puerto]
    if direccion_puerto in dicc_nombres:
        del dicc_nombres[direccion_puerto]

    for rid, dp in list(mapa_robottcp.items()):
        if dp == direccion_puerto:
            del mapa_robottcp[rid]

    actualizar_opciones_desplegable()
    ventana.after(0, lambda: opcion_seleccionada.set('Conexiones'))

def hilo_servidor():
    #Hilo principal del servidor: acepta conexiones indefinidamente.
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        servidor.bind((TCPHOST, TCPPORT))
        servidor.listen(5)
        mostrar_mensaje(f"Esperando aceptar conexiones por {TCPPORT}")

        while True:
            try:
                conexion, direccion = servidor.accept()
                dir_puerto = f"{direccion[0]}:{direccion[1]}"
                mostrar_mensaje(f"Nueva conexión {dir_puerto} establecida")
                dicc_conexiones_establecidas[dir_puerto] = conexion
                dicc_nombres[dir_puerto] = dir_puerto

                # Auto-seleccionar la nueva conexión en la interfaz gráfica
                ventana.after(0, lambda dp=dir_puerto: opcion_seleccionada.set(dp))
                actualizar_opciones_desplegable()

                t = threading.Thread(
                    target=hilo_recibir_mensajes,
                    args=(conexion, dir_puerto),
                    daemon=True
                )
                t.start()
                # Solicitar identificacion al robot recien conectado para poblar el menu
                try:
                    conexion.sendall(b"GET_STATUS")
                except socket.error as e:
                    mostrar_mensaje(f"! No se pudo solicitar identificacion a {dir_puerto}: {e}")
            except socket.error as e:
                mostrar_mensaje(f"! Error de socket: {e}")
                break

    except Exception as e:
        mostrar_mensaje(f"! Error al iniciar servidor: {e}")
    finally:
        servidor.close()

# Comportamientos de botones

def iniciar_servidor():
    t = threading.Thread(target=hilo_servidor, args=(), daemon=True)
    t.start()

def conectar(): #Funcion conservada para conectar manualmente si se requiere.
    ip = entry_ip_destino.get().strip()
    puerto_str = entry_puerto_destino.get().strip()
    if not ip or not puerto_str.isdigit():
        return
    puerto = int(puerto_str)
    dir_puerto = f"{ip}:{puerto}"

    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        conexion.connect((ip, puerto))
        dicc_conexiones_establecidas[dir_puerto] = conexion
        dicc_nombres[dir_puerto] = dir_puerto #<--Aquí­ es donde hay que establecer el nombre amigable

        actualizar_opciones_desplegable()
        t = threading.Thread(target=hilo_recibir_mensajes, args=(conexion, dir_puerto), daemon=True)
        t.start()
        conexion.sendall(b"GET_STATUS\n")
    except socket.error as e:
        mostrar_mensaje(f"! Error al conectar con {dir_puerto}: {e}")


def enviar_mensaje(event=None):  # event=None permite que sea llamado tanto por el botón como por la tecla Enter
    seleccion = opcion_seleccionada.get()
    dir_puerto = None

    # Buscar el puerto subyacente según el nombre amigable seleccionado
    for dp, nombre in dicc_nombres.items():
        if nombre == seleccion or dp == seleccion:
            dir_puerto = dp
            break

    if not dir_puerto or dir_puerto in ('Conexiones', 'None', ''):
        mostrar_mensaje("Selecciona una conexión válida.")
        return

    conexion = dicc_conexiones_establecidas.get(dir_puerto)
    mensaje = entry_mensaje.get()
    if not mensaje.strip() or not conexion:
        return

    # Si se enví­a el target desde GUI, replicarlo en MQTT
    if mensaje.startswith('SET_TARGET'):
        data = mensaje.split(' ')
        if len(data) >= 3:
            try:
                x, y = int(data[1]), int(data[2])
                r_id = next((rid for rid, p in mapa_robottcp.items() if p == dir_puerto), None)
                # Extractor de emergencia si el mapa inverso aún se está construyendo
                if not r_id and "robot " in seleccion:
                    try:
                        r_id = seleccion.split(" ")[1].split("(")[0]
                    except Exception:
                        pass

                if r_id:
                    payload = json.dumps({"x": x, "y": y, "ts": time.time(), "source": "console"})
                    MQTTC.publish(f"$Planta/robots/{r_id}/target_pos", payload, qos=1, retain=True)
            except ValueError:
                pass

    try:
        conexion.sendall(mensaje.encode('utf-8'))
        mostrar_mensaje(f"Enviado a {dicc_nombres.get(dir_puerto, dir_puerto)}: {mensaje}")
        entry_mensaje.delete(0, tk.END)
    except socket.error as e:
        mostrar_mensaje(f"! Error al enviar: {e}")

def cerrar_conexion():
    dir_puerto = opcion_seleccionada.get()
    if dir_puerto in ('Conexiones', 'None', ''):
        mostrar_mensaje("Selecciona una conexión.")
        return
    conexion = dicc_conexiones_establecidas.get(dir_puerto)
    if conexion is not None:
        try:
            conexion.close()
        except Exception:
            pass
        del dicc_conexiones_establecidas[dir_puerto]
        mostrar_mensaje(f"Cerrada conexión {dir_puerto} y finalizado hilo")
        actualizar_opciones_desplegable()
        opcion_seleccionada.set('Conexiones')

# Receptor Global MQTT (Ignition -> Consola TCP -> Robot)
def on_mqtt_coordinador(client, userdata, msg):
    try:
        topic_parts = msg.topic.split('/')
        # topic: $Planta/robots/R1/target_pos
        if len(topic_parts) >= 4 and topic_parts[3] == 'target_pos':
            r_id = topic_parts[2]
            data = json.loads(msg.payload.decode())
            # Ignorar targets originados en esta misma consola (ya enviados directamente por TCP)
            if data.get('source') == 'console':
                return
            x, y = data.get('x'), data.get('y')

            # Redirigir el target por la conexión TCP especí­fica del Robot
            dir_puerto = mapa_robottcp.get(r_id)
            if dir_puerto:
                conn = dicc_conexiones_establecidas.get(dir_puerto)
                if conn:
                    comand = f"SET_TARGET {x} {y}\n"
                    conn.sendall(comand.encode('utf-8')) #Garantizar que no haya errores de codificación luego en pickel
                    mostrar_mensaje(f"[OPC] Ignition ordenó mover a {r_id}. Comando enviado.")
    except Exception as e:
        pass

def hilo_UDP():
    # Crear un socket UDP
    udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Obtener la dirección IP y el puerto del servidor
    server_address = (UDPHOST, UDPPORT)
    # Enlazar el socket a la dirección IP y el puerto del servidor
    udp_socket.bind(server_address)
    MARGEN = 5
    udp_socket.settimeout(MARGEN)
    WatchList = {}
    while True:
        hora_actual = time.time()
        for Robot in WatchList:
            if WatchList[Robot]['status'] != 'OFFLINE' and WatchList[Robot]['ts'] < hora_actual - MARGEN:
                print(f"[UDP] Robot {Robot}: Inactivo")
                WatchList[Robot]['status'] = 'OFFLINE'
                MQTTC.publish(f"$Planta/robots/{Robot}/conexion", "false") # Corrección a JSON nativo

        try:
            # Recibir los datos a través del socket
            data, client_address = udp_socket.recvfrom(4096)
            # Deserializar los datos utilizando pickle.loads()
            data_deserialized = pickle.loads(data)
            # Imprimir los datos deserializados
            print("[UDP] ", data_deserialized)
            MQTTC.publish(f"$Planta/robots/{data_deserialized["robot_id"]}/conexion", f"{True}")
            WatchList[data_deserialized["robot_id"]] = data_deserialized

        except socket.timeout:
            # Si el servidor no responde en 5 segundos, se imprime un mensaje
            print("[UDP] Ningun robot envia datos en 5 segundos")
        except Exception: #Cierra el programa si el error no es tiemout.
            print("Error: ",str(exception().__traceback__),"\n")
            break
    # Cerrar el socket
    udp_socket.close()


# Construcción de la interfaz
def main():
    global ventana, texto_mensajes, opcion_seleccionada, desplegable_seleccion_conexion
    global entry_puerto_servidor, entry_ip_destino, entry_puerto_destino, entry_mensaje

    iniciar_servidor()

    ventana = tk.Tk()
    ventana.title("Servidor TCP Maestro ReSiDiCo")
    ventana.resizable(False, False)

    font_label = ('Helvetica', 10)
    font_bold = ('Helvetica', 10, 'bold')
    font_btn = ('Helvetica', 10)
    PAD = dict(padx=8, pady=3)

    tk.Frame(ventana, height=4, bd=1, relief=tk.SUNKEN).grid(row=0, column=0, columnspan=3, sticky='ew')

    texto_mensajes = scrolledtext.ScrolledText(
        ventana, width=58, height=14, state=tk.DISABLED,
        font=('Courier', 9), wrap=tk.WORD
    )
    texto_mensajes.grid(row=10, column=0, columnspan=3, padx=8, pady=6)

    tk.Frame(ventana, height=4, bd=1, relief=tk.SUNKEN).grid(row=11, column=0, columnspan=3, sticky='ew')

    tk.Label(ventana, text="OPERACIONES CON CONEXIÓN", font=font_bold).grid(row=12, column=0, columnspan=3, pady=(6, 2))

    tk.Label(ventana, text="Seleccionar conexión:", font=font_label).grid(row=13, column=0, sticky='e', **PAD)

    opcion_seleccionada = tk.StringVar()
    desplegable_seleccion_conexion = tk.OptionMenu(ventana, opcion_seleccionada, None)
    desplegable_seleccion_conexion.config(font=font_label, width=25)
    desplegable_seleccion_conexion.grid(row=13, column=1, sticky='w', **PAD)

    tk.Label(ventana, text="Mensaje:", font=font_label).grid(row=14, column=0, sticky='e', **PAD)
    entry_mensaje = tk.Entry(ventana, width=32)
    entry_mensaje.grid(row=14, column=1, columnspan=2, sticky='w', **PAD)
    entry_mensaje.bind('<Return>', enviar_mensaje)

    tk.Button(ventana, text="Enviar mensaje", font=font_btn, width=16, command=enviar_mensaje).grid(row=15, column=0,
                                                                                                    columnspan=3,
                                                                                                    pady=4)
    tk.Button(ventana, text="Cerrar conexión", font=font_btn, width=16, command=cerrar_conexion).grid(row=16, column=0,
                                                                                                      columnspan=3,
                                                                                                      pady=(0, 8))

    actualizar_opciones_desplegable()
    ventana.mainloop()

if __name__ == '__main__':
    # Inicialización del MQTT Cliente
    MQTTC = Client(client_id="UDP-TCP_OPC")
    MQTTC.on_message = on_mqtt_coordinador
    MQTTC.connect(MQBROKER, MQPORT)

    # Requisito: El coordinador debe escuchar targets para mandarlos por TCP
    MQTTC.subscribe("$Planta/robots/+/target_pos")
    MQTTC.loop_start()

    tTCP = threading.Thread(name='TCPComands', target=main, args=())
    tUPD = threading.Thread(name='UDPHB', target=hilo_UDP, args=())

    tTCP.start()
    tUPD.start()

    tUPD.join()
    tTCP.join()
