#siempre debemos trar las librerias con 
#para llamar herramientas
import os#importamos os para leer las variables del archivo .env

import mysql.connector#traemos la herramienta para hablar con MySQL
from dotenv import load_dotenv#traemos la herramienta que lee el archivo .env

#cargamos las credenciales guardadas en el archivo .env
load_dotenv()

print("--- INICIANDO CONEXIÓN AL SISTEMA AGRÍCOLA --- ")

try:
    #intentamos abrir la puerta a la base de datos en mysql llamada gestion_agricola
    conexion = mysql.connector.connect(
        host=os.environ.get("SGA_DB_HOST", "localhost"),
        user=os.environ.get("SGA_DB_USER", "root"),
        password=os.environ.get("SGA_DB_PASSWORD", ""),
        database=os.environ.get("SGA_DB_NAME", "gestion_agricola"),
    )
    # Si logramos entrar, mostramos un mensaje de éxito
    if conexion.is_connected():
        print("¡Éxito! Python ya está conectado a tu base de datos MySQL.")

except mysql.connector.Error as error:
    # Si hay un error (ej. MySQL está apagado o la clave está mal), el except nos protege.
    # Además, usamos la 'f' y las llaves {} para imprimir exactamente cuál fue el error.
    print(f"¡Ups! No pudimos conectar. El problema fue este: {error}")




    