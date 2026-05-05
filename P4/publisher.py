# publisher.py
import paho.mqtt.client as mqtt
import json, time

client = mqtt.Client()
client.connect("localhost", 1883, 60)

ROOT = "$Planta/"
RIDS = [1,2,3]
Obj_R1 = ROOT + f"robots/{RIDS[0]}/target_pos"
Obj_R2 = ROOT + f"robots/{RIDS[1]}/target_pos"
Obj_R3 = ROOT + f"robots/{RIDS[2]}/target_pos"

destinos = {
    Obj_R1: {"x": 20, "y": 5},
    Obj_R2: {"x": 21, "y": 30},
    Obj_R3: {"x": 41, "y": 40},
}

for topic, coords in destinos.items():
    client.publish(topic, json.dumps(coords))
    print(f"Publicado en {topic}: {coords}")
    time.sleep(1)

client.disconnect()