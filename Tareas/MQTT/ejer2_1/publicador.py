import random

from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
BROKER_PORT = 1883
ROOT = "$SYS/"
topic1 = ROOT+"sensor/datoB"

if __name__ == '__main__':
    client = Client(client_id="PubFormated")
    client.connect(THE_BROKER, BROKER_PORT)

    while True:
        lectura = random.randint(1,10)
        unidad = 'Kwh'
        print("publicando dato " + topic1)
        client.publish(topic1,'valor:'+str(lectura)+';unidad:'+unidad)
        time.sleep(0.5)