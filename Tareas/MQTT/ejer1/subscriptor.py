from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
ROOT = "$SYS/"
topic1 = ROOT+"sensor/datoA"
last_msg = {}

def on_connect(client, userdata, flags, rc):
    print("conexión con éxito")

def on_message(client, userdata, message):
    received_msg = message.payload.decode()
    if message.topic == topic1:
        last_msg[message.topic] = received_msg
    print("mensaje "+received_msg)
    if message.topic == topic1:
        try:
            dato=int(received_msg)
        except ValueError:
            dato=received_msg

if __name__ == '__main__':
    client = Client(client_id="SubTest")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(THE_BROKER, 1883)

    client.subscribe(topic1)
    client.loop_start()

    while True:
        print(last_msg)
        time.sleep(5)