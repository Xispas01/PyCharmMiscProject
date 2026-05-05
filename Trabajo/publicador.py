import random

from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
BROKER_PORT = 1883
ROOT = "$SYS/"
topic1 = ROOT+"sensor/datoA"

if __name__ == '__main__':
    client = Client(client_id="PubTest")
    client.connect(THE_BROKER, BROKER_PORT)

    while True:
        lectura = random.randint(1,10)
        print("publicando dato sensor/datoA")
        client.publish(topic1,lectura)
        time.sleep(0.5)