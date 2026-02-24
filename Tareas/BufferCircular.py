#Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza

import collections as cls
import random
import threading
import time

Visualizar = True

cls.deque([],10)
class BufferFIFO():
    def __init__(self,size:int = 10):
        self.bufferLock = threading.RLock()
        self.hasSpace = threading.Condition(lock=self.bufferLock)
        self.hasItem = threading.Condition(lock=self.bufferLock)

        self.count = 0
        self.size = size

        self.data = []

    def insert(self,element) -> bool:
        self.bufferLock.acquire()

        while self.count >= self.size:
            self.hasSpace.wait()

        self.data.append(element)
        self.count += 1

        self.hasItem.notify(1)
        self.bufferLock.release()

        return True

    def remove(self):
        self.bufferLock.acquire()

        while self.count <= 0:
            self.hasItem.wait()

        element = self.data.pop(0)
        self.count -= 1

        self.hasSpace.notify(1)
        self.bufferLock.release()

        return element

    def look(self,FirstIn:bool = True):
        self.bufferLock.acquire()

        while self.count <= 0:
            self.hasItem.wait()

        if FirstIn:
            element = self.data[0]
        else:
            element = self.data[self.count-1]

        self.bufferLock.release()

        return element

    def list(self) -> None:
        self.bufferLock.acquire()

        if self.isEmpty():
            print("Lista Vacia")
        else:
            print("----------Lista----------")
            for index,element in enumerate(self.data):
                print("Item %d = %d" % (index,element))

            print("--------Fin Lista--------")

        self.bufferLock.release()

    def isFull(self)->bool:
        self.bufferLock.acquire()
        v = self.count == self.size
        self.bufferLock.release()

        return v

    def isEmpty(self)->bool:
        self.bufferLock.acquire()
        v = self.count == 0
        self.bufferLock.release()

        return v

def Produce(buffer,N,id):
    Entries = 1
    Objective = N + Entries
    while Entries < Objective:
        time.sleep((random.random()+1)*2)
        dato = id + Entries
        buffer.insert(dato)
        print('Elemento con valor %3d Insertado' % (dato))
        Entries +=1

def Consume(buffer,N,id):
    Entries = 1
    Objective = N + Entries
    while Entries < Objective:
        time.sleep((random.random()+1)*2)
        print('Elemento con valor %3d extraido por hilo id: %3d, extraccion %2d' % (buffer.remove(),id,Entries))
        Entries +=1

def Visual(buffer):
    while Visualizar:
         buffer.list()
         time.sleep(1)

if __name__ == '__main__':

    buffer = BufferFIFO()
    hilosConsumidoresProductores = []
    hiloVisual = threading.Thread(name='Visualizador',target=Visual,args=(buffer,))
    N = 10

    for i in range(6):
        hilosConsumidoresProductores.append(threading.Thread(name=("Generador %d" % (i)),target=Produce,args=(buffer,N,(i+1)*100,)))
    for i in range(6):
        hilosConsumidoresProductores.append(threading.Thread(name=("Consumidor %d" % (i)),target=Consume,args=(buffer,N,(i+1)*100,)))


    for hilo in hilosConsumidoresProductores:
        hilo.start()
    hiloVisual.start()

    for hilo in hilosConsumidoresProductores:
        hilo.join()
    Visualizar = False

    hiloVisual.join()

    exit(0)
