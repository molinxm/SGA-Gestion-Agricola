# ============================================================================
# SGA · Sistema de Gestión Agrícola
# Script de prueba de conexión (MySQL o SQLite)
# ============================================================================

import os
import sqlite3
import mysql.connector
from dotenv import load_dotenv

# Cargamos las credenciales del archivo .env
load_dotenv()

db_type = os.environ.get("SGA_DB_TYPE", "mysql").lower()

print(f"--- INICIANDO PRUEBA DE CONEXIÓN ({db_type.upper()}) ---")

try:
    if db_type == "sqlite":
        path = os.environ.get("SGA_SQLITE_PATH", "sga_agricola.db")
        conexion = sqlite3.connect(path)
        print(f"¡Éxito! Conectado a la base de datos SQLite en: {path}")
        conexion.close()
    else:
        conexion = mysql.connector.connect(
            host=os.environ.get("SGA_DB_HOST", "localhost"),
            user=os.environ.get("SGA_DB_USER", "root"),
            password=os.environ.get("SGA_DB_PASSWORD", ""),
            database=os.environ.get("SGA_DB_NAME", "gestion_agricola"),
        )
        if conexion.is_connected():
            print("¡Éxito! Python ya está conectado a tu base de datos MySQL.")
            conexion.close()

except Exception as error:
    print(f"¡Ups! No pudimos conectar. Detalle: {error}")
