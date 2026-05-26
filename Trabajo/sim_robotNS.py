#!/usr/bin/env python
# coding: utf-8
from json import JSONEncoder
from tabnanny import verbose

from time import sleep
import threading
import json
import paho.mqtt.client as MQTTC
import socket
import pickle
import time
import sys

MQBROKER = "localhost"
MQPORT = 1883

UDPHOST = "localhost"
UDPPORT = 9001

TCPHOST = "localhost"
TCPPORT = 12345

MQROOT = "$Planta/"

ControlPrints = False

class Robot:
    def __init__(self,RobotID,MQTTConfig,UDPConfig,TCPConfig):
        self.RobotID = RobotID
        self.MQTTClient = MQTTC.Client(client_id=f"{RobotID}")

        self.MQTTBroker = MQTTConfig[0]
        self.MQTTBrokerPort = MQTTConfig[1]

        self.PositionTopic = MQROOT + f"robots/{RobotID}/pos"
        self.EventTopic = MQROOT + f"robots/{RobotID}/event"
        self.BatteryTopic = MQROOT + f"robots/{RobotID}/battery"

        self.UDPSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.UDPServer = (UDPConfig[0], UDPConfig[1])

        # Creamos un objeto socket TCP
        self.TCPSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.TCPServer = (TCPConfig[0],TCPConfig[1])

        self.Position = {"x": 20, "y": 5}
        self.Event = "Start"
        self.Battery = 100.0

        self.CheckStop = False
        self.HasTarget = False
        self.TargetPosition = None

    def MQTTHeartBeat(self):
        while True:
            sleep(0.2)
            if ControlPrints:
                print(f"{self.RobotID} sending MQTT HB")
            self.MQTTClient.publish(self.PositionTopic,f"{json.dumps(self.Position)}")
            self.MQTTClient.publish(self.EventTopic, f"Last Event: {self.Event}")
            self.MQTTClient.publish(self.BatteryTopic, f"{self.Battery:03.02f}%")


    def UDPHeartBeat(self):
        while True:
            sleep(0.5)
            if ControlPrints:
                print(f"{self.RobotID} sending UDP HB")
            # Serializar los datos utilizando pickle.dumps()
            hora_actual = time.time()
            data_serialized = pickle.dumps({ 'robot_id': f"{self.RobotID}", 'seq': 142, 'timestamp': hora_actual, 'battery': f"{self.Battery}" })
            # Enviar los datos serializados a través del socket
            self.UDPSocket.sendto(data_serialized, self.UDPServer)

    def TCPComandCenter(self):
        while True:
            # Recibir datos
            Command = self.TCPSocket.recv(1024).decode()
            if Command.startswith('SET_TARGET'):
                if ControlPrints:
                    print(f"SET_TARGET {Command}\n")
                print(f"SET_TARGET {Command}\n")
                data = Command.split(' ')
                if len(data) != 3:
                    print(f"SET_TARGET {Command} is invalid\n")
                else :
                    try:
                        Tpos = {'x':int(data[1]),'y':int(data[2])}
                    except  ValueError:
                        print(f"SET_TARGET {Command} is invalid\n")
                    else:
                        self.TargetPosition = Tpos
                        print(f"Target set to {Tpos}\n")
            elif Command.startswith('STOP'):
                if ControlPrints:
                    print(f"STOP {Command}\n")
                self.TCPSocket.send("ACK".encode())
                self.TCPSocket.send(f"{self.Position}".encode())
            elif Command.startswith('RESUME'):
                if ControlPrints:
                    print(f"RESUME {Command}\n")
                self.TCPSocket.send("ACK".encode())
            elif Command.startswith('GET_STATUS'):
                if ControlPrints:
                    print(f"GET_STATUS {Command}\n")
            elif Command.startswith('SHUTDOWN'):
                if ControlPrints:
                    print(f"SHUTDOWN {Command}\n")
                self.TCPSocket.send("ACK".encode())
                self.TCPSocket.close()
                break
            else:
                if ControlPrints:
                    print(f"Comando \"{Command}\" desconocido\n")

    def start(self):
        self.MQTTClient.connect(self.MQTTBroker,self.MQTTBrokerPort)
        self.TCPSocket.connect(self.TCPServer)

        HiloMQTTHB = threading.Thread(name='MQTTHB', target=self.MQTTHeartBeat, args=())
        HiloUDPHB = threading.Thread(name='UDPHB', target=self.UDPHeartBeat, args=())
        HiloTCPCC = threading.Thread(name='TCPCC', target=self.TCPComandCenter, args=())

        HiloMQTTHB.start()
        HiloUDPHB.start()
        HiloTCPCC.start()

if __name__ == '__main__':
    # Punto de entrada
    R1 = Robot("R1",[MQBROKER,MQPORT],[UDPHOST,UDPPORT],[TCPHOST,TCPPORT])
    R1.start()
    R2 = Robot("R2",[MQBROKER,MQPORT],[UDPHOST,UDPPORT],[TCPHOST,TCPPORT])
    R2.start()
    while True:
        pass