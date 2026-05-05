import random

from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
BROKER_PORT = 1883
ID = 1

ROOT = "$Planta/"
position = ROOT+f"robots/{ID:03d}/position"
event = ROOT+f"robots/{ID:03d}/event"
battery = ROOT+f"robots/{ID:03d}/battery"

topicList = [position,event,battery]
topicConfig = {position:(0,False),event:(1,True),battery:(0,False)}

def PublishTopic(t,payload):
    cfg = topicConfig[t]
    client.publish(t, payload, cfg[0], cfg[1])

if __name__ == '__main__':
    client = Client(client_id=f"Robot_{ID:03d}")
    client.connect(THE_BROKER, BROKER_PORT)

    while True:
        print("publicando datos")
        payload = {}
        PublishTopic(position,payload)
        PublishTopic(event, payload)
        PublishTopic(battery, payload)
        time.sleep(1)