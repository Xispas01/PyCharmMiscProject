# Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza

import socket
import threading
import tkinter as tk
from tkinter import messagebox
import pickle
import uuid


class AplicacionUDP:
    def __init__(self, root):
        self.root = root
        self.root.title("Chat UDP - ReSiDiCo")

        # Variables de control de red
        self.socket_escucha = None
        self.hilo_recepcion = None
        self.ejecutando = False
        self.mensajes_recibidos = set()  # Para deduplicación (IDs únicos)
        self.nodos_registrados = set()  # Guardará tuplas (IP, Puerto_Escucha)

        self.setup_gui()
        # Iniciamos en modo Cliente por defecto
        self.cambiar_modo("Cliente")

    def setup_gui(self):
        # 1. Modo de funcionamiento (No editable)
        tk.Label(self.root, text='Modo Actual:').grid(row=0, column=0, sticky="e")
        self.var_modo = tk.StringVar(value="Cliente")
        self.entry_modo_actual = tk.Entry(self.root, textvariable=self.var_modo, state='readonly',
                                          readonlybackground="lightgrey")
        self.entry_modo_actual.grid(row=0, column=1, sticky="w")

        # 2. Configuración de Puertos (Clave para evitar conflictos)
        tk.Label(self.root, text='Mi Puerto Escucha:').grid(row=1, column=0, sticky="e")
        self.entry_puerto_local = tk.Entry(self.root)
        self.entry_puerto_local.insert(0, "10001")
        self.entry_puerto_local.grid(row=1, column=1, sticky="w")

        tk.Label(self.root, text='IP Destino:').grid(row=2, column=0, sticky="e")
        self.entry_ip_dest = tk.Entry(self.root)
        self.entry_ip_dest.insert(0, "127.0.0.1")
        self.entry_ip_dest.grid(row=2, column=1, sticky="w")

        tk.Label(self.root, text='Puerto Destino:').grid(row=2, column=2, sticky="e")
        self.entry_puerto_dest = tk.Entry(self.root)
        self.entry_puerto_dest.insert(0, "10002")
        self.entry_puerto_dest.grid(row=2, column=3, sticky="w")

        # 3. Selector de Modo
        tk.Label(self.root, text='Cambiar a:').grid(row=3, column=0, sticky="e")
        self.selector_modo = tk.OptionMenu(self.root, self.var_modo, "Cliente", "Servidor", "Cliente/Servidor",
                                           command=self.cambiar_modo)
        self.selector_modo.grid(row=3, column=1, sticky="w")

        # 4. Entrada de texto
        tk.Label(self.root, text='Escribir texto:').grid(row=4, column=0, sticky="e")
        self.cuadro_texto_origen = tk.Entry(self.root, width=40)
        self.cuadro_texto_origen.grid(row=4, column=1, columnspan=2)

        # 5. Botón Enviar
        self.boton_enviar = tk.Button(self.root, text="Enviar / Copiar Texto", command=self.boton_click)
        self.boton_enviar.grid(row=5, column=0, columnspan=4, pady=5)

        # 6. Cuadro de texto destino (Historial)
        self.cuadro_texto_destino = tk.Text(self.root, height=10, width=60)
        self.cuadro_texto_destino.grid(row=6, column=0, columnspan=4, padx=5)

        self.scrollbar = tk.Scrollbar(self.root, command=self.cuadro_texto_destino.yview)
        self.scrollbar.grid(row=6, column=4, sticky=tk.NS)
        self.cuadro_texto_destino.config(yscrollcommand=self.scrollbar.set)

    def cambiar_modo(self, modo):
        """Cierra el socket anterior y abre uno nuevo si el modo requiere escucha."""
        self.detener_escucha()

        if modo in ["Servidor", "Cliente/Servidor"]:
            try:
                puerto = int(self.entry_puerto_local.get())
                self.socket_escucha = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.socket_escucha.bind(('', puerto))

                self.ejecutando = True
                self.hilo_recepcion = threading.Thread(target=self.hilo_escucha_udp, daemon=True)
                self.hilo_recepcion.start()
                self.insertar_mensaje(f"SISTEMA: Escuchando en puerto {puerto}")
            except Exception as e:
                messagebox.showerror("Error de Bind", f"No se pudo abrir el puerto {puerto}: {e}")
                self.var_modo.set("Cliente")  # Revertir si falla

    def hilo_escucha_udp(self):
        """Bucle de recepción de datos."""
        while self.ejecutando:
            try:
                data, addr = self.socket_escucha.recvfrom(4096)
                mensaje_dict = pickle.loads(data)

                msg_id = mensaje_dict.get('id')
                # SEGURIDAD: Descartar si ya se ha recibido (Deduplicación)
                if msg_id in self.mensajes_recibidos:
                    continue

                self.mensajes_recibidos.add(msg_id)

                # Registro automático del remitente para reenvíos
                # Usamos el puerto de escucha que el remitente nos envía en el paquete
                remitente_info = (addr[0], mensaje_dict['puerto_origen'])
                self.nodos_registrados.add(remitente_info)

                # Mostrar en pantalla
                self.insertar_mensaje(f"[{remitente_info[0]}:{remitente_info[1]}] {mensaje_dict['texto']}")

                # REENVÍO (Forwarding)
                if self.var_modo.get() in ["Servidor", "Cliente/Servidor"]:
                    self.reenviar_paquete(mensaje_dict, remitente_info)

            except:
                break

    def boton_click(self):
        """Envía el texto y lo añade localmente."""
        texto = self.cuadro_texto_origen.get()
        if not texto: return

        puerto_local = int(self.entry_puerto_local.get())

        # Crear paquete con ID único
        paquete = {
            'id': str(uuid.uuid4()),
            'texto': texto,
            'puerto_origen': puerto_local  # Para que los demás sepan a qué puerto responder
        }

        ip_dest = self.entry_ip_dest.get()
        puerto_dest = int(self.entry_puerto_dest.get())

        try:
            # Enviamos usando un socket temporal si no somos servidor, o el de escucha si lo somos
            sock_envio = self.socket_escucha if self.socket_escucha else socket.socket(socket.AF_INET,
                                                                                       socket.SOCK_DGRAM)
            sock_envio.sendto(pickle.dumps(paquete), (ip_dest, puerto_dest))

            self.mensajes_recibidos.add(paquete['id'])  # Evitar procesarlo si nos lo reenvían
            self.insertar_mensaje(f"Yo: {texto}")
            self.cuadro_texto_origen.delete(0, tk.END)
        except Exception as e:
            self.insertar_mensaje(f"Error al enviar: {e}")

    def reenviar_paquete(self, paquete, remitente_addr):
        """Reenvía el paquete a todos los nodos conocidos excepto al que lo envió."""
        data = pickle.dumps(paquete)
        for nodo in self.nodos_registrados:
            if nodo != remitente_addr:
                try:
                    self.socket_escucha.sendto(data, nodo)
                except:
                    pass

    def insertar_mensaje(self, msg):
        self.cuadro_texto_destino.insert(tk.END, msg + '\n')
        self.cuadro_texto_destino.yview_moveto(1.0)

    def detener_escucha(self):
        self.ejecutando = False
        if self.socket_escucha:
            self.socket_escucha.close()
            self.socket_escucha = None


if __name__ == '__main__':
    ventana = tk.Tk()
    app = AplicacionUDP(ventana)

    # Control de salida forzada solicitado
    try:
        ventana.mainloop()
    except KeyboardInterrupt:
        print("Terminado por orden del usuario")
    except Exception as e:
        print("Error en el programa: \n", e)
    finally:
        app.detener_escucha()