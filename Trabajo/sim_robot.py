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

        self.MQTTBroker = MQTTBroker
        self.MQTTBrokerPort = MQTTBrokerPort

        self._stop_event   = threading.Event()
        self._target_event = threading.Event()

        # Topics MQTT
        ROOT = "$Planta/"
        position = ROOT + f"robots/{robot_id}/position"
        event = ROOT + f"robots/{robot_id}/event"
        battery = ROOT + f"robots/{robot_id}/battery"

        self.targetTopic = ROOT + f"robots/{robot_id}/target_pos"

        self.topicList = {"position":position, "event":event, "battery":battery}
        self.topicConfig = {position: (0, False), event: (1, True), battery: (0, False)}

        self.client = MQTTC.Client(client_id=f"Robot_{robot_id}")
        self.client.user_data_set(self)
        self.client.on_connect = self._on_mqtt_connect
        self.client.on_message = self._on_mqtt_message

        self.client.connect(self.MQTTBroker,self.MQTTBrokerPort)


    # Callbacks MQTT
    def _on_mqtt_connect(self, client, userdata, flags, rc):
        if rc == 0:
            print("[MQTT] Conectado al broker")
            client.subscribe(self.targetTopic,self.on_target_received)
            print(f"[MQTT] Suscrito a: {self.targetTopic}")
        else:
            print(f"[MQTT] Error de conexión, código: {rc}")

    def _on_mqtt_message(self, client, userdata, msg):
        try:
            data   = json.loads(msg.payload.decode())
            target = [data["x"], data["y"]]
            self.target_pos = target
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[MQTT] Error al procesar mensaje de {msg.topic}: {e}")

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
        while True:
            # Esperar hasta recibir el objetivo
            while not self._target_event.is_set() and not self._stop_event.is_set():
                time.sleep(0.05)

            if self._stop_event.is_set():
                return

            print(f"[{self.name}] Moviéndome hacia {self.target_pos}")

            # Bucle de movimiento
            while self.current_pos != self.target_pos and not self._stop_event.is_set():
                self.move_towards_target()

                print(f"[{self.name}] Posicion Actual {self.current_pos} hacia {self.target_pos}")

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

if __name__ == '__main__':
    # Punto de entrada
    R1 = Robot(1, "Robot1", [1, 1], "Localhost", 1883)
    R1.start()
    R2 = Robot(2, "Robot2", [48, 1], "Localhost", 1883)
    R2.start()
    R3 = Robot(3, "Robot3", [1, 48], "Localhost", 1883)
    R3.start()
    while True:
        time.sleep(10)
        pass