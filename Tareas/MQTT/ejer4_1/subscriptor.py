from os.path import split

from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
ROOT = "$SYS/"
Temp = ROOT+"casa/habitación/+/temperatura"

last_msg = {}

def on_connect(client, userdata, flags, rc):
    print("conexión con éxito")

def on_message(client, userdata, message):
    received_msg = message.payload.decode()
    items = {}
    campos = received_msg.split(';')

    for campo in campos:
        (id,value) = campo.split(':')
        items[id] = value
    print('lectura '+items['valor']+' '+items['unidad'])
    try:
        dato=int(received_msg)
    except ValueError:
        dato=received_msg

    last_msg[message.topic] = 'lectura '+items['valor']+' '+items['unidad']

    client.publish(message.topic.replace("temperatura","Alerta"), int(items['valor']) > 20)


if __name__ == '__main__':
    client = Client(client_id="TempTrakerGeneral")
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(THE_BROKER, 1883)

    client.subscribe(Temp)
    client.loop_start()

    while True:
        print(last_msg)
        time.sleep(5)