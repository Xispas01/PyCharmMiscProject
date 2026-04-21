import time
from asyncua.sync import Client
if __name__ == "__main__":
    with Client("opc.tcp://localhost:4840/freeopcua/server/") as client:
        client.load_data_type_definitions()  # load definition of server specific structures/extension objects
        # Client has a few methods to get proxy to UA nodes that should always be in address space such as Root or Objects
        print("Objects node is: ", client.nodes.objects)
        print("Children of root are: ", client.nodes.root.get_children())
        myvar_posx1 = client.nodes.root.get_child(["0:Objects", "2:Robot1", "2:R1Pos_x"])
        obj = client.nodes.root.get_child(["0:Objects", "2:Robot1"])
        print("myvar is: ", myvar_posx1)
        print("myobj is: ", obj)
        myvar_posx1.write_value(100)
        print("El valor leido es: ", myvar_posx1.read_value())
        count = 0
        while True:
            time.sleep(1)
            print("El valor en la iteracion ", myvar_posx1.read_value())