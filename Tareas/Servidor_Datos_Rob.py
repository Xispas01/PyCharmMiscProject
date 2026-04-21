import time
from asyncua.sync import Server
from asyncua import ua
if __name__ == "__main__":
    # configuramos el servidor
    server = Server()
    server.set_endpoint("opc.tcp://localhost:4840/freeopcua/server/")
    # configuramos nuestro namespace
    uri = "http://localhost/mynamespace"
    idx = server.register_namespace(uri)
    print(f"Espacio de nombres registrado: {uri} con índice: {idx}")
    # populating our address space
    myobj1 = server.nodes.objects.add_object(idx, "Robot1")
    myrob1_posx = myobj1.add_variable(idx, "R1Pos_x",0)
    myrob1_posy = myobj1.add_variable(idx, "R1Pos_y", 0)
    myrob1_posx.set_writable()    # Set MyVariable to be writable by clients
    myrob1_posy.set_writable()  # Set MyVariable to be writable by clients
    myobj2 = server.nodes.objects.add_object(idx, "Robot2")
    myrob2_posx = myobj2.add_variable(idx, "R2Pos_x", 0)
    myrob2_posy = myobj2.add_variable(idx, "R2Pos_y", 0)
    myrob2_posx.set_writable()  # Set MyVariable to be writable by clients
    myrob2_posy.set_writable()  # Set MyVariable to be writable by clients
    server.start()
    try:
        count = 0
        while True:
            time.sleep(1)
            count += 1
            myrob1_posx.write_value(count)
            myrob1_posy.write_value(count+10)
    finally:
        #close connection, remove subscriptions, etc
        server.stop()