"""
============================================================================
 SGA · Sistema de Gestión Agrícola
 Punto de entrada WSGI para servidores de producción
 (PythonAnywhere, gunicorn, waitress, etc.)
============================================================================

PythonAnywhere
--------------
En la pestaña "Web" -> sección "WSGI configuration file", reemplaza todo el
contenido de ese archivo por esto (ajustando TU_USUARIO):

    import sys
    path = "/home/TU_USUARIO/SGA_Web"
    if path not in sys.path:
        sys.path.insert(0, path)

    from app import app as application

Local / gunicorn
----------------
    gunicorn wsgi:application
"""

from app import app as application

if __name__ == "__main__":
    application.run()
