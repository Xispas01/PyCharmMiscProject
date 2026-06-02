#!/usr/bin/env python
# coding: utf-8
import random

import paho.mqtt.client as MQTTC
import json
import tkinter as tk
import threading
import time
from json import JSONEncoder
import pickle
import sys

MQBROKER = "localhost"
MQPORT = 1883

# Constantes globales
WINDOW_SIZE = 50
ROBOT_SIZE = 10

# Se gestiona de manera totalmente dinámica leyendo del servidor MQTT
TARGET_TOPICS = '$Planta/robots/+/target_pos'
ACTUAL_TOPICS = '$Planta/robots/+/position'

# Aplicación principal
class RobotSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Robots")

        # Canvas
        self.canvas = tk.Canvas(
            self.root,
            width=ROBOT_SIZE * WINDOW_SIZE,
            height=ROBOT_SIZE * WINDOW_SIZE,
            bg="#FFFFFF"
        )
        self.canvas.pack()

        # Botón
        self.start_button = tk.Button(
            self.root,
            text="Iniciar Simulación",
            command=self.start_simulation
        )
        self.start_button.pack(pady=10)

        # La lista empieza completamente vacía. No se autogenera nada de forma local.
        self.robots = {}

        # Cliente MQTT
        self.mqtt_client = MQTTC.Client()
        self.mqtt_client.user_data_set(self)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        try:
            self.mqtt_client.connect(MQBROKER, MQPORT, 60)
            mqtt_thread = threading.Thread(
                target=self.mqtt_client.loop_forever,
                daemon=True
            )
            mqtt_thread.start()
            print(f"[MQTT] Conectando a {MQBROKER}:{MQPORT}…")
        except Exception as e:
            print(f"[MQTT] No se pudo conectar al broker: {e}")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # Callbacks MQTT
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Conectado al broker")
            # Escucha global de cualquier instanciación u objetivo de robot
            client.subscribe(TARGET_TOPICS)
            client.subscribe(ACTUAL_TOPICS)
        else:
            print(f"[MQTT] Error de conexión, código: {rc}")

    def update_position_on_canvas(self,shape,pos,size):
        self.canvas.coords(
            shape,  # ID entero del óvalo
            pos['x'] - size/2,
            pos['y'] - size/2,
            pos['x'] + size/2,
            pos['y'] + size/2
        )

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            #'$Planta/robots/+/target_pos'
            data = json.loads(msg.payload.decode())
            RobotID = topic_parts[2]

            if RobotID not in self.robots:
                ge = "#"
                de = ("%02x" % random.randint(0, 255))
                re = ("%02x" % random.randint(0, 255))
                we = ("%02x" % random.randint(0, 255))
                color = ge + de + re + we

                size = ROBOT_SIZE
                target = self.canvas.create_rectangle(data['x'] - size/2, data['y'] - size/2,data['x'] + size/2, data['y'] + size/2, fill=color)
                robot = self.canvas.create_oval(data['x'] - size/2, data['y'] - size/2,data['x'] + size/2, data['y'] + size/2, fill=color)
                self.robots[RobotID]={'color':color,'size':size,'robot':robot,'target':target}

            size = self.robots[RobotID]['size']
            robot = self.robots[RobotID]['robot']
            target = self.robots[RobotID]['target']

            if topic_parts[3]=='target_pos':
                #draw OBJ Color self.robots[RobotID]
                self.update_position_on_canvas(target,data,size)
            elif topic_parts[3]=='position':
                #draw POS Color self.robots[RobotID]
                self.update_position_on_canvas(robot,data,size)


        except (json.JSONDecodeError, KeyError) as e:
            print(f"[MQTT] Error al procesar mensaje de {msg.topic}: {e}")

    def start_simulation(self):
        self.start_button["state"] = "disabled"
        print("Simulación iniciada de forma pasiva. Esperando altas y bajas desde el servidor MQTT…")


    def on_closing(self):
        try:
            self.mqtt_client.disconnect()
        except Exception:
            pass
        self.root.destroy()


# Punto de entrada
root = tk.Tk()
app = RobotSimulatorApp(root)
root.mainloop()