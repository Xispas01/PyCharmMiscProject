from paho.mqtt.client import Client
import time
import sys
THE_BROKER = "localhost"
THE_TOPIC = "ChatLog"
topic_test1 = THE_TOPIC+"test/UPV_1"
topic_test2 = THE_TOPIC+"test/UPV_2"

if __name__ == '__main__':
    client = Client(client_id="sub-test-pub")
    client.connect(THE_BROKER, 1883)
    contador=0

    while True:
        print("publicando dato test/1")
        client.publish(topic_test1,"esto es un string")
        print("publicando dato test/2")
        client.publish(topic_test2, "esto es un string con dato: "+contador.__str__())
        contador=contador+1
        time.sleep(5)
