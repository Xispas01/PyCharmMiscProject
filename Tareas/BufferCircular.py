import collections as cls
import random
import threading
import time


class BufferFIFO():
    def __init__(self,size:int = 10):
        self.bufferLock = threading.Condition()

        self.count = 0
        self.size = size

        self.data = []

    def insert(self,element) -> bool:
        self.bufferLock.acquire()

        while self.count >= self.size:
            self.bufferLock.wait()

        self.data.append(element)
        self.count += 1

        self.bufferLock.notify_all()
        self.bufferLock.release()

        return True

    def remove(self):
        self.bufferLock.acquire()

        while self.count <= 0:
            self.bufferLock.wait()

        element = self.data.pop(0)
        self.count -= 1

        self.bufferLock.notify_all()
        self.bufferLock.release()

        return element

    def look(self,FirstIn:bool = True):
        self.bufferLock.acquire()

        while self.count <= 0:
            self.bufferLock.wait()

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

def Produce(buffer):
    while True:
        time.sleep((random.random()+1)*2)
        dato = random.randint(0,100)
        buffer.insert(dato)
        print('Elemento con valor %3d Insertado' % (dato))

def Consume(buffer):
    while True:
        time.sleep((random.random()+1)*2)
        print('Elemento con valor %3d extraido' % (buffer.remove()))

def Visual(buffer):
    while True:
         buffer.list()
         time.sleep(1)

if __name__ == '__main__':

    buffer = BufferFIFO()
    hilosConsumidoresProductores = [threading.Thread(name='Visualizador',target=Visual,args=(buffer,))]

    for i in range(6):
        hilosConsumidoresProductores.append(threading.Thread(name=("Generador %d" % (i)),target=Produce,args=(buffer,)))

    for i in range(6):
        hilosConsumidoresProductores.append(threading.Thread(name=("Consumidor %d" % (i)),target=Consume,args=(buffer,)))


    for hilo in hilosConsumidoresProductores:
        hilo.start()
