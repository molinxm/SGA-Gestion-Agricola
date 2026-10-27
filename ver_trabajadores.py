import os#importamos os para leer las variables del archivo .env

import mysql.connector
from dotenv import load_dotenv#traemos la herramienta que lee el archivo .env

#cargamos las credenciales guardadas en el archivo .env
load_dotenv()

try:
    conexion = mysql.connector.connect(
        host=os.environ.get("SGA_DB_HOST", "localhost"),
        user=os.environ.get("SGA_DB_USER", "root"),
        password=os.environ.get("SGA_DB_PASSWORD", ""),
        database=os.environ.get("SGA_DB_NAME", "gestion_agricola")
    )

    #creamos el cursor
    cursor = conexion.cursor()

    # 3 Escribimos la consulta sql para seleccionar/leer todos los registros
    sql  = "SELECT id_trabajador, nombre, telefono, cargo FROM Trabajadores"

    cursor.execute(sql) #ejecutamos la orden de leer todos los registros de la tabla trabajadores

    #ejecutamos la orden(no agregamos otro parametro porqque no queremos agregar nada, solo leer)
    resultado = cursor.fetchall()

    print("\n--- LISTA DE TRABAJADORES REGISTRADOS ---")

    #4 recorremos el resultado y mostramos los datos de cada trabajador PARA QUE SE VEA BONITO
    for trabajador in resultado:
        print(f"ID: {trabajador[0]} / Nombre: {trabajador[1]} / Telefono: {trabajador[2]} / cargo: {trabajador[3]} ")

    print("-" * 42)
except mysql.connector.Error as error:
    print(f"¡Ups! No pudimos leer los trabajadores. El problema fue este: {error}")

finally:
    # 5 siempre cerramos el cursor y la coneccion por orden y seguridad
    if 'conexion' in locals() and conexion.is_connected():
        cursor.close()
        conexion.close()
        print("Conexion Cerrada correctamente.")