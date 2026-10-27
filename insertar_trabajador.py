import os

import mysql.connector
from dotenv import load_dotenv

# Cargamos las credenciales guardadas en el archivo .env
load_dotenv()


def insertar_trabajador_db(nombre, telefono, cargo):
  try:
    conexion = mysql.connector.connect(
        host=os.environ.get("SGA_DB_HOST", "localhost"),
        user=os.environ.get("SGA_DB_USER", "root"),
        password=os.environ.get("SGA_DB_PASSWORD", ""),
        database=os.environ.get("SGA_DB_NAME", "gestion_agricola"),
    )

    cursor = conexion.cursor()
    sql = "INSERT INTO Trabajadores (nombre, telefono, cargo) VALUES (%s, %s, %s)"
    nuevo_trabajador = (nombre, telefono, cargo)

    cursor.execute(sql, nuevo_trabajador)
    conexion.commit()

    print(
        f"EXITO Se ha registrado un nuevo trabajador correctamente. Filas"
        f" afectadas: {cursor.rowcount}"
    )
    return True

  except mysql.connector.Error as error:
    print(
        "¡Ups! No pudimos registrar el trabajador. El problema fue este:"
        f" {error}"
    )
    return False

  finally:
    if "conexion" in locals() and conexion.is_connected():
      cursor.close()
      conexion.close()
      print("Conexion Cerrada correctamente.")