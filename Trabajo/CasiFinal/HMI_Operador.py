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
ACTUAL_CONECTION = '$Planta/robots/+/conexion'

REDRAW_INTERVAL_MS = 50   # refresco del canvas cada 50 ms (20 fps)

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

        # Estado de los robots: { RobotID: { 'color', 'pos', 'target' } }
        # Acceso: hilo MQTT escribe, hilo Tkinter lee "” protegido con lock
        # La lista empieza completamente vacía. No se autogenera nada de forma local.
        self.robots_state = {}  # datos recibidos por MQTT
        self.robots_state_lock = threading.Lock()

        # Objetos canvas (IDs enteros): solo se leen/escriben desde hilo Tkinter
        self.robots_canvas = {}  # { RobotID: {'oval': id, 'rect': id, 'color': str} }

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
            print(f"[MQTT] Conectando a {MQBROKER}:{MQPORT} ")
        except Exception as e:
            print(f"[MQTT] No se pudo conectar al broker: {e}")

        self.root.after(REDRAW_INTERVAL_MS, self._update_position_on_canvas)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    # Callbacks MQTT
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Conectado al broker")
            # Escucha global de cualquier instanciación u objetivo de robot
            client.subscribe(TARGET_TOPICS)
            client.subscribe(ACTUAL_TOPICS)
            client.subscribe(ACTUAL_CONECTION)
        else:
            print(f"[MQTT] Error de conexión, código: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            #'$Planta/robots/+/target_pos'

            if len(topic_parts) < 4:
                return

            robot_id = topic_parts[2]
            subtopic = topic_parts[3]

            # Desconexion del robot: purgar estado y canvas de forma inmediata
            if subtopic == 'conexion':
                if msg.payload.decode().strip().lower() == 'false':
                    with self.robots_state_lock:
                        if robot_id in self.robots_state:
                            print("[HMI] Robot",robot_id[1], "Desconectado")
                            del self.robots_state[robot_id]
                    self.root.after(0, lambda rid=robot_id: self._eliminar_robot_canvas(rid))
                return  # Siempre "true" ignora / "false" ya fue procesado

            data = json.loads(msg.payload.decode())

            #Dibujar robots si existen
            with self.robots_state_lock:
                if robot_id not in self.robots_state:
                    if subtopic != 'position':  # Solo dar de alta desde posicion activa del robot
                        return

                    color = "#%02x%02x%02x" % (
                        random.randint(0, 255),
                        random.randint(0, 255),
                        random.randint(0, 255),
                    )
                    self.robots_state[robot_id] = {
                        'color': color,
                        'pos': {'x': data['x'], 'y': data['y']},
                        'target': {'x': -1, 'y': -1},  # Destino desconocido hasta recibir posicion con heading
                    }

                if subtopic == 'target_pos':
                    self.robots_state[robot_id]['target'] = {'x': data['x'], 'y': data['y']}
                elif subtopic == 'position':
                    self.robots_state[robot_id]['pos'] = {'x': data['x'], 'y': data['y']}
                    # Extraer destino del campo heading embebido en el mensaje de posicion
                    heading = data.get('heading')
                    if isinstance(heading, dict) and 'x' in heading and 'y' in heading:
                        self.robots_state[robot_id]['target'] = {'x': heading['x'], 'y': heading['y']}
                    else:
                        self.robots_state[robot_id]['target'] = {'x': -1, 'y': -1}

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[MQTT] Error al procesar {msg.topic}: {e}")

    def _update_position_on_canvas(self):
    #Acualización de las posicones en el canvas redibujando
        with self.robots_state_lock:
            state_snapshot = {
                rid: dict(data) for rid, data in self.robots_state.items()
            }

        size = ROBOT_SIZE
        h = size / 2

        for robot_id, state in state_snapshot.items():
            color = state['color']
            pos = state['pos']
            target = state['target']

            if robot_id not in self.robots_canvas:
                # Crear formas la primera vez (estamos en hilo Tkinter, es seguro)
                rect = self.canvas.create_rectangle(
                    target['x'] - h, target['y'] - h,
                    target['x'] + h, target['y'] + h,
                    outline=color, width=2
                )
                oval = self.canvas.create_oval(
                    pos['x'] - h, pos['y'] - h,
                    pos['x'] + h, pos['y'] + h,
                    fill=color
                )
                self.robots_canvas[robot_id] = {
                    'rect': rect,
                    'oval': oval,
                    'color': color,
                }
                print(f"[HMI] Robot {robot_id} registrado en canvas")

            # Actualizar posición del óvalo (robot real)
            oval = self.robots_canvas[robot_id]['oval']
            self.canvas.coords(
                oval,
                pos['x'] - h, pos['y'] - h,
                pos['x'] + h, pos['y'] + h,
            )

            # Actualizar posición del rectángulo (destino)
            rect = self.robots_canvas[robot_id]['rect']
            self.canvas.coords(
                rect,
                target['x'] - h, target['y'] - h,
                target['x'] + h, target['y'] + h,
            )

        # Reprogramar el siguiente ciclo
        self.root.after(REDRAW_INTERVAL_MS, self._update_position_on_canvas)

    def _eliminar_robot_canvas(self, robot_id):
        # Borra las formas geometricas del robot del canvas y limpia su entrada.
        if robot_id in self.robots_canvas:
            self.canvas.delete(self.robots_canvas[robot_id]['oval'])
            self.canvas.delete(self.robots_canvas[robot_id]['rect'])
            del self.robots_canvas[robot_id]
            print(f"[HMI] Robot {robot_id} eliminado del canvas")

    def start_simulation(self):
        self.start_button["state"] = "disabled"
        print("Simulación iniciada de forma pasiva.")


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