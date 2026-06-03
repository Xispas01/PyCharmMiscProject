import json
import time
import asyncio

from asyncua import Server

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client

OPC_ENDPOINT = "opc.tcp://0.0.0.0:4840/upv/jgimniz/"
OPC_NAMESPACE = "http://upv.es/JgimnizP18"

MQBROKER = "localhost"
MQPORT = 1883

# VARIABLES GLOBALES OPC-UA
robots_nodes = {}
mqtt_client_global = None
targets_count = 0
ignition_override = set()

# CALLBACK MQTT
def on_message(client, userdata, msg):
    global robots_nodes
    global targets_count
    try:
        topic = msg.topic
        tokens = topic.split("/")
        robot_id = tokens[2]
        dataName = tokens[3]
        data = json.loads(msg.payload.decode())
        robot = robots_nodes.get(robot_id)
        if robot is None:
            return
        # POSITION
        if dataName == "position":
            asyncio.run_coroutine_threadsafe(
                robot["pos_x"].write_value(float(data["x"])),
                loop
            )
            asyncio.run_coroutine_threadsafe(
                robot["pos_y"].write_value(float(data["y"])),
                loop
            )
        # BATTERY
        elif dataName == "battery":
            asyncio.run_coroutine_threadsafe(
                robot["battery"].write_value(float(data["level"])),
                loop
            )
        # STATUS
        elif dataName == "status":
            asyncio.run_coroutine_threadsafe(
                robot["status"].write_value(data),
                loop
            )
        # CONEXION
        elif dataName == "conexion":
            asyncio.run_coroutine_threadsafe(
                robot["Connected"].write_value(bool(data)),
                loop
            )
        # EVENTS
        elif dataName == "event":
            if data["type"] == "arrived":
                targets_count += 1
                asyncio.run_coroutine_threadsafe(
                    targets_reached.write_value(targets_count),
                    loop
                )
    except Exception as e:
        print("Error MQTT:", e)

# PUBLICAR TARGET MQTT
def publicar_target(robot_id, x, y):
    global mqtt_client_global
    topic = f"$Planta/robots/{robot_id}/target_pos"
    data = {"x": x,"y": y}
    mqtt_client_global.publish(topic,json.dumps(data))
    print(f"[OPCUA -> MQTT] {robot_id} target=({x},{y})")

# MAIN OPC-UA
async def main():
    global loop
    global active_robots
    global targets_reached

    loop = asyncio.get_running_loop()
    # SERVIDOR OPC-UA
    server = Server()
    await server.init()
    server.set_endpoint(OPC_ENDPOINT)

    # NAMESPACE
    idx = await server.register_namespace(OPC_NAMESPACE)

    # OBJETOS
    objects = server.nodes.objects
    planta = await objects.add_object(idx,"Planta")
    # STATISTICS
    general_stats = await planta.add_object(idx,"Stats")
    active_robots = await general_stats.add_variable(idx,"ActiveRobots",0)
    targets_reached = await general_stats.add_variable(idx,"TargetsReached",0)



    # ROBOTS
    for robot_id in ["R1", "R2", "R3"]:
        robot_obj = await planta.add_object(idx,f"{robot_id}")
        # POSITION
        pos_x = await robot_obj.add_variable(idx,"PosX",0.0)
        pos_y = await robot_obj.add_variable(idx,"PosY",0.0)
        # TARGET
        target_x = await robot_obj.add_variable(idx,"X",0.0)
        target_y = await robot_obj.add_variable(idx,"Y",0.0)
        await target_x.set_writable()
        await target_y.set_writable()
        # VARIABLES
        robot_battery = await robot_obj.add_variable(idx,"Battery",100.0)
        robot_status = await robot_obj.add_variable(idx,"Status","IDLE")
        robot_connected = await robot_obj.add_variable(idx,"Connected",False)
        # GUARDAR REFERENCIAS
        robots_nodes[robot_id] = {
            "pos_x": pos_x,"pos_y":pos_y,
            "target_x": target_x,"target_y": target_y,
            "battery": robot_battery,
            "status": robot_status,
            "connected": robot_connected}

    # MQTT CLIENTE
    MQTTC = Client(client_id="PasarelaMQTT_OPC")

    global mqtt_client_global
    mqtt_client_global = MQTTC
    MQTTC.on_message = on_message

    MQTTC.connect(MQBROKER,MQPORT)
    MQTTC.subscribe("$Planta/robots/+/position")
    MQTTC.subscribe("$Planta/robots/+/battery")
    MQTTC.subscribe("$Planta/robots/+/event")
    MQTTC.loop_start()

    # ARRANCAR SERVIDOR

    async with server:
        print("\nServidor OPC-UA activo\n")
        print("opc.tcp://0.0.0.0:4840/upv/sdrc/\n")

        # ÚLTIMOS TARGETS
        last_targets = {"R1": (-1, -1),"R2": (-1, -1),"R3": (-1, -1)}

        while True:
            # TARGETS DESDE IGNITION
            for robot_id, robot in robots_nodes.items():
                try:
                    x = int(await robot["target_x"].read_value())
                    y = int(await robot["target_y"].read_value())
                    actual = (x, y)

                    # SOLO SI CAMBIA
                    if actual != last_targets[robot_id]:
                        ignition_override.add(robot_id)
                        publicar_target(robot_id,x,y)
                        last_targets[robot_id] = actual
                        await asyncio.sleep(1)
                        ignition_override.discard(robot_id)
                except Exception as e:
                    print("Error targets:",e)

            # TIMEOUT ROBOTS
            activos = 0
            for robot_id, robot in robots_nodes.items():
                try:
                    c = int(await robot["connected"].read_value())
                    if c:
                        activos = activos + 1
                except Exception as e:
                    print("Error:",e)

            await active_robots.write_value(activos)
            await asyncio.sleep(0.5)

# MAIN

if __name__ == "__main__":
    asyncio.run(main())