from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
THE_TOPIC = "ChatLog"
topic_test1 = THE_TOPIC + "test/UPV_1"
topic_test2 = THE_TOPIC + "test/UPV_2"
last_msg = {}


def on_connect(client, userdata, flags, rc):
    print("conexión con éxito")


def on_message(client, userdata, message):
    received_msg = message.payload.decode()
    if message.topic == topic_test1 or message.topic == topic_test2:
        last_msg[message.topic] = received_msg
        print("mensaje " + received_msg)
    if message.topic == topic_test2:
        print(received_msg.split())
        campos = received_msg.split(":")
        dato = int(campos[1])


if __name__ == '__main__':
    client = Client(client_id="sub-test-susc")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(THE_BROKER, 1883)
    client.subscribe(topic_test1)
    client.subscribe(topic_test2)
    client.loop_start()

    while True:
        print(last_msg)
        time.sleep(5)