import json
import time
import asyncio

from asyncua import Server

import paho.mqtt.client as mqtt
from paho.mqtt.client import Client

OPC_ENDPOINT = "opc.tcp://0.0.0.0:4840/upv/jgimniz/"
OPC_NAMESPACE = "http://upv.es/JgimnizP18"


# VARIABLES GLOBALES OPC-UA
robots_nodes = {}
mqtt_client_global = None
targets_count = 0
last_update = {}
ignition_override = set()

# CALLBACK MQTT
def on_message(client, userdata, msg):
    global robots_nodes
    global targets_count
    global last_update
    try:
        topic = msg.topic
        tokens = topic.split("/")
        robot_id = tokens[2]
        dataName = tokens[3]
        last_update[robot_id] = time.time()
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
                robot["Connected"].write_value(data),
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
    topic = f"robots/{robot_id}/target_pos"
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
    plant = await objects.add_object(idx,"Plant")
    # STATISTICS
    stats_obj = await plant.add_object(idx,"Statistics")
    active_robots = await stats_obj.add_variable(idx,"ActiveRobots",0)
    targets_reached = await stats_obj.add_variable(idx,"TargetsReached",0)



    # ROBOTS
    for robot_id in ["R1", "R2", "R3"]:
        robot_obj = await plant.add_object(idx,f"Robot_{robot_id}")
        # POSITION
        pos_obj = await robot_obj.add_object(idx,"Position")
        pos_x = await pos_obj.add_variable(idx,"X",0.0)
        pos_y = await pos_obj.add_variable(idx,"Y",0.0)
        # TARGET
        target_obj = await robot_obj.add_object(idx,"Target")
        target_x = await target_obj.add_variable(idx,"X",0.0)
        target_y = await target_obj.add_variable(idx,"Y",0.0)
        await target_x.set_writable()
        await target_y.set_writable()
        # VARIABLES
        battery = await robot_obj.add_variable(idx,"Battery",100.0)
        status = await robot_obj.add_variable(idx,"Status","IDLE")
        connected = await robot_obj.add_variable(idx,"Connected",False)
        # GUARDAR REFERENCIAS
        robots_nodes[robot_id] = {
            "pos_x": pos_x,"pos_y": pos_y,
            "target_x": target_x,"target_y": target_y,
            "battery": battery,
            "status": status,
            "connected": connected}

    # MQTT CLIENTE
    mqtt_client = Client(mqtt.CallbackAPIVersion.VERSION1,client_id="opcua-server")

    global mqtt_client_global
    mqtt_client_global = mqtt_client
    mqtt_client.on_message = on_message

    mqtt_client.connect("localhost",1883)
    mqtt_client.subscribe("robots/+/position")
    mqtt_client.subscribe("robots/+/battery")
    mqtt_client.subscribe("robots/+/event")
    mqtt_client.loop_start()



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
            now = time.time()
            activos = 0

            for robot_id, robot in robots_nodes.items():
                ultimo = last_update.get(robot_id,0)
                if now - ultimo > 2:
                    await robot["connected"].write_value(False)
                else:
                    await robot["connected"].write_value(True)
                    activos += 1

            await active_robots.write_value(activos)
            await asyncio.sleep(0.5)

# MAIN

if __name__ == "__main__":
    asyncio.run(main())