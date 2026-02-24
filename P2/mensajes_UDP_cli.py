#Editores:
# Alejandro Mancebo Arnal
# Jose Ginemo Niza

import socket
import tkinter as tk
import threading

# Variable global para el socket y control
client_socket = None
listening = False


def recibir_mensajes():
    """Hilo que escucha respuestas del servidor o de otros clientes."""
    global listening, client_socket
    while listening:
        try:
            # Buffer de 1024 bytes
            data, addr = client_socket.recvfrom(1024)
            mensaje = data.decode('utf-8')

            # Insertar en el cuadro de texto de destino
            cuadro_texto_destino.insert(tk.END, f"Recibido de {addr}: {mensaje}\n")
            cuadro_texto_destino.yview_moveto(1.0)
        except:
            # Si el socket se cierra, salimos del bucle
            break


def enviar_mensaje():
    """Envía el texto a la IP y puerto especificados."""
    global client_socket, listening

    ip_dest = entry_ip.get()
    puerto_dest = int(entry_puerto.get())
    texto = cuadro_texto_origen.get()

    if texto:
        try:
            # Si es la primera vez que enviamos, inicializamos el socket y el hilo de escucha
            if client_socket is None:
                client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                # Opcional: bind a puerto 0 para que el SO asigne uno libre automáticamente
                client_socket.bind(('', 0))
                listening = True
                hilo_recibo = threading.Thread(target=recibir_mensajes, daemon=True)
                hilo_recibo.start()

            # Enviar datos
            server_address = (ip_dest, puerto_dest)
            client_socket.sendto(texto.encode('utf-8'), server_address)

            # Reflejar en la interfaz local
            cuadro_texto_destino.insert(tk.END, f"Tú -> {ip_dest}:{puerto_dest}: {texto}\n")
            cuadro_texto_destino.yview_moveto(1.0)
            cuadro_texto_origen.delete(0, tk.END)

        except Exception as e:
            cuadro_texto_destino.insert(tk.END, f"Error: {e}\n")


if __name__ == '__main__':
    ventana = tk.Tk()
    ventana.title("CLIENTE UDP MULTI-INSTANCIA")

    # --- Configuración de Destino (Faltaba en tu código) ---
    frame_config = tk.Frame(ventana)
    frame_config.grid(row=0, column=0, columnspan=2, pady=5)

    tk.Label(frame_config, text="IP Destino:").pack(side=tk.LEFT)
    entry_ip = tk.Entry(frame_config, width=15)
    entry_ip.insert(0, "127.0.0.1")
    entry_ip.pack(side=tk.LEFT, padx=5)

    tk.Label(frame_config, text="Puerto:").pack(side=tk.LEFT)
    entry_puerto = tk.Entry(frame_config, width=8)
    entry_puerto.insert(0, "4096")
    entry_puerto.pack(side=tk.LEFT, padx=5)

    # --- Entrada de mensaje ---
    tk.Label(ventana, text='Escribir texto:').grid(row=1, column=0, sticky="e")
    cuadro_texto_origen = tk.Entry(ventana, width=40)
    cuadro_texto_origen.grid(row=1, column=1, padx=5, pady=5)

    # --- Botón de envío ---
    boton = tk.Button(ventana, text="Enviar Mensaje", command=enviar_mensaje, bg="lightblue")
    boton.grid(row=2, column=0, columnspan=2, pady=5)

    # --- Historial / Destino ---
    cuadro_texto_destino = tk.Text(ventana, height=12, width=60)
    cuadro_texto_destino.grid(row=3, column=0, columnspan=2, padx=10, pady=5)

    scrollbar = tk.Scrollbar(ventana, command=cuadro_texto_destino.yview)
    scrollbar.grid(row=3, column=2, sticky=tk.NS)
    cuadro_texto_destino.config(yscrollcommand=scrollbar.set)

    try:
        ventana.mainloop()
    except KeyboardInterrupt:
        print("Cerrando...")
    finally:
        listening = False
        if client_socket:
            client_socket.close()