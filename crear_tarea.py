import os
import tkinter as tk
from tkinter import messagebox, ttk

import mysql.connector
from dotenv import load_dotenv

# Cargamos las credenciales guardadas en el archivo .env
load_dotenv()

# Diccionario global para guardar {'Nombre': id_trabajador}
dicc_trabajadores = {}


def conexion_db():
  """Abre una conexión a MySQL usando las credenciales del archivo .env."""
  return mysql.connector.connect(
      host=os.environ.get("SGA_DB_HOST", "localhost"),
      user=os.environ.get("SGA_DB_USER", "root"),
      password=os.environ.get("SGA_DB_PASSWORD", ""),
      database=os.environ.get("SGA_DB_NAME", "gestion_agricola"),
  )


# --- 1. CONSULTAR TRABAJADORES USANDO 'id_trabajador' ---
def obtener_trabajadores_db():
  trabajadores = {}
  try:
    conexion = conexion_db()
    cursor = conexion.cursor()

    # Usamos id_trabajador exactamente como lo definiste en MySQL
    cursor.execute("SELECT id_trabajador, nombre FROM Trabajadores")
    registros = cursor.fetchall()

    for id_trab, nombre in registros:
      trabajadores[nombre] = id_trab

    print("Trabajadores cargados con éxito:", trabajadores)

  except mysql.connector.Error as error:
    print(f"Error al cargar trabajadores: {error}")
  finally:
    if "conexion" in locals() and conexion.is_connected():
      cursor.close()
      conexion.close()

  return trabajadores


# --- 2. REFRESCAR LA LISTA EN EL COMBOBOX ---
def refrescar_lista_trabajadores():
  global dicc_trabajadores
  dicc_trabajadores = obtener_trabajadores_db()
  combo_trabajadores["values"] = list(dicc_trabajadores.keys())


# --- 3. INSERCIÓN DE LA TAREA EN MYSQL ---
def crear_tarea_db(
    titulo, descripcion, estado_tarea, observaciones, id_trabajador
):
  try:
    conexion = conexion_db()
    cursor = conexion.cursor()

    sql = (
        "INSERT INTO Tareas (titulo, descripcion, estado_tarea, observaciones,"
        " id_trabajador) VALUES (%s, %s, %s, %s, %s)"
    )
    nueva_tarea = (
        titulo,
        descripcion,
        estado_tarea,
        observaciones,
        id_trabajador,
    )

    cursor.execute(sql, nueva_tarea)
    conexion.commit()

    print(
        "EXITO: Tarea creada y asignada correctamente. Filas afectadas:"
        f" {cursor.rowcount}"
    )
    return True

  except mysql.connector.Error as error:
    print(f"Error al crear la tarea: {error}")
    return False

  finally:
    if "conexion" in locals() and conexion.is_connected():
      cursor.close()
      conexion.close()


# --- 4. LÓGICA DEL BOTÓN Y LIMPIEZA DE CAMPOS ---
def boton_guardar_tarea():
  titulo = entry_titulo.get()
  descripcion = entry_descripcion.get()
  estado = combo_estado.get()
  observaciones = entry_observaciones.get()
  nombre_trabajador = combo_trabajadores.get()

  if titulo and descripcion and estado and nombre_trabajador:
    # Traemos el id_trabajador correspondiente al nombre seleccionado
    id_trabajador = dicc_trabajadores.get(nombre_trabajador)

    exito = crear_tarea_db(
        titulo, descripcion, estado, observaciones, id_trabajador
    )

    if exito:
      messagebox.showinfo("Éxito", "¡Tarea creada y asignada correctamente!")

      # Limpiamos todos los campos para la siguiente entrada
      entry_titulo.delete(0, tk.END)
      entry_descripcion.delete(0, tk.END)
      entry_observaciones.delete(0, tk.END)
      combo_trabajadores.set("")
      combo_estado.set("PENDIENTE")

    else:
      messagebox.showerror(
          "Error", "No se pudo registrar la tarea en la base de datos."
      )
  else:
    messagebox.showwarning(
        "Atención", "Por favor completa los campos obligatorios (*)."
    )


# --- 5. INTERFAZ GRÁFICA (TKINTER) ---
root = tk.Tk()
root.title("Gestión Agrícola - Asignar Tarea")
root.geometry("450x520")
root.config(bg="#ffffff")

# Título de la pantalla
tk.Label(
    root,
    text="Asignación de Nuevas Tareas",
    font=("Arial", 14, "bold"),
    bg="#ffffff",
    fg="#2c3e50",
).pack(pady=15)

# Carga inicial de trabajadores
dicc_trabajadores = obtener_trabajadores_db()

# Campo 1: Selección de Operario
tk.Label(root, text="Asignar a Operario (*):", bg="#ffffff").pack(
    anchor="w", padx=40, pady=(5, 0)
)
combo_trabajadores = ttk.Combobox(
    root,
    values=list(dicc_trabajadores.keys()),
    width=37,
    state="readonly",
    postcommand=refrescar_lista_trabajadores,  # Refresca automáticamente al desplegar
)
combo_trabajadores.pack(pady=5, padx=40)

# Campo 2: Título de la tarea
tk.Label(root, text="Título de la Tarea (*):", bg="#ffffff").pack(
    anchor="w", padx=40, pady=(5, 0)
)
entry_titulo = tk.Entry(root, width=40, font=("Arial", 10))
entry_titulo.pack(pady=5, padx=40)

# Campo 3: Descripción
tk.Label(root, text="Descripción (*):", bg="#ffffff").pack(
    anchor="w", padx=40, pady=(5, 0)
)
entry_descripcion = tk.Entry(root, width=40, font=("Arial", 10))
entry_descripcion.pack(pady=5, padx=40)

# Campo 4: Estado
tk.Label(root, text="Estado de la Tarea (*):", bg="#ffffff").pack(
    anchor="w", padx=40, pady=(5, 0)
)
combo_estado = ttk.Combobox(
    root,
    values=["PENDIENTE", "EN PROCESO", "COMPLETADA", "INCOMPLETA"],
    width=37,
    state="readonly",
)
combo_estado.set("PENDIENTE")
combo_estado.pack(pady=5, padx=40)

# Campo 5: Observaciones
tk.Label(root, text="Observaciones adicionales:", bg="#ffffff").pack(
    anchor="w", padx=40, pady=(5, 0)
)
entry_observaciones = tk.Entry(root, width=40, font=("Arial", 10))
entry_observaciones.pack(pady=5, padx=40)

# Botón Guardar
btn_guardar = tk.Button(
    root,
    text="Guardar y Asignar Tarea",
    command=boton_guardar_tarea,
    bg="#2980b9",
    fg="white",
    font=("Arial", 10, "bold"),
    pady=5,
)
btn_guardar.pack(pady=25)

root.mainloop()