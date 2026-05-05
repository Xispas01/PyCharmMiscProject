#!/usr/bin/env python
# coding: utf-8
from json import JSONEncoder

import paho.mqtt.client as MQTTC
import json
import tkinter as tk
import threading
import time
import pickle
import sys

BROKER = "localhost"
PORT = 1883


# Constantes globales
WINDOW_SIZE = 50
ROBOT_SIZE  = 10

TARGET_TOPICS = {
    "Robot1/target_pos": "Robot1",
    "Robot2/target_pos": "Robot2",
    "Robot3/target_pos": "Robot3",
}

# Broker interno (pub/sub entre hilos)
class MessageBroker:
    def __init__(self):
        self._lock = threading.Lock()
        self._subscribers: dict[str, list] = {}

    def subscribe(self, topic: str, callback):
        with self._lock:
            self._subscribers.setdefault(topic, []).append(callback)
        print(f"[Broker] Suscripción registrada -> topic '{topic}'")

    def publish(self, topic: str, message):
        with self._lock:
            callbacks = list(self._subscribers.get(topic, []))
        if callbacks:
            print(f"[Broker] Publicando en '{topic}': {message}")
            for cb in callbacks:
                cb(message)
        else:
            print(f"[Broker] Sin suscriptores aún en '{topic}': {message}")

# Instancia global del broker interno
broker = MessageBroker()

# Robot
class Robot(threading.Thread):

    def __init__(self, robot_id, name, start_pos,MQTTBroker,MQTTBrokerPort):
        super().__init__(daemon=True)
        self.robot_id    = robot_id
        self.name        = name
        self.current_pos = list(start_pos)
        self.target_pos  = None

        self._stop_event   = threading.Event()
        self._target_event = threading.Event()

        # Suscribirse al broker interno

        # Topics MQTT
        ROOT = "$Planta/"

        self._topic = ROOT + f"robots/{robot_id}/target_pos"
        broker.subscribe(self._topic, self.on_target_received)

        position = ROOT + f"robots/{robot_id}/position"
        event = ROOT + f"robots/{robot_id}/event"
        battery = ROOT + f"robots/{robot_id}/battery"
        self.topicList = {"position":position, "event":event, "battery":battery}

        self.topicConfig = {position: (0, False), event: (1, True), battery: (0, False)}

        self.client = MQTTC.Client(client_id=f"Robot_{robot_id}")
        self.client.connect(MQTTBroker,MQTTBrokerPort)

    def PublishTopic(self, t, payload):
        cfg = self.topicConfig[t]
        self.client.publish(t, json.dumps(payload), cfg[0], cfg[1])

    def on_target_received(self, target_pos):
        #Llamado por el broker interno cuando llega un nuevo destino.
        self.target_pos = list(target_pos)
        print(f"[{self.name}] Objetivo recibido → {self.target_pos}")
        self._target_event.set()  # desbloquea el hilo en espera

    def run(self):
        print(f"[{self.name}] Iniciando en {self.current_pos}, esperando objetivo…")


        # Esperar hasta recibir el objetivo
        while not self._target_event.is_set() and not self._stop_event.is_set():
            time.sleep(0.05)

        if self._stop_event.is_set():
            return

        print(f"[{self.name}] Moviéndome hacia {self.target_pos}")

        # Bucle de movimiento
        while self.current_pos != self.target_pos and not self._stop_event.is_set():
            self.move_towards_target()
            self.update_position_on_canvas()

            ts = time.time()
            payload = {"X":self.current_pos[0],"Y":self.current_pos[0],"TS":ts}
            self.PublishTopic(self.topicList["position"],payload)

            time.sleep(0.5)

        if not self._stop_event.is_set():
            print(f"[{self.name}] ¡Ha llegado a {self.target_pos}!")


    def move_towards_target(self):
        if self.current_pos[0] < self.target_pos[0]:
            self.current_pos[0] += 1
        elif self.current_pos[0] > self.target_pos[0]:
            self.current_pos[0] -= 1

        if self.current_pos[1] < self.target_pos[1]:
            self.current_pos[1] += 1
        elif self.current_pos[1] > self.target_pos[1]:
            self.current_pos[1] -= 1

    def stop(self):
        self._stop_event.set()


# Aplicación principal
class RobotSimulatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Robots")

        # Botón
        self.start_button = tk.Button(
            self.root,
            text="Iniciar Simulación",
            command=self.start_simulation
        )
        self.start_button.pack(pady=10)

        # Crear robots (sin target aún; lo recibirán vía MQTT)
        self.robots = [
            Robot(self.canvas, 1, "Robot1", "red",   [1, 1],"Localhost",1883),
            Robot(self.canvas, 2, "Robot2", "green", [48, 1],"Localhost",1883),
            Robot(self.canvas, 3, "Robot3", "blue",  [1, 48],"Localhost",1883),
        ]
        self.display_initial_positions()

        # Cliente MQTT
        self.mqtt_client = MQTTC.Client()
        self.mqtt_client.user_data_set(self)
        self.mqtt_client.on_connect = self._on_mqtt_connect
        self.mqtt_client.on_message = self._on_mqtt_message
        try:
            self.mqtt_client.connect(BROKER, PORT, 60)
            mqtt_thread = threading.Thread(
                target=self.mqtt_client.loop_forever,
                daemon=True
            )
            mqtt_thread.start()
            print(f"[MQTT] Conectando a {BROKER}:{PORT}…")
        except Exception as e:
            print(f"[MQTT] No se pudo conectar al broker: {e}")

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)


    # Callbacks MQTT

    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Conectado al broker")
            for topic in TARGET_TOPICS:
                client.subscribe(topic)
                print(f"[MQTT] Suscrito a: {topic}")
        else:
            print(f"[MQTT] Error de conexión, código: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            data   = json.loads(msg.payload.decode())
            target = [data["x"], data["y"]]

            robot_name = TARGET_TOPICS.get(msg.topic)
            if robot_name:
                broker.publish(f"{robot_name}/target_pos", target)
            else:
                print(f"[MQTT] Topic desconocido: {msg.topic}")

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[MQTT] Error al procesar mensaje de {msg.topic}: {e}")


    # UI
    def display_initial_positions(self):
        #Dibuja los robots en su posición inicial antes de arrancar.
        for robot in self.robots:
            robot.draw_oval()

    def start_simulation(self):
        #Arranca los hilos de los robots y deshabilita el botón.
        for robot in self.robots:
            self.canvas.delete(robot.robot_shape)
        for robot in self.robots:
            robot.start()

        self.start_button["state"] = "disabled"
        print("Simulación iniciada. Esperando coordenadas vía MQTT…")

    def stop_simulation(self):
        for robot in self.robots:
            robot.stop()

    def on_closing(self):
        self.stop_simulation()
        try:
            self.mqtt_client.disconnect()
        except Exception:
            pass
        self.root.destroy()


# Punto de entrada
root = tk.Tk()
app  = RobotSimulatorApp(root)
root.mainloop()