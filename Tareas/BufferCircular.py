import collections as cls
import threading

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
            for element in self.data:
                print(element)

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