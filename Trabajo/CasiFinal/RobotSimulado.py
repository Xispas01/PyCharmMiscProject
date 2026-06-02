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

BATTERY_CONSUMPTION_RATE = -1.0
BATTERY_REGEN_RATE = 0.5
ROBOT_STEP = 1
SimTimeStep = 0.2
ControlPrints = False

class Robot:
    def __init__(self,RobotID,MQTTConfig,UDPConfig,TCPConfig):
        self.RobotID = RobotID
        self.MQTTClient = MQTTC.Client(client_id=f"{RobotID}")

        self.MQTTBroker = MQTTConfig[0]
        self.MQTTBrokerPort = MQTTConfig[1]

        self.PositionTopic = MQROOT + f"robots/{RobotID}/position"
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

        self.ActiveState = True
        self.Status = 'IDLE'
        self.Halted = False
        self.ArriveTarget = False
        self.HasTarget = False
        self.TargetPosition = None

    def MQTTHeartBeat(self):
        while self.ActiveState:
            sleep(0.2)
            if ControlPrints:
                print(f"{self.RobotID} sending MQTT HB")

            hora_actual = time.time()
            positionData = {'x':self.Position['x'],'y':self.Position['y'],'heading':self.TargetPosition,'ts':hora_actual}
            batteryData = {'level':self.Battery,'ts':hora_actual}

            self.MQTTClient.publish(self.PositionTopic,f"{json.dumps(positionData)}")
            self.MQTTClient.publish(self.BatteryTopic, f"{json.dumps(batteryData)}")


    def UDPHeartBeat(self):
        while self.ActiveState:
            sleep(0.5)
            if ControlPrints:
                print(f"{self.RobotID} sending UDP HB")
            # Serializar los datos utilizando pickle.dumps()
            hora_actual = time.time()
            data_serialized = pickle.dumps({ 'robot_id': self.RobotID, 'seq': 142, 'ts': hora_actual, 'battery': self.Battery, 'status':self.Status})
            # Enviar los datos serializados a través del socket
            self.UDPSocket.sendto(data_serialized, self.UDPServer)
        self.UDPSocket.close()

    def TCPComandCenter(self):
        while self.ActiveState:
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
                        self.HasTarget = True
                        print(f"Target set to {Tpos} for {self.RobotID}\n")
            elif Command.startswith('STOP'):
                if ControlPrints:
                    print(f"STOP {Command}\n")
                self.TCPSocket.send("ACK".encode())
                self.TCPSocket.send(f"{self.Position}".encode())
                self.Halted = True
                self.Status = 'HALTED'
            elif Command.startswith('RESUME'):
                if ControlPrints:
                    print(f"RESUME {Command}\n")
                self.TCPSocket.send("ACK".encode())
                self.Halted = False
                self.Status = 'IDLE'
            elif Command.startswith('GET_STATUS'):
                if ControlPrints:
                    print(f"GET_STATUS {Command}\n")
                hora_actual = time.time()
                data_serialized = pickle.dumps({'robot_id': self.RobotID, 'seq': 142, 'ts': hora_actual, 'battery': self.Battery,'halted': self.Halted})
                self.TCPSocket.send(data_serialized)
            elif Command.startswith('SHUTDOWN'):
                if ControlPrints:
                    print(f"SHUTDOWN {Command}\n")
                self.TCPSocket.send("ACK".encode())
                self.ActiveState = False
                break
            else:
                self.TCPSocket.send(f"Comando \"{Command}\" desconocido\n".encode())
                if ControlPrints:
                    print(f"Comando \"{Command}\" desconocido\n")

        self.TCPSocket.close()

    def move_towards_target(self):
        if self.Position['x'] < self.TargetPosition['x']:
            self.Position['x'] += ROBOT_STEP
        elif self.Position['x'] > self.TargetPosition['x']:
            self.Position['x'] -= ROBOT_STEP

        if self.Position['y'] < self.TargetPosition['y']:
            self.Position['y'] += ROBOT_STEP
        elif self.Position['y'] > self.TargetPosition['y']:
            self.Position['y'] -= ROBOT_STEP

    def CheckTarget(self):
        return self.Position['x'] == self.TargetPosition['x'] and self.Position['y'] == self.TargetPosition['y']

    def BatteryChange(self,amount):
        self.Battery += amount
        if self.Battery > 100.0:
            self.Battery = 100.0
        elif self.Battery < 0.0:
            self.Battery = 0.0

        if self.Battery < 5.0:
            self.Halted = True
            self.Status = 'HALTED'
        if self.Battery < 10.0:
            hora_actual = time.time()
            self.MQTTClient.publish(self.EventTopic,f"{json.dumps({'type':'low_bat','ts':hora_actual})}",qos=1,retain=True)


    def Simulation(self):
        while self.ActiveState:
            time.sleep(SimTimeStep)
            self.BatteryChange(BATTERY_REGEN_RATE)
            while not self.Halted and self.HasTarget and not self.CheckTarget() and self.Battery + BATTERY_CONSUMPTION_RATE > 0.0:
                self.Status = 'MOVING'

                self.move_towards_target()
                self.BatteryChange(BATTERY_CONSUMPTION_RATE)

                if ControlPrints:
                    print(f"Objetivo {self.RobotID} {self.TargetPosition}\n")
                    print(f"Posicion {self.RobotID} {self.Position}\n")

                if self.CheckTarget():
                    self.HasTarget = False
                    self.TargetPosition = None
                    self.Status = 'IDLE'
                    hora_actual = time.time()
                    self.MQTTClient.publish(self.EventTopic, f"{json.dumps({'type': 'arrived', 'ts': hora_actual})}",qos=1, retain=True)
                time.sleep(SimTimeStep)


    def start(self):
        print(f"{self.RobotID} Arrancando")
        self.MQTTClient.connect(self.MQTTBroker,self.MQTTBrokerPort)
        self.TCPSocket.connect(self.TCPServer)

        HiloMQTTHB = threading.Thread(name='MQTTHB', target=self.MQTTHeartBeat, args=())
        HiloUDPHB = threading.Thread(name='UDPHB', target=self.UDPHeartBeat, args=())
        HiloTCPCC = threading.Thread(name='TCPCC', target=self.TCPComandCenter, args=())
        HiloSimulacion = threading.Thread(name='SIMUL', target=self.Simulation, args=())

        HiloMQTTHB.start()
        HiloUDPHB.start()
        HiloTCPCC.start()
        HiloSimulacion.start()

        print(f"{self.RobotID} En Marcha")

        HiloMQTTHB.join()
        HiloUDPHB.join()
        HiloTCPCC.join()
        HiloSimulacion.join()

def LaunchRobot(RobotID,MQTTConfig,UDPConfig,TCPConfig):
    R = Robot(RobotID, MQTTConfig, UDPConfig, TCPConfig)
    R.start()

if __name__ == '__main__':
    # Punto de entrada

    print(f"R1 Start")
    HiloR1 = threading.Thread(name='R1', target=LaunchRobot, args=("R1",[MQBROKER,MQPORT],[UDPHOST,UDPPORT],[TCPHOST,TCPPORT]))
    HiloR1.start()

    print(f"R2 Start")
    HiloR2 = threading.Thread(name='R2', target=LaunchRobot, args=("R2",[MQBROKER,MQPORT],[UDPHOST,UDPPORT],[TCPHOST,TCPPORT]))
    HiloR2.start()

    print(f"R3 Start")
    HiloR3 = threading.Thread(name='R3', target=LaunchRobot, args=("R3",[MQBROKER,MQPORT],[UDPHOST,UDPPORT],[TCPHOST,TCPPORT]))
    HiloR3.start()

    HiloR1.join()
    HiloR2.join()
    HiloR3.join()