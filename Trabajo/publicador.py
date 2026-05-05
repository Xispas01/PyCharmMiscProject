import random

from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
BROKER_PORT = 1883
ID = 1

ROOT = "$Planta/"
position = ROOT+f"robots/{ID:03d}/position"
target_pos = ROOT+f"robots/{ID:03d}/target_pos"
battery = ROOT+f"robots/{ID:03d}/battery"

topicList = [position,target_pos,battery]
topicConfig = {position:(0,False),target_pos:(1,True),battery:(0,False)}

if __name__ == '__main__':
    client = Client(client_id=f"Robot_{ID:03d}")
    client.connect(THE_BROKER, BROKER_PORT)

    while True:
        print("publicando datos")
        for t in topicList:
            lectura = random.randint(1,10)
            cfg = topicConfig[t]
            client.publish(t,lectura,cfg[0],cfg[1])
        time.sleep(1)