#!/usr/bin/env python
# coding: utf-8

import paho.mqtt.client as MQTTC
import json
import tkinter as tk
import threading
import time
from json import JSONEncoder
import pickle
import sys

BROKER = "localhost"
PORT = 1883
ID = 1

# Constantes globales
WINDOW_SIZE = 50
ROBOT_SIZE = 10

# Se gestiona de manera totalmente dinámica leyendo del servidor MQTT
TARGET_TOPICS = {}


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

    def __init__(self, canvas, robot_id, name, color, start_pos, MQTTBroker, MQTTBrokerPort):
        super().__init__(daemon=True)
        self.canvas = canvas
        self.robot_id = robot_id
        self.name = name
        self.color = color
        self.current_pos = list(start_pos)
        self.target_pos = None
        self.robot_size = ROBOT_SIZE
        self.robot_shape = None  # ID entero del óvalo en el canvas
        self.target_shape = None  # ID entero del óvalo destino

        self._stop_event = threading.Event()
        self._target_event = threading.Event()

        # Suscribirse al broker interno
        self._topic = f"{self.name}/target_pos"
        broker.subscribe(self._topic, self.on_target_received)

        # Topics MQTT
        ROOT = "$Planta/"
        position = ROOT + f"robots/{robot_id}/position"
        event = ROOT + f"robots/{robot_id}/event"
        battery = ROOT + f"robots/{robot_id}/battery"

        self.topicList = {"position": position, "event": event, "battery": battery}
        self.topicConfig = {position: (0, False), event: (1, True), battery: (0, False)}
        self.client = MQTTC.Client(client_id=f"Robot_{robot_id}")
        self.client.connect(MQTTBroker, MQTTBrokerPort)

    def draw_oval(self):
        # Crea el óvalo del robot en el canvas y guarda su ID.
        self.robot_shape = self.canvas.create_oval(
            self.current_pos[0] * self.robot_size,
            self.current_pos[1] * self.robot_size,
            (self.current_pos[0] + 1) * self.robot_size,
            (self.current_pos[1] + 1) * self.robot_size,
            fill=self.color
        )

    def PublishTopic(self, t, payload):
        cfg = self.topicConfig[t]
        self.client.publish(t, json.dumps(payload), cfg[0], cfg[1])

    def on_target_received(self, target_pos):
        # Llamado por el broker interno cuando llega un nuevo destino.
        self.target_pos = list(target_pos)
        print(f"[{self.name}] Objetivo recibido → {self.target_pos}")
        self._target_event.set()  # desbloquea el hilo en espera

    def run(self):
        print(f"[{self.name}] Iniciando en {self.current_pos}, esperando objetivo…")

        # Dibujar el robot en su posición inicial real recibida
        self.draw_oval()

        # Esperar hasta recibir el objetivo
        while not self._target_event.is_set() and not self._stop_event.is_set():
            time.sleep(0.05)

        if self._stop_event.is_set():
            return

        # Dibujar el destino
        self.target_shape = self.canvas.create_oval(
            self.target_pos[0] * self.robot_size,
            self.target_pos[1] * self.robot_size,
            (self.target_pos[0] + 1) * self.robot_size,
            (self.target_pos[1] + 1) * self.robot_size,
            fill=self.color
        )

        print(f"[{self.name}] Moviéndome hacia {self.target_pos}")

        # Bucle de movimiento
        while self.current_pos != self.target_pos and not self._stop_event.is_set():
            self.move_towards_target()
            self.update_position_on_canvas()

            ts = time.time()
            payload = {"X": self.current_pos[0], "Y": self.current_pos[1], "TS": ts}
            self.PublishTopic(self.topicList["position"], payload)

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

    def update_position_on_canvas(self):
        self.canvas.coords(
            self.robot_shape,
            self.current_pos[0] * self.robot_size,
            self.current_pos[1] * self.robot_size,
            (self.current_pos[0] + 1) * self.robot_size,
            (self.current_pos[1] + 1) * self.robot_size
        )

    def stop(self):
        self._stop_event.set()


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
        self.robots = [
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
            # Escucha global de cualquier instanciación u objetivo de robot
            client.subscribe("+/target_pos")
            print("[MQTT] Suscrito dinámicamente a: +/target_pos")
        else:
            print(f"[MQTT] Error de conexión, código: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            topic_parts = msg.topic.split('/')
            if len(topic_parts) != 2 or topic_parts[1] != "target_pos":
                return

            robot_name = topic_parts[0]
            data = json.loads(msg.payload.decode())

            # --- CASO 1: ELIMINACIÓN/DESCONEXIÓN EN EL SERVIDOR MQTT ---
            if data.get("action") == "shutdown" or data.get("x") is None or data.get("y") is None:
                if msg.topic in TARGET_TOPICS:
                    del TARGET_TOPICS[msg.topic]
                    print(f"[MQTT] Robot desconectado. Eliminado de TARGET_TOPICS: {msg.topic}")

                for robot in list(self.robots):
                    if robot.name == robot_name:
                        robot.stop()
                        if robot.robot_shape:
                            self.canvas.delete(robot.robot_shape)
                        if robot.target_shape:
                            self.canvas.delete(robot.target_shape)
                        self.robots.remove(robot)
                        print(f"[MQTT] Instancia de [{robot_name}] removida de la interfaz.")
                return

            # --- CASO 2: DETECCIÓN Y SUSCRIPCIÓN NUEVA EN EL SERVIDOR MQTT ---
            if msg.topic not in TARGET_TOPICS:
                TARGET_TOPICS[msg.topic] = robot_name
                print(f"[MQTT] Nuevo robot detectado en el servidor MQTT: {msg.topic} -> {robot_name}")

            # Verificar si ya existe físicamente en la UI local, si no, se crea usando sus datos reales
            robot_existe = any(r.name == robot_name for r in self.robots)
            if not robot_existe:
                robot_id = len(self.robots) + 1

                # Leemos la posición inicial y los atributos estéticos directamente enviados del Servidor MQTT
                start_x = data.get("start_x", data["x"])
                start_y = data.get("start_y", data["y"])
                color = data.get("color", "gray")  # Gris por defecto si el servidor no especifica color

                print(
                    f"[MQTT] Instanciando remotamente [{robot_name}] en posición inicial: [{start_x}, {start_y}] con color '{color}'")
                new_robot = Robot(self.canvas, robot_id, robot_name, color, [start_x, start_y], BROKER, PORT)
                self.robots.append(new_robot)

                # Si la simulación gráfica ya fue iniciada por el botón, corre el hilo al vuelo
                if self.start_button["state"] == "disabled":
                    new_robot.start()

            # Enviar coordenadas de destino al broker interno de control de hilos
            target = [data["x"], data["y"]]
            broker.publish(f"{robot_name}/target_pos", target)

        except (json.JSONDecodeError, KeyError) as e:
            print(f"[MQTT] Error al procesar mensaje de {msg.topic}: {e}")

    # UI
    def display_initial_positions(self):
        for robot in self.robots:
            robot.draw_oval()

    def start_simulation(self):
        # Arranca los hilos de los robots que se hayan detectado hasta el momento
        for robot in self.robots:
            self.canvas.delete(robot.robot_shape)
        for robot in self.robots:
            robot.start()

        self.start_button["state"] = "disabled"
        print("Simulación iniciada de forma pasiva. Esperando altas y bajas desde el servidor MQTT…")

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
app = RobotSimulatorApp(root)
root.mainloop()