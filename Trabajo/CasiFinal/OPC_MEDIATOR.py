import asyncio
import sys
from asyncua import Client, Node, ua

# ==========================================
# CONFIGURACIÓN DEL CLIENTE
# ==========================================
OPC_URL = "opc.tcp://localhost:4840/upv/jgimniz/"
PROMPT = "OPC-UA> "


# ==========================================
# FUNCIONES AUXILIARES DE CONSOLA
# ==========================================
def print_async(mensaje):
    """
    Imprime un mensaje sin romper el indicador de escritura del usuario.
    Usa secuencias ANSI (\r retorna al inicio, \033[K borra hasta el final de la línea).
    """
    sys.stdout.write(f"\r\033[K{mensaje}\n{PROMPT}")
    sys.stdout.flush()


# ==========================================
# MANEJADOR DE SUSCRIPCIONES (DataChange)
# ==========================================
class DataChangeHandler:
    def datachange_notification(self, node: Node, val, data):
        node_id = node.nodeid.to_string()
        print_async(f"[🔄 NOTIFICACIÓN] Nodo {node_id} cambió dinámicamente a: {val}")


# ==========================================
# EXPLORACIÓN Y FILTRADO DEL ÁRBOL
# ==========================================
async def browse_and_print(node: Node, sub=None, level: int = 0, subscribe: bool = False):
    """
    Recorre la estructura de forma jerárquica.
    Si 'subscribe' es True, añade los tags a las notificaciones en tiempo real.
    """
    try:
        children = await node.get_children()
        for child in children:
            node_class = await child.read_node_class()
            name = (await child.read_display_name()).Text
            node_id = child.nodeid.to_string()
            indent = "    " * level

            if node_class == ua.NodeClass.Object:
                print(f"{indent}📂 [Objeto] {name} | NodeID: {node_id}")
                await browse_and_print(child, sub, level + 1, subscribe)

            elif node_class == ua.NodeClass.Variable:
                try:
                    val = await child.read_value()
                    val_type = type(val).__name__
                    print(f"{indent}📄 [Tag] {name} | Tipo: {val_type} | NodeID: {node_id} | Valor actual: {val}")

                    # Solo suscribirse la primera vez (evita duplicados en los REFRESH)
                    if subscribe and sub is not None:
                        await sub.subscribe_data_change(child)
                except ua.UaError as e:
                    print(f"{indent}⚠️ [Error leyendo tag] {name}: {e}")

    except Exception as e:
        print(f"Error explorando el nodo: {e}")


# ==========================================
# CONSOLA INTERACTIVA CON COMANDOS
# ==========================================
async def interactive_console(client: Client, planta_node: Node, sub):
    """
    Procesa las entradas de consola filtrando por REFRESH, UPDATE y TARGET.
    """
    loop = asyncio.get_running_loop()
    print("\n" + "=" * 65)
    print("💻 CONSOLA DE CONTROL - FILTRADO POR OBJETO 'PLANTA'")
    print("Comandos aceptados:")
    print("  1. REFRESH                 -> Muestra la estructura actualizada.")
    print("  2. UPDATE NodeID=Valor     -> Sobrescribe un tag específico.")
    print("  3. TARGET Robot X Y        -> Actualiza destino (Ej: TARGET R3 150 75)")
    print("  4. QUIT                    -> Finaliza la ejecución.")
    print("=" * 65 + "\n")

    while True:
        # Pinta el indicador de escritura antes de quedarse bloqueado esperando
        sys.stdout.write(PROMPT)
        sys.stdout.flush()

        # Espera la entrada del usuario sin bloquear el Event Loop
        comando = await loop.run_in_executor(None, sys.stdin.readline)
        comando = comando.strip()

        if not comando:
            continue

        if comando.lower() in ('q', 'quit', 'exit'):
            print("\nCerrando consola interactiva...")
            break

        # 1. COMANDO REFRESH
        if comando.upper() == 'REFRESH':
            print("\n🔄 [REFRESH] Solicitando valores actualizados al servidor...")
            print(f"📂 [Raíz] Planta")
            # Volvemos a escanear e imprimir pero con subscribe=False para no duplicar listeners
            await browse_and_print(planta_node, sub, level=1, subscribe=False)
            print("-" * 40 + "\n")
            continue

        # 2. COMANDO UPDATE
        elif comando.upper().startswith('UPDATE '):
            argumentos = comando[7:].strip()

            if '=' not in argumentos:
                print("❌ Formato incorrecto. Debe ser: UPDATE NodeID=Valor (Ejemplo: UPDATE ns=2;i=6=12)\n")
                continue

            try:
                node_id_str, val_str = argumentos.split('=', 1)
                node_id_str = node_id_str.strip()
                val_str = val_str.strip()

                target_node = client.get_node(node_id_str)
                current_val = await target_node.read_value()
                target_type = type(current_val)

                # Casteo dinámico según el tipo detectado en el servidor
                if target_type is bool:
                    cast_val = val_str.lower() in ("true", "1", "yes", "si")
                else:
                    cast_val = target_type(val_str)

                await target_node.write_value(cast_val)
                display_name = (await target_node.read_display_name()).Text
                print(
                    f"✅ 📢 [ESTRUCTURA ACTUALIZADA] -> Tag: '{display_name}' | Nuevo Valor: {cast_val} | Tipo: {target_type.__name__}\n")

            except ValueError:
                print(f"❌ Error de Tipo: El valor '{val_str}' no se puede convertir a {target_type.__name__}.\n")
            except ua.UaError as e:
                print(f"❌ Error OPC-UA: Nodo inválido o sin permisos. Detalle: {e}\n")
            except Exception as e:
                print(f"❌ Error inesperado: {e}\n")

        # 3. COMANDO TARGET (Modifica X e Y de forma simultánea)
        elif comando.upper().startswith('TARGET '):
            partes = comando.split()
            if len(partes) != 4:
                print("❌ Formato incorrecto. Uso: TARGET RobotID X Y (Ejemplo: TARGET R3 150 75)\n")
                continue

            _, robot_target, x_str, y_str = partes

            try:
                x_val = float(x_str)
                y_val = float(y_str)
            except ValueError:
                print("❌ Error de Tipo: Las coordenadas X e Y deben ser números.\n")
                continue

            try:
                robot_node = None
                # Buscar dinámicamente el objeto del robot por su nombre
                for child in await planta_node.get_children():
                    if (await child.read_display_name()).Text.upper() == robot_target.upper():
                        robot_node = child
                        break

                if not robot_node:
                    print(f"❌ Error: No se encontró ningún robot llamado '{robot_target}'.\n")
                    continue

                node_x, node_y = None, None
                # Extraer los tags X e Y dentro del robot encontrado
                for child in await robot_node.get_children():
                    name = (await child.read_display_name()).Text.upper()
                    if name == "X":
                        node_x = child
                    elif name == "Y":
                        node_y = child

                if not node_x or not node_y:
                    print(f"❌ Error: La estructura de '{robot_target}' no contiene los tags X e Y.\n")
                    continue

                # Enviar ambas variables al servidor OPC-UA simultáneamente
                await asyncio.gather(
                    node_x.write_value(x_val),
                    node_y.write_value(y_val)
                )
                print(
                    f"✅ 🎯 [DESTINO ACTUALIZADO] {robot_target.upper()} -> Nueva Coordenada: (X: {x_val}, Y: {y_val})\n")

            except ua.UaError as e:
                print(f"❌ Error de escritura en OPC-UA: {e}\n")
            except Exception as e:
                print(f"❌ Error al procesar TARGET: {e}\n")

        else:
            print("❌ Comando no reconocido. Utiliza REFRESH, UPDATE o TARGET\n")


# ==========================================
# BUCLE PRINCIPAL DE EJECUCIÓN
# ==========================================
async def main():
    print(f"Estableciendo conexión con {OPC_URL} ...")
    client = Client(url=OPC_URL)

    try:
        await client.connect()
        print("✅ Conexión establecida de forma segura.\n")

        # Suscripción inicial para eventos en segundo plano
        handler = DataChangeHandler()
        sub = await client.create_subscription(500, handler)

        # FILTRADO: Localizar el objeto específico "Planta"
        print("🔍 Buscando el objeto 'Planta' en el servidor...")
        planta_node = None
        objects_root = client.nodes.objects

        for child in await objects_root.get_children():
            name = (await child.read_display_name()).Text
            if name == "Planta":
                planta_node = child
                break

        if planta_node is None:
            print("❌ Error Crítico: No se localizó ningún objeto con el nombre 'Planta' en la raíz.")
            return

        print("\n🌲 ESTRUCTURA INICIAL DETECTADA (Filtro: Planta):")
        print(f"📂 [Raíz] Planta | NodeID: {planta_node.nodeid.to_string()}")
        # Mapeamos y nos suscribimos únicamente a los hijos de Planta
        await browse_and_print(planta_node, sub, level=1, subscribe=True)

        # Lanzamiento de la consola de comandos pasándole el filtro de la Planta
        await interactive_console(client, planta_node, sub)

    except ConnectionRefusedError:
        print("❌ Error: No se pudo conectar. Verifica que tu servidor esté activo.")
    except Exception as e:
        print(f"❌ Fallo en el cliente general: {e}")
    finally:
        print("Cerrando sesión de forma ordenada...")
        try:
            await client.disconnect()
            print("Desconectado de forma segura.")
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nEjecución abortada por el usuario.")