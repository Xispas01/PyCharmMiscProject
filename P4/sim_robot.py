#!/usr/bin/env python
# coding: utf-8

import paho.mqtt.client as mqtt
import json
import tkinter as tk
import threading
import time

# Constantes globales
WINDOW_SIZE = 50
ROBOT_SIZE  = 10

#Variables Locales
BROKER = "localhost"
PORT   = 1883

#Variables de red
#BROKER = "localhost"
#PORT   = 1883

# Topics MQTT (topic -> nombre robot)
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
    def __init__(self, canvas, robot_id, name, color, start_pos):
        super().__init__(daemon=True)
        self.canvas      = canvas
        self.robot_id    = robot_id
        self.name        = name
        self.color       = color
        self.current_pos = list(start_pos)
        self.target_pos  = None
        self.robot_size  = ROBOT_SIZE
        self.robot_shape = None   # ID entero del óvalo en el canvas
        self.target_shape = None  # ID entero del rectángulo destino

        self._stop_event   = threading.Event()
        self._target_event = threading.Event()

        # Suscribirse al broker interno
        self._topic = f"{self.name}/target_pos"
        broker.subscribe(self._topic, self.on_target_received)

    def draw_oval(self):
        #Crea el óvalo del robot en el canvas y guarda su ID.
        self.robot_shape = self.canvas.create_oval(
            self.current_pos[0] * self.robot_size,
            self.current_pos[1] * self.robot_size,
            (self.current_pos[0] + 1) * self.robot_size,
            (self.current_pos[1] + 1) * self.robot_size,
            fill=self.color
        )

    def on_target_received(self, target_pos):
        #Llamado por el broker interno cuando llega un nuevo destino.
        self.target_pos = list(target_pos)
        print(f"[{self.name}] Objetivo recibido → {self.target_pos}")
        self._target_event.set()  # desbloquea el hilo en espera

    def run(self):
        print(f"[{self.name}] Iniciando en {self.current_pos}, esperando objetivo…")

        # Dibujar el robot
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
            self.robot_shape,  # ID entero del óvalo
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

        # Crear robots (sin target aún; lo recibirán vía MQTT)
        self.robots = [
            Robot(self.canvas, 1, "Robot1", "red",   [1, 1]),
            Robot(self.canvas, 2, "Robot2", "green", [48, 1]),
            Robot(self.canvas, 3, "Robot3", "blue",  [1, 48]),
        ]
        self.display_initial_positions()

        # Cliente MQTT
        self.mqtt_client = mqtt.Client()
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