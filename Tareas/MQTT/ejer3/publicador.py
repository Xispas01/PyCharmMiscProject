import random

from paho.mqtt.client import Client
import time
import sys

THE_BROKER = "localhost"
ROOT = "$SYS/"
TCocina = ROOT+"casa/habitación/cocina/temperatura"
TDorm1 = ROOT+"casa/habitación/dorm1/temperatura"
TDorm2 = ROOT+"casa/habitación/dorm2/temperatura"
TAseo = ROOT+"casa/habitación/aseo/temperatura"
HAseo = ROOT+"casa/habitación/aseo/humedad"

tempTopics = [TCocina,TDorm1,TDorm2,TAseo]
def TempGen():
    Ponderacion = random.randint(1,100)
    if Ponderacion < 70:
        return random.randint(0,20)
    return random.randint(20,100)

if __name__ == '__main__':
    client = Client(client_id="RoomTracker")
    client.connect(THE_BROKER, 1883)

    while True:
        for topic in tempTopics:
            lectura = TempGen()
            unidad = 'C'
            client.publish(topic, 'valor:' + str(lectura) + ';unidad:' + unidad)
            time.sleep(0.5)

        lectura = random.randint(0,100)
        unidad = 'Hr'
        client.publish(HAseo,'valor:'+str(lectura)+';unidad:'+unidad)

        time.sleep(0.5)