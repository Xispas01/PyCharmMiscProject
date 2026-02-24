# Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza


import socket
import tkinter as tk
import threading


# Función para obtener la IP real del ordenador en la red local
def obtener_mi_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # No necesita conexión real, solo detecta la interfaz activa
        s.connect(('8.8.8.8', 1))
        ip = s.getsockname()[0]
    except Exception:
        ip = '127.0.0.1'
    finally:
        s.close()
    return ip


def escuchar():
    global listening, server_socket, clientes_conectados
    puerto = 4096
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        server_socket.bind(('0.0.0.0', puerto))

        # Mostramos los datos necesarios para el cliente
        mi_ip = obtener_mi_ip()
        cuadro_texto_destino.insert(tk.END, f"--- DATOS PARA EL CLIENTE ---\n")
        cuadro_texto_destino.insert(tk.END, f"IP: {mi_ip}  |  PUERTO: {puerto}\n")
        cuadro_texto_destino.insert(tk.END, "-----------------------------\n")
        cuadro_texto_destino.yview_moveto(1.0)

        while listening:
            # El socket se queda esperando datos aquí
            data, addr = server_socket.recvfrom(1024)
            mensaje = data.decode('utf-8')

            # 1. Registrar al cliente si es la primera vez que escribe
            if addr not in clientes_conectados:
                clientes_conectados.add(addr)

            # Mostrar en la interfaz del servidor
            texto_final = f"Desde {addr[0]}:{addr[1]} -> {mensaje}\n"
            cuadro_texto_destino.insert(tk.END, texto_final)
            cuadro_texto_destino.yview_moveto(1.0)

            # 2. Reenviar el mensaje al resto de clientes conectados
            for cliente in clientes_conectados:
                # Opcional: Si no quieres que el mensaje le rebote al que lo envió, descomenta el 'if'
                # if cliente != addr:
                try:
                    server_socket.sendto(texto_final.encode('utf-8'), cliente)
                except Exception:
                    pass  # Ignoramos si falla el reenvío a un cliente específico

    except Exception as e:
        # Al cerrar el socket desde fuera, saltará un error aquí y terminará el hilo limpiamente
        if listening:
            cuadro_texto_destino.insert(tk.END, f"Error: {e}\n")
    finally:
        server_socket.close()


def iniciar_hilo():
    global listening, server_socket
    if not listening:
        # ACTIVAR
        listening = True
        boton_conectar.config(text="Desactivar Servidor", bg="red", fg="white")
        thread = threading.Thread(target=escuchar, daemon=True)
        thread.start()
    else:
        # DESACTIVAR
        listening = False
        boton_conectar.config(text="Activar Servidor", bg="SystemButtonFace", fg="black")
        # Forzamos el cierre del socket para desbloquear el recvfrom
        if server_socket:
            server_socket.close()
        cuadro_texto_destino.insert(tk.END, ">>> Servidor Detenido.\n")


if __name__ == '__main__':
    # Variables de control global
    listening = False
    server_socket = None

    # 3. Añadimos un conjunto (set) para guardar las direcciones de los clientes
    clientes_conectados = set()

    ventana = tk.Tk()
    ventana.title("SERVIDOR UDP")

    tk.Label(ventana, text='Historial de mensajes recibidos:').grid(row=0, column=0)

    cuadro_texto_destino = tk.Text(ventana, height=15, width=50)
    cuadro_texto_destino.grid(row=1, column=0, columnspan=2)

    scrollbar = tk.Scrollbar(ventana, command=cuadro_texto_destino.yview)
    scrollbar.grid(row=1, column=2, sticky=tk.NS)
    cuadro_texto_destino.config(yscrollcommand=scrollbar.set)

    # Botón para activar la escucha
    boton_conectar = tk.Button(ventana, text="Activar Servidor", command=iniciar_hilo)
    boton_conectar.grid(row=2, column=0, columnspan=2, pady=10)

    # Control de salida forzada
    try:
        ventana.mainloop()
    except KeyboardInterrupt:
        print("Terminado por orden del usuario")
    except Exception as e:
        print("Error en el programa: \n", e)