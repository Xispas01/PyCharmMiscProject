import socket
import threading
import tkinter as tk
from tkinter import scrolledtext

#Estado global
dicc_conexiones_establecidas = {'None': None}

# Referencias a widgets (se asignan en main())
ventana = None
texto_mensajes = None
opcion_seleccionada = None
desplegable_seleccion_conexion = None
entry_puerto_servidor = None
entry_ip_destino = None
entry_puerto_destino = None
entry_mensaje = None


#Metodos de Utilidades

def mostrar_mensaje(msg: str):
    """Añade una línea al área de texto de forma thread-safe."""
    def _insert():
        texto_mensajes.config(state=tk.NORMAL)
        texto_mensajes.insert(tk.END, msg + '\n')
        texto_mensajes.see(tk.END)
        texto_mensajes.config(state=tk.DISABLED)
    ventana.after(0, _insert)


def actualizar_opciones_desplegable():
    """Reconstruye el menú desplegable con las conexiones actuales."""
    def _update():
        desplegable_seleccion_conexion['menu'].delete(0, 'end')
        for opcion in dicc_conexiones_establecidas.keys():
            desplegable_seleccion_conexion['menu'].add_command(
                label=opcion,
                command=lambda v=opcion: opcion_seleccionada.set(v)
            )
    ventana.after(0, _update)


#Lógica de red

def hilo_recibir_mensajes(conexion: socket.socket, direccion_puerto: str):
    #Bucle de recepción continua para una conexión activa.
    while True:
        try:
            datos = conexion.recv(1024)
            if not datos:
                mostrar_mensaje(f"Conexión {direccion_puerto} cerrada por el remoto.")
                break
            mostrar_mensaje(
                f"Mensaje recibido por conexión {direccion_puerto}: {datos.decode('utf-8', errors='replace')}"
            )
        except socket.error:
            mostrar_mensaje(f"Error en conexión {direccion_puerto}. Conexión cerrada.")
            break

    # Limpiar del diccionario si aún existe
    if direccion_puerto in dicc_conexiones_establecidas:
        del dicc_conexiones_establecidas[direccion_puerto]
        actualizar_opciones_desplegable()


def hilo_servidor(puerto: int):
    """Hilo principal del servidor: acepta conexiones indefinidamente."""
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    try:
        servidor.bind(('0.0.0.0', puerto))
        servidor.listen(5)
        mostrar_mensaje(f"Hola esperando aceptar conexiones por {puerto}")

        while True:
            try:
                conexion, direccion = servidor.accept()
                dir_puerto = f"{direccion[0]}:{direccion[1]}"
                mostrar_mensaje(f"Nueva conexión {dir_puerto} establecida")
                dicc_conexiones_establecidas[dir_puerto] = conexion
                actualizar_opciones_desplegable()

                t = threading.Thread(
                    target=hilo_recibir_mensajes,
                    args=(conexion, dir_puerto),
                    daemon=True
                )
                t.start()
            except socket.error:
                break
    except Exception as e:
        mostrar_mensaje(f"Error al iniciar servidor: {e}")
    finally:
        servidor.close()


# Comportamientos de botones

def iniciar_servidor():
    puerto_str = entry_puerto_servidor.get().strip()
    if not puerto_str.isdigit():
        mostrar_mensaje("⚠ Puerto servidor inválido.")
        return
    t = threading.Thread(target=hilo_servidor, args=(int(puerto_str),), daemon=True)
    t.start()


def conectar():
    ip = entry_ip_destino.get().strip()
    puerto_str = entry_puerto_destino.get().strip()
    if not ip or not puerto_str.isdigit():
        mostrar_mensaje("⚠ IP o puerto destino inválidos.")
        return

    puerto = int(puerto_str)
    dir_puerto = f"{ip}:{puerto}"

    if dir_puerto in dicc_conexiones_establecidas:
        mostrar_mensaje(f"⚠ Ya existe una conexión con {dir_puerto}.")
        return

    conexion = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        conexion.connect((ip, puerto))
        mostrar_mensaje(f"Nueva conexión {dir_puerto} establecida")
        dicc_conexiones_establecidas[dir_puerto] = conexion
        actualizar_opciones_desplegable()

        t = threading.Thread(
            target=hilo_recibir_mensajes,
            args=(conexion, dir_puerto),
            daemon=True
        )
        t.start()
    except socket.error as e:
        mostrar_mensaje(f"Error al conectar con {dir_puerto}: {e}")


def enviar_mensaje():
    dir_puerto = opcion_seleccionada.get()
    if dir_puerto in ('Conexiones', 'None', ''):
        mostrar_mensaje("Selecciona una conexión.")
        return
    conexion = dicc_conexiones_establecidas.get(dir_puerto)
    if conexion is None:
        mostrar_mensaje("Conexión no válida.")
        return
    mensaje = entry_mensaje.get()
    try:
        conexion.send(mensaje.encode('utf-8'))
        mostrar_mensaje(f"Enviado por conexión {dir_puerto} el mensaje: {mensaje}")
    except socket.error as e:
        mostrar_mensaje(f"Error al enviar a {dir_puerto}: {e}")


def cerrar_conexion():
    dir_puerto = opcion_seleccionada.get()
    if dir_puerto in ('Conexiones', 'None', ''):
        mostrar_mensaje("Selecciona una conexión.")
        return
    conexion = dicc_conexiones_establecidas.get(dir_puerto)
    if conexion is not None:
        try:
            conexion.close()
        except Exception:
            pass
        del dicc_conexiones_establecidas[dir_puerto]
        mostrar_mensaje(f"Cerrada conexión {dir_puerto} y finalizado hilo")
        actualizar_opciones_desplegable()
        opcion_seleccionada.set('Conexiones')


#Construcción de la interfaz

def main():
    global ventana, texto_mensajes, opcion_seleccionada, desplegable_seleccion_conexion
    global entry_puerto_servidor, entry_ip_destino, entry_puerto_destino, entry_mensaje

    ventana = tk.Tk()
    ventana.title("Enviar y recibir mensajes TCP")
    ventana.resizable(False, False)

    # Fuente por defecto
    font_label  = ('Helvetica', 10)
    font_bold   = ('Helvetica', 10, 'bold')
    font_btn    = ('Helvetica', 10)

    PAD = dict(padx=8, pady=3)

    #Separador superior
    tk.Frame(ventana, height=4, bd=1, relief=tk.SUNKEN).grid(
        row=0, column=0, columnspan=3, sticky='ew')

    #Sección SERVIDOR
    tk.Label(ventana, text="SERVIDOR PARA ACEPTAR NUEVAS CONEXIONES",
             font=font_bold).grid(row=1, column=0, columnspan=3, pady=(6, 2))

    tk.Label(ventana, text="Puerto servidor:", font=font_label).grid(
        row=2, column=0, sticky='e', **PAD)
    entry_puerto_servidor = tk.Entry(ventana, width=32)
    entry_puerto_servidor.grid(row=2, column=1, columnspan=2, sticky='w', **PAD)

    tk.Button(ventana, text="Iniciar servidor", font=font_btn,
              width=18, command=iniciar_servidor).grid(
        row=3, column=0, columnspan=3, pady=5)

    #Separador
    tk.Frame(ventana, height=4, bd=1, relief=tk.SUNKEN).grid(
        row=4, column=0, columnspan=3, sticky='ew')

    #Sección NUEVA CONEXIÓN
    tk.Label(ventana, text="NUEVA CONEXIÓN",
             font=font_bold).grid(row=5, column=0, columnspan=3, pady=(6, 2))

    tk.Label(ventana, text="IP destino:", font=font_label).grid(
        row=6, column=0, sticky='e', **PAD)
    entry_ip_destino = tk.Entry(ventana, width=32)
    entry_ip_destino.grid(row=6, column=1, columnspan=2, sticky='w', **PAD)

    tk.Label(ventana, text="Puerto destino:", font=font_label).grid(
        row=7, column=0, sticky='e', **PAD)
    entry_puerto_destino = tk.Entry(ventana, width=32)
    entry_puerto_destino.grid(row=7, column=1, columnspan=2, sticky='w', **PAD)

    tk.Button(ventana, text="Conectar", font=font_btn,
              width=14, command=conectar).grid(
        row=8, column=0, columnspan=3, pady=5)


    tk.Frame(ventana, height=4, bd=1, relief=tk.SUNKEN).grid(
        row=9, column=0, columnspan=3, sticky='ew')

    # Área de texto (mensajes)
    texto_mensajes = scrolledtext.ScrolledText(
        ventana, width=58, height=14, state=tk.DISABLED,
        font=('Courier', 9), wrap=tk.WORD
    )
    texto_mensajes.grid(row=10, column=0, columnspan=3, padx=8, pady=6)


    tk.Frame(ventana, height=4, bd=1, relief=tk.SUNKEN).grid(
        row=11, column=0, columnspan=3, sticky='ew')

    # Sección OPERACIONES CON CONEXIÓN
    tk.Label(ventana, text="OPERACIONES CON CONEXIÓN",
             font=font_bold).grid(row=12, column=0, columnspan=3, pady=(6, 2))

    tk.Label(ventana, text="Seleccionar conexión:", font=font_label).grid(
        row=13, column=0, sticky='e', **PAD)
    opcion_seleccionada = tk.StringVar(value='Conexiones')
    desplegable_seleccion_conexion = tk.OptionMenu(ventana, opcion_seleccionada, None)
    desplegable_seleccion_conexion.config(font=font_label, width=18)
    desplegable_seleccion_conexion.grid(row=13, column=1, sticky='w', **PAD)

    tk.Label(ventana, text="Mensaje:", font=font_label).grid(
        row=14, column=0, sticky='e', **PAD)
    entry_mensaje = tk.Entry(ventana, width=32)
    entry_mensaje.grid(row=14, column=1, columnspan=2, sticky='w', **PAD)

    tk.Button(ventana, text="Enviar mensaje", font=font_btn,
              width=16, command=enviar_mensaje).grid(
        row=15, column=0, columnspan=3, pady=4)

    tk.Button(ventana, text="Cerrar conexión", font=font_btn,
              width=16, command=cerrar_conexion).grid(
        row=16, column=0, columnspan=3, pady=(0, 8))

    # Inicializar desplegable
    actualizar_opciones_desplegable()

    ventana.mainloop()


if __name__ == '__main__':
    main()