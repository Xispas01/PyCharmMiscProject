#Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza
import threading
import time
import random
import matplotlib.pyplot as plt
import matplotlib.animation as animation

visualizar = False

MAX_VALOR = 20
MIN_VALOR = 0
DATOS_VISUALIZADOS = 750
class Grafica ():
    def __init__(self,):
        self.datos_grafica = []
        self.datos_grafica.append([0])
        self.datos_grafica.append([0])
        #Configuramos la gráfica
        self.fig = plt.figure()
        self.ax = self.fig.add_subplot(111)
        self.hl, = plt.plot(self.datos_grafica[0],self.datos_grafica[1])
        plt.ylim(MIN_VALOR-1, MAX_VALOR+1)
        plt.xlim(0, DATOS_VISUALIZADOS)
    def visualizar_nuevo_valor(self, new_valor):
        self.datos_grafica[1].append(float(new_valor))
        if len(self.datos_grafica[1]) > DATOS_VISUALIZADOS:
            self.datos_grafica[1].pop(0)
    # Función que actualizará los datos de la gráfica
    # Se llama periódicamente desde el 'FuncAnimation'
    def update_line(self, num, hl, data):
        hl.set_data(range(len(data[1])), data[1])
        return hl,

    def iniciar_grafica_animada(self):
        line_ani = animation.FuncAnimation(self.fig,self.update_line, fargs=(self.hl,self.datos_grafica), interval=50, blit=False)
        plt.show()  # Es bloqueante

class  Contenedor:
    def __init__(self):
        self.var_compartida = 0
        self.monitor = threading.Condition()

    def incrementar(self):
        self.monitor.acquire()

        while self.var_compartida >= 20:
            self.monitor.wait()

        self.var_compartida += 1
        self.monitor.notify_all()
        self.monitor.release()

    def decrementar(self) :
        self.monitor.acquire()

        while self.var_compartida <= 0:
            self.monitor.wait()

        self.var_compartida -= 1
        self.monitor.notify_all()
        self.monitor.release()

    def leer_valor(self) -> int :

        self.monitor.acquire()
        v = self.var_compartida
        self.monitor.release()
        return v

def Produce(contenedor):
    while True:
        time.sleep(random.random())
        contenedor.incrementar()

def Consume(contenedor):
    while True:
        time.sleep(random.random())
        contenedor.decrementar()

def Visual(contenedor, grafica):
    while visualizar:
         valor = contenedor.leer_valor()
         grafica.visualizar_nuevo_valor(valor)
         time.sleep(0.1)

if __name__ == '__main__':
    container = Contenedor()
    grafica = Grafica()

    hilo_generador = threading.Thread(name='Generador',target=Produce,args=(container,))
    hilo_consumidor = threading.Thread(name='Consumidor',target=Consume,args=(container,))
    hilo_visualizador = threading.Thread(name='Visualizador',target=Visual,args=(container, grafica,))

    visualizar = True
    hilo_generador.start()
    hilo_consumidor.start()
    hilo_visualizador.start()

    grafica.iniciar_grafica_animada()  # Llamada bloqueante