# publisher.py
import paho.mqtt.client as mqtt
import json, time

client = mqtt.Client()
client.connect("localhost", 1883, 60)

destinos = {
    "Robot1/target_pos": {"x": 15, "y": 5},
    "Robot2/target_pos": {"x": 20, "y": 30},
    "Robot3/target_pos": {"x": 40, "y": 40},
}

for topic, coords in destinos.items():
    client.publish(topic, json.dumps(coords))
    print(f"Publicado en {topic}: {coords}")
    time.sleep(1)

client.disconnect()