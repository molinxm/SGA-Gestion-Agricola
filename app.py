"""
============================================================================
 SGA · Sistema de Gestión Agrícola
 Backend Flask + MySQL (mysql-connector) con control de acceso por roles (RBAC)
 Proyecto académico - UNIMINUTO
============================================================================

Se conecta a la base de datos real del proyecto:  gestion_agricola
Tablas utilizadas:
    trabajadores (id_trabajador, nombre, telefono, cargo, documento, email,
                  estado, fecha_ingreso, observaciones)
    tareas       (id_tarea, titulo, descripcion, estado_tarea, observaciones,
                  id_trabajador, lote, cultivo, prioridad,
                  fecha_inicio, fecha_limite, fecha_completada)
    usuarios     (id, nombre, email, password_hash, rol, activo, operario_id)

Rutas principales
-----------------
  GET  /                          Landing page pública
  GET  /login  |  POST /login     Autenticación
  GET  /logout                    Cierre de sesión
  GET  /tareas                    Listado + filtros + estadísticas de tareas
  POST /tareas/crear              Crear tarea
  POST /tareas/<id>/editar        Editar tarea
  POST /tareas/<id>/estado        Cambiar estado de la tarea
  POST /tareas/<id>/eliminar      Eliminar tarea
  GET  /operarios                 Listado de trabajadores con estadísticas
  POST /operarios/crear           Crear trabajador
  POST /operarios/<id>/editar     Editar trabajador
  POST /operarios/<id>/eliminar   Eliminar trabajador
  GET  /reportes                  Panel de indicadores
  GET  /reportes/exportar         Exportación CSV (tareas | operarios)

Puesta en marcha
----------------
    copiar .env.example a .env     Define las credenciales de MySQL
    flask --app app init-db        Crea/actualiza el esquema y usuarios semilla
    python app.py                  Levanta el servidor en http://127.0.0.1:5000
"""

import csv
import io
import os
from datetime import date, datetime
from functools import wraps

import mysql.connector
from dotenv import load_dotenv
from mysql.connector import Error
from flask import (
    Flask,
    Response,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from werkzeug.security import check_password_hash, generate_password_hash

# ---------------------------------------------------------------------------
#  Configuración
# ---------------------------------------------------------------------------

# Carga las variables del archivo .env (si existe) en os.environ.
load_dotenv()

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SGA_SECRET_KEY", "sga-dev-secret-cambiar-en-produccion"),
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    TEMPLATES_AUTO_RELOAD=True,
)

# Credenciales de la base de datos real del proyecto.
# Se leen del entorno (.env). Copia .env.example a .env y complétalo.
DB_CONFIG = {
    "host": os.environ.get("SGA_DB_HOST", "localhost"),
    "port": int(os.environ.get("SGA_DB_PORT", "3306")),
    "user": os.environ.get("SGA_DB_USER", "root"),
    "password": os.environ.get("SGA_DB_PASSWORD", ""),
    "database": os.environ.get("SGA_DB_NAME", "gestion_agricola"),
    "charset": "utf8mb4",
    "use_unicode": True,
    "autocommit": False,
}

# Nombres de las tablas reales.
# Se escriben en minúsculas porque MySQL en Linux (servidor) distingue
# mayúsculas de minúsculas; en Windows funciona igual, es indiferente.
TABLA_TRABAJADORES = "trabajadores"
TABLA_TAREAS = "tareas"
TABLA_USUARIOS = "usuarios"

# Dominio de negocio ---------------------------------------------------------
# Valores que se muestran en la interfaz
ESTADOS = ("Pendiente", "En Proceso", "Completada", "Incompleta")
PRIORIDADES = ("Alta", "Media", "Baja")
CARGOS = (
    "Jefe de Campo",
    "Operario Agrícola",
    "Tractorista",
    "Riego y Fertirriego",
    "Fitopatología",
    "Almacén",
)
ESTADOS_OPERARIO = ("Activo", "Inactivo")
ROLES = ("admin", "supervisor", "operario")

# La columna estado_tarea guarda los valores en MAYÚSCULAS; aquí se traducen
# a la forma presentable que consumen las plantillas.
EQUIVALENCIA_ESTADO = {
    "PENDIENTE": "Pendiente",
    "EN PROCESO": "En Proceso",
    "EN_PROCESO": "En Proceso",
    "COMPLETADA": "Completada",
    "INCOMPLETA": "Incompleta",
}

# Tarjetas de módulos mostradas en la landing page
MODULOS = [
    {
        "icono": "fa-users-gear",
        "titulo": "Gestión de Operarios",
        "texto": "Registra, actualiza y controla el personal de campo con sus cargos y estado laboral.",
        "endpoint": "operarios",
        "roles": ("admin", "supervisor"),
    },
    {
        "icono": "fa-clipboard-check",
        "titulo": "Gestión de Tareas",
        "texto": "Asigna labores por lote y cultivo, define prioridades y sigue cada estado en tiempo real.",
        "endpoint": "tareas",
        "roles": ROLES,
    },
    {
        "icono": "fa-chart-line",
        "titulo": "Reportes e Indicadores",
        "texto": "Mide cumplimiento, productividad por operario y rendimiento por cultivo con exportación CSV.",
        "endpoint": "reportes",
        "roles": ("admin", "supervisor"),
    },
    {
        "icono": "fa-shield-halved",
        "titulo": "Seguridad RBAC",
        "texto": "Accesos diferenciados para administrador, supervisor y operario según su responsabilidad.",
        "endpoint": "login",
        "roles": ROLES,
    },
]


# ---------------------------------------------------------------------------
#  Conexión a base de datos
# ---------------------------------------------------------------------------

def get_db():
    """Devuelve una conexión MySQL reutilizada durante el ciclo de la petición."""
    if "db" not in g:
        g.db = mysql.connector.connect(**DB_CONFIG)
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        try:
            if db.is_connected():
                db.close()
        except Error:
            pass


def fetch_all(sql, params=None):
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchall()
    finally:
        cursor.close()


def fetch_one(sql, params=None):
    cursor = get_db().cursor(dictionary=True)
    try:
        cursor.execute(sql, params or ())
        return cursor.fetchone()
    finally:
        cursor.close()


def execute(sql, params=None):
    db = get_db()
    cursor = db.cursor()
    try:
        cursor.execute(sql, params or ())
        db.commit()
        return cursor.lastrowid
    except Error:
        db.rollback()
        raise
    finally:
        cursor.close()


def db_error_message(error):
    return (
        "No fue posible conectar con MySQL. Revisa la configuración "
        "(SGA_DB_HOST / SGA_DB_USER / SGA_DB_PASSWORD / SGA_DB_NAME). "
        f"Detalle: {error}"
    )


# ---------------------------------------------------------------------------
#  Helpers de negocio
# ---------------------------------------------------------------------------

def parse_date(value):
    """Convierte 'YYYY-MM-DD' en date; devuelve None si viene vacío o inválido."""
    value = (value or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        return None


def clean(value, max_len=None):
    value = (value or "").strip()
    if max_len:
        value = value[:max_len]
    return value


def estado_a_interfaz(valor):
    """'EN PROCESO' -> 'En Proceso' (valor tal como lo muestran las plantillas)."""
    if not valor:
        return "Pendiente"
    clave = str(valor).strip().upper()
    if clave in EQUIVALENCIA_ESTADO:
        return EQUIVALENCIA_ESTADO[clave]
    return str(valor).strip().title()


def estado_a_base(valor):
    """'En Proceso' -> 'EN PROCESO' (valor tal como se guarda en MySQL)."""
    clave = (valor or "").strip().upper()
    if clave == "EN_PROCESO":
        clave = "EN PROCESO"
    return clave if clave in ESTADOS_DB else "PENDIENTE"


ESTADOS_DB = ("PENDIENTE", "EN PROCESO", "COMPLETADA", "INCOMPLETA")


def contar_por_estado(filas, campo="estado"):
    """Cuenta registros por estado, garantizando todas las claves en 0."""
    conteo = {estado: 0 for estado in ESTADOS}
    for fila in filas:
        clave = fila.get(campo)
        if clave in conteo:
            conteo[clave] += 1
    return conteo


# ---------------------------------------------------------------------------
#  Seguridad: decoradores RBAC
# ---------------------------------------------------------------------------

def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        if not session.get("user_id"):
            flash("Inicia sesión para acceder a esta sección.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)

    return wrapper


def roles_required(*roles):
    """Restringe la vista a los roles indicados (admin siempre pasa)."""

    def decorator(view):
        @wraps(view)
        def wrapper(*args, **kwargs):
            if not session.get("user_id"):
                flash("Inicia sesión para acceder a esta sección.", "warning")
                return redirect(url_for("login", next=request.path))
            if session.get("rol") != "admin" and session.get("rol") not in roles:
                flash("No tienes permisos para acceder a esta sección.", "error")
                return redirect(url_for("tareas"))
            return view(*args, **kwargs)

        return wrapper

    return decorator


# ---------------------------------------------------------------------------
#  Filtros y contexto global para las plantillas Jinja2
# ---------------------------------------------------------------------------

@app.template_filter("estado_class")
def estado_class(estado):
    return {
        "Pendiente": "badge--pendiente",
        "En Proceso": "badge--proceso",
        "Completada": "badge--completada",
        "Incompleta": "badge--incompleta",
    }.get(estado, "badge--neutral")


@app.template_filter("prioridad_class")
def prioridad_class(prioridad):
    return {
        "Alta": "badge--alta",
        "Media": "badge--media",
        "Baja": "badge--baja",
    }.get(prioridad, "badge--neutral")


@app.template_filter("fecha_es")
def fecha_es(valor):
    """Formatea date/datetime como dd/mm/aaaa."""
    if not valor:
        return "—"
    if isinstance(valor, (date, datetime)):
        return valor.strftime("%d/%m/%Y")
    return str(valor)


@app.template_filter("iniciales")
def iniciales(nombre):
    if not nombre:
        return "?"
    partes = [p for p in str(nombre).split() if p]
    if not partes:
        return "?"
    if len(partes) == 1:
        return partes[0][:2].upper()
    return (partes[0][0] + partes[-1][0]).upper()


@app.context_processor
def inject_globals():
    return {
        "current_user": {
            "id": session.get("user_id"),
            "nombre": session.get("nombre"),
            "rol": session.get("rol"),
            "operario_id": session.get("operario_id"),
        },
        "ESTADOS": ESTADOS,
        "PRIORIDADES": PRIORIDADES,
        "CARGOS": CARGOS,
        "ESTADOS_OPERARIO": ESTADOS_OPERARIO,
        "ROLES": ROLES,
        "hoy": date.today(),
        "ahora": datetime.now(),
    }


# ---------------------------------------------------------------------------
#  Landing page pública
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    return render_template("index.html", modulos=MODULOS)


# ---------------------------------------------------------------------------
#  Autenticación
# ---------------------------------------------------------------------------

@app.route("/login", methods=["GET", "POST"])
def login():
    if session.get("user_id"):
        return redirect(url_for("tareas"))

    email = ""

    if request.method == "POST":
        email = clean(request.form.get("email")).lower()
        password = request.form.get("password") or ""

        if not email or not password:
            flash("Ingresa tu correo institucional y tu contraseña.", "warning")
            return render_template("login.html", email=email), 400

        try:
            usuario = fetch_one(
                f"SELECT * FROM {TABLA_USUARIOS} WHERE email = %s", (email,)
            )
        except Error as error:
            flash(db_error_message(error), "error")
            return render_template("login.html", email=email), 503

        if not usuario or not check_password_hash(usuario["password_hash"], password):
            flash("Credenciales inválidas. Verifica tu correo y contraseña.", "error")
            return render_template("login.html", email=email), 401

        if not usuario.get("activo"):
            flash("Tu cuenta está inactiva. Contacta al administrador del sistema.", "warning")
            return render_template("login.html", email=email), 403

        session.clear()
        session["user_id"] = usuario["id"]
        session["nombre"] = usuario["nombre"]
        session["rol"] = usuario["rol"]
        session["operario_id"] = usuario.get("operario_id")
        flash(f"¡Bienvenido, {usuario['nombre']}! Ya estás dentro del sistema.", "success")

        destino = request.args.get("next", "")
        if not destino.startswith("/") or destino.startswith("//"):
            destino = url_for("tareas")
        return redirect(destino)

    return render_template("login.html", email=email)


@app.route("/logout")
def logout():
    session.clear()
    flash("Sesión finalizada correctamente. ¡Vuelve pronto!", "info")
    return redirect(url_for("index"))


# ---------------------------------------------------------------------------
#  Módulo: Tareas  (tabla Tareas)
# ---------------------------------------------------------------------------

SELECT_TAREAS = f"""
    SELECT t.id_tarea                                   AS id,
           t.titulo,
           t.descripcion,
           t.id_trabajador                              AS operario_id,
           t.lote,
           t.cultivo,
           t.prioridad,
           t.estado_tarea                               AS estado,
           t.fecha_inicio,
           t.fecha_limite,
           t.fecha_completada,
           w.nombre                                     AS operario_nombre,
           w.cargo                                      AS operario_cargo
    FROM {TABLA_TAREAS} t
    LEFT JOIN {TABLA_TRABAJADORES} w ON w.id_trabajador = t.id_trabajador
"""


@app.route("/tareas")
@login_required
def tareas():
    estado = clean(request.args.get("estado"))
    prioridad = clean(request.args.get("prioridad"))
    operario_filtro = clean(request.args.get("operario_id"))
    busqueda = clean(request.args.get("q"))

    sql = SELECT_TAREAS + " WHERE 1 = 1"
    params = []

    # Un operario solo visualiza las tareas asignadas a él
    if session.get("rol") == "operario":
        sql += " AND t.id_trabajador <=> %s"
        params.append(session.get("operario_id"))

    if estado in ESTADOS:
        sql += " AND t.estado_tarea = %s"
        params.append(estado_a_base(estado))
    if prioridad in PRIORIDADES:
        sql += " AND t.prioridad = %s"
        params.append(prioridad)
    if operario_filtro.isdigit():
        sql += " AND t.id_trabajador = %s"
        params.append(int(operario_filtro))
    if busqueda:
        sql += " AND (t.titulo LIKE %s OR t.lote LIKE %s OR t.cultivo LIKE %s)"
        like = f"%{busqueda}%"
        params.extend([like, like, like])

    sql += (" ORDER BY FIELD(t.estado_tarea, 'EN PROCESO', 'PENDIENTE', 'INCOMPLETA', 'COMPLETADA'),"
            " t.fecha_limite IS NULL, t.fecha_limite ASC")

    try:
        lista_tareas = fetch_all(sql, params)
        operarios_lista = fetch_all(
            f"SELECT id_trabajador AS id, nombre, cargo, estado "
            f"FROM {TABLA_TRABAJADORES} ORDER BY nombre"
        )
    except Error as error:
        flash(db_error_message(error), "error")
        lista_tareas, operarios_lista = [], []

    hoy = date.today()
    for tarea in lista_tareas:
        # Se traduce el estado de MySQL ('EN PROCESO') a la forma de la interfaz ('En Proceso')
        tarea["estado"] = estado_a_interfaz(tarea["estado"])
        tarea["vencida"] = bool(
            tarea["fecha_limite"]
            and tarea["fecha_limite"] < hoy
            and tarea["estado"] not in ("Completada", "Incompleta")
        )

    return render_template(
        "tareas.html",
        tareas=lista_tareas,
        operarios=operarios_lista,
        conteo=contar_por_estado(lista_tareas),
        filtros={"estado": estado, "prioridad": prioridad,
                 "operario_id": operario_filtro, "q": busqueda},
        total_filtrado=len(lista_tareas),
    )


@app.route("/tareas/crear", methods=["POST"])
@roles_required("supervisor")
def crear_tarea():
    titulo = clean(request.form.get("titulo"), 150)
    if not titulo:
        flash("El título de la tarea es obligatorio.", "error")
        return redirect(url_for("tareas"))

    operario_id = request.form.get("operario_id") or None
    operario_id = int(operario_id) if str(operario_id).isdigit() else None
    estado = clean(request.form.get("estado"))
    prioridad = clean(request.form.get("prioridad"))

    if estado not in ESTADOS:
        estado = "Pendiente"
    if prioridad not in PRIORIDADES:
        prioridad = "Media"

    completada = date.today() if estado == "Completada" else None

    try:
        execute(
            f"""
            INSERT INTO {TABLA_TAREAS}
                (titulo, descripcion, id_trabajador, lote, cultivo, prioridad,
                 estado_tarea, observaciones, fecha_inicio, fecha_limite, fecha_completada)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                titulo,
                clean(request.form.get("descripcion")),
                operario_id,
                clean(request.form.get("lote"), 60) or None,
                clean(request.form.get("cultivo"), 80) or None,
                prioridad,
                estado_a_base(estado),
                clean(request.form.get("observaciones"), 255) or None,
                parse_date(request.form.get("fecha_inicio")) or date.today(),
                parse_date(request.form.get("fecha_limite")),
                completada,
            ),
        )
        flash(f"Tarea «{titulo}» registrada correctamente.", "success")
    except Error as error:
        flash(db_error_message(error), "error")

    return redirect(url_for("tareas"))


@app.route("/tareas/<int:tarea_id>/editar", methods=["POST"])
@roles_required("supervisor")
def editar_tarea(tarea_id):
    titulo = clean(request.form.get("titulo"), 150)
    if not titulo:
        flash("El título de la tarea es obligatorio.", "error")
        return redirect(url_for("tareas"))

    operario_id = request.form.get("operario_id") or None
    operario_id = int(operario_id) if str(operario_id).isdigit() else None

    estado = clean(request.form.get("estado"))
    if estado not in ESTADOS:
        estado = "Pendiente"
    prioridad = clean(request.form.get("prioridad"))
    if prioridad not in PRIORIDADES:
        prioridad = "Media"

    completada = parse_date(request.form.get("fecha_completada"))
    if estado == "Completada" and not completada:
        completada = date.today()
    if estado != "Completada":
        completada = None

    try:
        execute(
            f"""
            UPDATE {TABLA_TAREAS}
               SET titulo = %s, descripcion = %s, id_trabajador = %s, lote = %s,
                   cultivo = %s, prioridad = %s, estado_tarea = %s,
                   fecha_inicio = %s, fecha_limite = %s, fecha_completada = %s
             WHERE id_tarea = %s
            """,
            (
                titulo,
                clean(request.form.get("descripcion")),
                operario_id,
                clean(request.form.get("lote"), 60) or None,
                clean(request.form.get("cultivo"), 80) or None,
                prioridad,
                estado_a_base(estado),
                parse_date(request.form.get("fecha_inicio")),
                parse_date(request.form.get("fecha_limite")),
                completada,
                tarea_id,
            ),
        )
        flash("Tarea actualizada correctamente.", "success")
    except Error as error:
        flash(db_error_message(error), "error")

    return redirect(url_for("tareas"))


@app.route("/tareas/<int:tarea_id>/estado", methods=["POST"])
@login_required
def cambiar_estado_tarea(tarea_id):
    nuevo_estado = clean(request.form.get("estado"))
    if nuevo_estado not in ESTADOS:
        flash("Estado no válido.", "error")
        return redirect(url_for("tareas"))

    try:
        tarea = fetch_one(
            f"SELECT id_tarea, id_trabajador FROM {TABLA_TAREAS} WHERE id_tarea = %s",
            (tarea_id,),
        )
        if not tarea:
            flash("La tarea indicada no existe.", "error")
            return redirect(url_for("tareas"))

        # Un operario solo puede mover sus propias tareas
        if session.get("rol") == "operario" and tarea["id_trabajador"] != session.get("operario_id"):
            flash("Solo puedes actualizar el estado de las tareas asignadas a ti.", "error")
            return redirect(url_for("tareas"))

        fecha_completada = date.today() if nuevo_estado == "Completada" else None
        execute(
            f"UPDATE {TABLA_TAREAS} SET estado_tarea = %s, fecha_completada = %s "
            f"WHERE id_tarea = %s",
            (estado_a_base(nuevo_estado), fecha_completada, tarea_id),
        )
        flash(f"Estado actualizado a «{nuevo_estado}».", "success")
    except Error as error:
        flash(db_error_message(error), "error")

    return redirect(request.form.get("volver_a") or url_for("tareas"))


@app.route("/tareas/<int:tarea_id>/eliminar", methods=["POST"])
@roles_required("supervisor")
def eliminar_tarea(tarea_id):
    try:
        execute(f"DELETE FROM {TABLA_TAREAS} WHERE id_tarea = %s", (tarea_id,))
        flash("Tarea eliminada del sistema.", "success")
    except Error as error:
        flash(db_error_message(error), "error")
    return redirect(url_for("tareas"))


# ---------------------------------------------------------------------------
#  Módulo: Operarios  (tabla Trabajadores)
# ---------------------------------------------------------------------------

@app.route("/operarios")
@roles_required("supervisor")
def operarios():
    busqueda = clean(request.args.get("q"))
    estado = clean(request.args.get("estado"))
    cargo = clean(request.args.get("cargo"))

    sql = f"""
        SELECT w.id_trabajador            AS id,
               w.nombre,
               w.documento,
               w.telefono,
               w.email,
               w.cargo,
               w.estado,
               w.fecha_ingreso,
               w.observaciones,
               COUNT(t.id_tarea)                              AS tareas_asignadas,
               COALESCE(SUM(t.estado_tarea = 'COMPLETADA'), 0) AS tareas_completadas
        FROM {TABLA_TRABAJADORES} w
        LEFT JOIN {TABLA_TAREAS} t ON t.id_trabajador = w.id_trabajador
        WHERE 1 = 1
    """
    params = []
    if busqueda:
        sql += " AND (w.nombre LIKE %s OR w.documento LIKE %s OR w.email LIKE %s)"
        like = f"%{busqueda}%"
        params.extend([like, like, like])
    if estado in ESTADOS_OPERARIO:
        sql += " AND w.estado = %s"
        params.append(estado)
    if cargo in CARGOS:
        sql += " AND w.cargo = %s"
        params.append(cargo)

    sql += """
        GROUP BY w.id_trabajador, w.nombre, w.documento, w.telefono, w.email,
                 w.cargo, w.estado, w.fecha_ingreso, w.observaciones
        ORDER BY w.nombre ASC
    """

    try:
        lista_operarios = fetch_all(sql, params)
    except Error as error:
        flash(db_error_message(error), "error")
        lista_operarios = []

    resumen = {
        "total": len(lista_operarios),
        "activos": sum(1 for o in lista_operarios if o["estado"] == "Activo"),
        "inactivos": sum(1 for o in lista_operarios if o["estado"] == "Inactivo"),
        "tareas_completadas": sum(int(o["tareas_completadas"] or 0) for o in lista_operarios),
    }

    return render_template(
        "operarios.html",
        operarios=lista_operarios,
        resumen=resumen,
        filtros={"q": busqueda, "estado": estado, "cargo": cargo},
        total_filtrado=len(lista_operarios),
    )


@app.route("/operarios/crear", methods=["POST"])
@roles_required("supervisor")
def crear_operario():
    nombre = clean(request.form.get("nombre"), 120)
    documento = clean(request.form.get("documento"), 30)

    if not nombre or not documento:
        flash("El nombre y el documento del operario son obligatorios.", "error")
        return redirect(url_for("operarios"))

    estado = clean(request.form.get("estado"))
    cargo = clean(request.form.get("cargo"), 80)

    try:
        execute(
            f"""
            INSERT INTO {TABLA_TRABAJADORES}
                (nombre, documento, telefono, email, cargo, estado, fecha_ingreso, observaciones)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                nombre,
                documento,
                clean(request.form.get("telefono"), 30) or None,
                clean(request.form.get("email"), 150).lower() or None,
                cargo if cargo in CARGOS else "Operario Agrícola",
                estado if estado in ESTADOS_OPERARIO else "Activo",
                parse_date(request.form.get("fecha_ingreso")) or date.today(),
                clean(request.form.get("observaciones"), 255) or None,
            ),
        )
        flash(f"Operario «{nombre}» registrado correctamente.", "success")
    except Error as error:
        flash(db_error_message(error), "error")

    return redirect(url_for("operarios"))


@app.route("/operarios/<int:operario_id>/editar", methods=["POST"])
@roles_required("supervisor")
def editar_operario(operario_id):
    nombre = clean(request.form.get("nombre"), 120)
    documento = clean(request.form.get("documento"), 30)

    if not nombre or not documento:
        flash("El nombre y el documento del operario son obligatorios.", "error")
        return redirect(url_for("operarios"))

    estado = clean(request.form.get("estado"))
    cargo = clean(request.form.get("cargo"), 80)

    try:
        execute(
            f"""
            UPDATE {TABLA_TRABAJADORES}
               SET nombre = %s, documento = %s, telefono = %s, email = %s,
                   cargo = %s, estado = %s, fecha_ingreso = %s, observaciones = %s
             WHERE id_trabajador = %s
            """,
            (
                nombre,
                documento,
                clean(request.form.get("telefono"), 30) or None,
                clean(request.form.get("email"), 150).lower() or None,
                cargo if cargo in CARGOS else "Operario Agrícola",
                estado if estado in ESTADOS_OPERARIO else "Activo",
                parse_date(request.form.get("fecha_ingreso")),
                clean(request.form.get("observaciones"), 255) or None,
                operario_id,
            ),
        )
        flash("Datos del operario actualizados correctamente.", "success")
    except Error as error:
        flash(db_error_message(error), "error")

    return redirect(url_for("operarios"))


@app.route("/operarios/<int:operario_id>/eliminar", methods=["POST"])
@roles_required()  # solo admin
def eliminar_operario(operario_id):
    try:
        execute(f"DELETE FROM {TABLA_TRABAJADORES} WHERE id_trabajador = %s", (operario_id,))
        flash("Operario eliminado. Sus tareas quedaron sin asignar.", "success")
    except Error as error:
        flash(db_error_message(error), "error")
    return redirect(url_for("operarios"))


# ---------------------------------------------------------------------------
#  Módulo: Reportes
# ---------------------------------------------------------------------------

@app.route("/reportes")
@roles_required("supervisor")
def reportes():
    try:
        totales = fetch_one(
            f"""
            SELECT COUNT(*) AS total,
                   COALESCE(SUM(estado_tarea = 'PENDIENTE'), 0)  AS pendientes,
                   COALESCE(SUM(estado_tarea = 'EN PROCESO'), 0) AS en_proceso,
                   COALESCE(SUM(estado_tarea = 'COMPLETADA'), 0) AS completadas,
                   COALESCE(SUM(estado_tarea = 'INCOMPLETA'), 0) AS incompletas,
                   COALESCE(SUM(estado_tarea = 'COMPLETADA'
                                AND fecha_limite IS NOT NULL
                                AND fecha_completada IS NOT NULL
                                AND fecha_completada <= fecha_limite), 0) AS a_tiempo
            FROM {TABLA_TAREAS}
            """
        ) or {}

        por_estado = fetch_all(
            f"SELECT estado_tarea AS estado, COUNT(*) AS total "
            f"FROM {TABLA_TAREAS} GROUP BY estado_tarea"
        )
        por_prioridad = fetch_all(
            f"SELECT prioridad, COUNT(*) AS total FROM {TABLA_TAREAS} GROUP BY prioridad"
        )
        por_cultivo = fetch_all(
            f"""
            SELECT COALESCE(cultivo, 'Sin cultivo') AS cultivo,
                   COUNT(*) AS total,
                   COALESCE(SUM(estado_tarea = 'COMPLETADA'), 0) AS completadas
            FROM {TABLA_TAREAS}
            GROUP BY cultivo
            ORDER BY total DESC
            """
        )
        por_operario = fetch_all(
            f"""
            SELECT w.nombre, w.cargo,
                   COUNT(t.id_tarea) AS total,
                   COALESCE(SUM(t.estado_tarea = 'COMPLETADA'), 0) AS completadas,
                   COALESCE(SUM(t.estado_tarea IN ('PENDIENTE', 'EN PROCESO')), 0) AS abiertas,
                   COALESCE(SUM(t.estado_tarea = 'INCOMPLETA'), 0) AS incompletas
            FROM {TABLA_TRABAJADORES} w
            LEFT JOIN {TABLA_TAREAS} t ON t.id_trabajador = w.id_trabajador
            GROUP BY w.id_trabajador, w.nombre, w.cargo
            ORDER BY completadas DESC, total DESC
            """
        )
        por_periodo = fetch_all(
            f"""
            SELECT DATE_FORMAT(fecha_inicio, '%%Y-%%m') AS periodo,
                   COUNT(*) AS total,
                   COALESCE(SUM(estado_tarea = 'COMPLETADA'), 0) AS completadas
            FROM {TABLA_TAREAS}
            WHERE fecha_inicio IS NOT NULL
            GROUP BY periodo
            ORDER BY periodo
            """
        )
        total_operarios = fetch_one(
            f"SELECT COUNT(*) AS total, COALESCE(SUM(estado = 'Activo'), 0) AS activos "
            f"FROM {TABLA_TRABAJADORES}"
        ) or {}
    except Error as error:
        flash(db_error_message(error), "error")
        totales, por_estado, por_prioridad = {}, [], []
        por_cultivo, por_operario, por_periodo, total_operarios = [], [], [], {}

    total = int(totales.get("total") or 0)
    completadas = int(totales.get("completadas") or 0)
    a_tiempo = int(totales.get("a_tiempo") or 0)

    resumen = {
        "total": total,
        "pendientes": int(totales.get("pendientes") or 0),
        "en_proceso": int(totales.get("en_proceso") or 0),
        "completadas": completadas,
        "incompletas": int(totales.get("incompletas") or 0),
        "a_tiempo": a_tiempo,
        "cumplimiento": round((completadas / total) * 100, 1) if total else 0.0,
        "eficiencia": round((a_tiempo / completadas) * 100, 1) if completadas else 0.0,
        "operarios_total": int(total_operarios.get("total") or 0),
        "operarios_activos": int(total_operarios.get("activos") or 0),
    }

    conteo_estado = {estado: 0 for estado in ESTADOS}
    for fila in por_estado:
        clave = estado_a_interfaz(fila["estado"])
        if clave in conteo_estado:
            conteo_estado[clave] += int(fila["total"])
    dist_estado = {
        estado: (round((conteo_estado[estado] / total) * 100, 1) if total else 0.0)
        for estado in ESTADOS
    }

    max_prioridad = max([int(f["total"]) for f in por_prioridad], default=0) or 1

    return render_template(
        "reportes.html",
        resumen=resumen,
        por_estado=por_estado,
        dist_estado=dist_estado,
        por_prioridad=por_prioridad,
        max_prioridad=max_prioridad,
        por_cultivo=por_cultivo,
        por_operario=por_operario,
        por_periodo=por_periodo,
    )


@app.route("/reportes/exportar")
@roles_required("supervisor")
def exportar_reportes():
    tipo = clean(request.args.get("tipo")) or "tareas"
    marca = datetime.now().strftime("%Y%m%d_%H%M")
    buffer = io.StringIO()
    buffer.write("\ufeff")  # BOM para que Excel respete los acentos
    writer = csv.writer(buffer, delimiter=";")

    def formatear(valor):
        return valor.strftime("%d/%m/%Y") if valor else ""

    try:
        if tipo == "operarios":
            writer.writerow([
                "ID", "Nombre", "Documento", "Teléfono", "Email", "Cargo",
                "Estado", "Fecha ingreso", "Tareas asignadas", "Tareas completadas",
            ])
            filas = fetch_all(
                f"""
                SELECT w.id_trabajador AS id, w.nombre, w.documento,
                       COALESCE(w.telefono, '') AS telefono, COALESCE(w.email, '') AS email,
                       w.cargo, w.estado, w.fecha_ingreso,
                       COUNT(t.id_tarea) AS tareas_asignadas,
                       COALESCE(SUM(t.estado_tarea = 'COMPLETADA'), 0) AS tareas_completadas
                FROM {TABLA_TRABAJADORES} w
                LEFT JOIN {TABLA_TAREAS} t ON t.id_trabajador = w.id_trabajador
                GROUP BY w.id_trabajador, w.nombre, w.documento, w.telefono,
                         w.email, w.cargo, w.estado, w.fecha_ingreso
                ORDER BY w.nombre
                """
            )
            for fila in filas:
                writer.writerow([
                    fila["id"], fila["nombre"], fila["documento"] or "", fila["telefono"],
                    fila["email"], fila["cargo"], fila["estado"],
                    formatear(fila["fecha_ingreso"]),
                    fila["tareas_asignadas"], fila["tareas_completadas"],
                ])
            nombre_archivo = f"sga_operarios_{marca}.csv"
        else:
            writer.writerow([
                "ID", "Título", "Descripción", "Operario", "Lote", "Cultivo",
                "Prioridad", "Estado", "Fecha inicio", "Fecha límite",
                "Fecha completada", "¿Cumplió a tiempo?",
            ])
            filas = fetch_all(
                f"""
                SELECT t.id_tarea AS id, t.titulo, COALESCE(t.descripcion, '') AS descripcion,
                       COALESCE(w.nombre, 'Sin asignar') AS operario,
                       COALESCE(t.lote, '') AS lote, COALESCE(t.cultivo, '') AS cultivo,
                       t.prioridad, t.estado_tarea AS estado,
                       t.fecha_inicio, t.fecha_limite, t.fecha_completada
                FROM {TABLA_TAREAS} t
                LEFT JOIN {TABLA_TRABAJADORES} w ON w.id_trabajador = t.id_trabajador
                ORDER BY t.id_tarea
                """
            )
            for fila in filas:
                if (fila["estado"] == "COMPLETADA"
                        and fila["fecha_limite"] and fila["fecha_completada"]):
                    a_tiempo = "Sí" if fila["fecha_completada"] <= fila["fecha_limite"] else "No"
                else:
                    a_tiempo = "—"
                writer.writerow([
                    fila["id"], fila["titulo"], fila["descripcion"], fila["operario"],
                    fila["lote"], fila["cultivo"], fila["prioridad"],
                    estado_a_interfaz(fila["estado"]),
                    formatear(fila["fecha_inicio"]), formatear(fila["fecha_limite"]),
                    formatear(fila["fecha_completada"]), a_tiempo,
                ])
            nombre_archivo = f"sga_tareas_{marca}.csv"
    except Error as error:
        flash(db_error_message(error), "error")
        return redirect(url_for("reportes"))

    return Response(
        buffer.getvalue(),
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{nombre_archivo}"'},
    )


# ---------------------------------------------------------------------------
#  Migración de esquema y datos semilla
#  (idempotente: se puede ejecutar varias veces sin perder información)
# ---------------------------------------------------------------------------

# Columnas que la interfaz necesita y que se agregan si no existen todavía
COLUMNAS_EXTRA_TRABAJADORES = {
    "documento": "VARCHAR(30) NULL",
    "email": "VARCHAR(150) NULL",
    "estado": "VARCHAR(20) NOT NULL DEFAULT 'Activo'",
    "fecha_ingreso": "DATE NULL",
    "observaciones": "VARCHAR(255) NULL",
}

COLUMNAS_EXTRA_TAREAS = {
    "lote": "VARCHAR(60) NULL",
    "cultivo": "VARCHAR(80) NULL",
    "prioridad": "VARCHAR(10) NOT NULL DEFAULT 'Media'",
    "fecha_inicio": "DATE NULL",
    "fecha_limite": "DATE NULL",
    "fecha_completada": "DATE NULL",
    "observaciones": "VARCHAR(255) NULL",
}


def _existe_tabla(cursor, tabla):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.TABLES "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s",
        (DB_CONFIG["database"], tabla),
    )
    return cursor.fetchone()[0] > 0


def _existe_columna(cursor, tabla, columna):
    cursor.execute(
        "SELECT COUNT(*) FROM information_schema.COLUMNS "
        "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s AND COLUMN_NAME = %s",
        (DB_CONFIG["database"], tabla, columna),
    )
    return cursor.fetchone()[0] > 0


def _agregar_columnas_faltantes(cursor, tabla, columnas):
    agregadas = []
    for columna, definicion in columnas.items():
        if not _existe_columna(cursor, tabla, columna):
            cursor.execute(f"ALTER TABLE {tabla} ADD COLUMN {columna} {definicion}")
            agregadas.append(columna)
    return agregadas


def _renombrar_pk_tareas(cursor):
    """Garantiza que la llave primaria de Tareas se llame id_tarea."""
    if _existe_columna(cursor, TABLA_TAREAS, "id_tarea"):
        return None
    for candidato in ("id", "id_tareas", "ID_tarea"):
        if _existe_columna(cursor, TABLA_TAREAS, candidato):
            cursor.execute(
                f"ALTER TABLE {TABLA_TAREAS} CHANGE COLUMN {candidato} "
                f"id_tarea INT AUTO_INCREMENT"
            )
            return candidato
    return None


@app.cli.command("init-db")
def init_db_command():
    """Crea o actualiza el esquema de gestion_agricola y los usuarios semilla."""
    ruta = os.path.join(os.path.dirname(os.path.abspath(__file__)), "schema.sql")
    with open(ruta, "r", encoding="utf-8") as archivo:
        sentencias = [s.strip() for s in archivo.read().split(";") if s.strip()]

    try:
        conexion = mysql.connector.connect(
            host=DB_CONFIG["host"], port=DB_CONFIG["port"], user=DB_CONFIG["user"],
            password=DB_CONFIG["password"], charset="utf8mb4",
        )
        cursor = conexion.cursor()

        # 1) Crea la base de datos y las tablas que falten
        for sentencia in sentencias:
            cursor.execute(sentencia)
        conexion.commit()
        print(f"Base de datos «{DB_CONFIG['database']}» verificada.")

        # 2) Agrega las columnas que la interfaz necesita y aún no existen
        cursor.execute(f"USE {DB_CONFIG['database']}")
        nuevas = _agregar_columnas_faltantes(cursor, TABLA_TRABAJADORES, COLUMNAS_EXTRA_TRABAJADORES)
        if nuevas:
            print(f"  {TABLA_TRABAJADORES}: columnas agregadas -> {', '.join(nuevas)}")

        nuevas = _agregar_columnas_faltantes(cursor, TABLA_TAREAS, COLUMNAS_EXTRA_TAREAS)
        if nuevas:
            print(f"  {TABLA_TAREAS}: columnas agregadas -> {', '.join(nuevas)}")

        renombrada = _renombrar_pk_tareas(cursor)
        if renombrada:
            print(f"  {TABLA_TAREAS}: llave primaria «{renombrada}» renombrada a «id_tarea»")
        conexion.commit()

        # 3) Usuarios semilla (solo si la tabla está vacía)
        # Las contraseñas NO están en el código: se leen del entorno (.env).
        cursor.execute(f"SELECT COUNT(*) FROM {TABLA_USUARIOS}")
        if cursor.fetchone()[0] == 0:
            cursor.execute(f"SELECT id_trabajador FROM {TABLA_TRABAJADORES} ORDER BY id_trabajador LIMIT 1")
            fila = cursor.fetchone()
            primer_operario = fila[0] if fila else None

            semilla = [
                ("Administrador SGA", "admin@sga.edu.co", "SGA_ADMIN_PASSWORD", "admin", None),
                ("Supervisor de Campo", "supervisor@sga.edu.co", "SGA_SUPERVISOR_PASSWORD", "supervisor", None),
                ("Operario de Campo", "operario@sga.edu.co", "SGA_OPERARIO_PASSWORD", "operario", primer_operario),
            ]
            creadas = 0
            for nombre, email, variable, rol, operario_id in semilla:
                clave = os.environ.get(variable)
                if not clave:
                    print(f"  usuarios: se omite {email} (falta {variable} en el entorno).")
                    continue
                cursor.execute(
                    f"INSERT INTO {TABLA_USUARIOS} (nombre, email, password_hash, rol, operario_id) "
                    f"VALUES (%s, %s, %s, %s, %s)",
                    (nombre, email, generate_password_hash(clave), rol, operario_id),
                )
                creadas += 1
            conexion.commit()
            print(f"  usuarios: {creadas} cuenta(s) semilla creada(s).")
        else:
            print("  usuarios: ya existen cuentas registradas (no se modificaron).")

        # 4) Datos de ejemplo (solo si las tablas están vacías)
        cursor.execute(f"SELECT COUNT(*) FROM {TABLA_TRABAJADORES}")
        if cursor.fetchone()[0] == 0:
            ejemplo_trabajadores = [
                ("Carlos Mendoza Rivas", "1010234567", "3105550101", "carlos.mendoza@sga.co",
                 "Jefe de Campo", "Activo", "2019-02-11", "Certificado en BPA"),
                ("Lucía Fernández Gómez", "1020456789", "3105550102", "lucia.fernandez@sga.co",
                 "Fitopatología", "Activo", "2020-06-01", "Manejo integrado de plagas"),
                ("Andrés Ramírez Salas", "1030678901", "3105550103", "andres.ramirez@sga.co",
                 "Tractorista", "Activo", "2018-09-23", "Licencia de conducción C2"),
                ("María Cárdenas Peña", "1040890123", "3105550104", "maria.cardenas@sga.co",
                 "Riego y Fertirriego", "Activo", "2021-03-15", "Especialista en goteo"),
                ("Diana Ospina Herrera", "1060123456", "3105550106", "diana.ospina@sga.co",
                 "Almacén", "Activo", "2022-01-10", "Control de insumos"),
            ]
            for fila in ejemplo_trabajadores:
                cursor.execute(
                    f"INSERT INTO {TABLA_TRABAJADORES} (nombre, documento, telefono, email, "
                    f"cargo, estado, fecha_ingreso, observaciones) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                    fila,
                )
            conexion.commit()
            print(f"  {TABLA_TRABAJADORES}: 5 registros de ejemplo creados.")

        cursor.execute(f"SELECT COUNT(*) FROM {TABLA_TAREAS}")
        if cursor.fetchone()[0] == 0:
            cursor.execute(f"SELECT id_trabajador FROM {TABLA_TRABAJADORES} ORDER BY id_trabajador")
            ids = [fila[0] for fila in cursor.fetchall()] or [None]

            def operario(indice):
                return ids[indice] if indice < len(ids) else ids[0]

            ejemplo_tareas = [
                ("Fertilización foliar lote A", "Aplicación de biofertilizante en crecimiento.", "Lote A-1", "Maíz", "Alta", "COMPLETADA", "2026-09-02", "2026-09-06", "2026-09-05", operario(0)),
                ("Monitoreo de plaga cogollero", "Trampeo y conteo de incidencia en 10 puntos.", "Lote A-2", "Maíz", "Alta", "EN PROCESO", "2026-10-14", "2026-10-24", None, operario(1)),
                ("Mantenimiento de tractor", "Cambio de filtros y revisión hidráulica.", "Taller", "N/A", "Media", "PENDIENTE", "2026-10-27", "2026-11-04", None, operario(2)),
                ("Instalación de cintas de riego", "Ampliación del goteo en 2 hectáreas.", "Lote B-3", "Tomate", "Alta", "EN PROCESO", "2026-10-20", "2026-10-30", None, operario(3)),
                ("Inventario de insumos octubre", "Conteo físico y conciliación con sistema.", "Bodega 1", "N/A", "Baja", "COMPLETADA", "2026-10-01", "2026-10-10", "2026-10-09", operario(4)),
                ("Cosecha de lote C", "Recolección y clasificación por calibre.", "Lote C-1", "Aguacate", "Alta", "PENDIENTE", "2026-11-02", "2026-11-12", None, operario(0)),
                ("Control de malezas lote C", "Guadañada y cobertura vegetal.", "Lote C-2", "Aguacate", "Media", "INCOMPLETA", "2026-10-08", "2026-10-15", None, operario(1)),
                ("Análisis de suelo lote B", "Muestreo compuesto a laboratorio.", "Lote B-1", "Tomate", "Media", "COMPLETADA", "2026-09-20", "2026-09-28", "2026-09-30", operario(2)),
                ("Poda de formación frutales", "Poda sanitaria y direccionamiento.", "Lote D-1", "Mango", "Media", "EN PROCESO", "2026-10-18", "2026-10-29", None, operario(3)),
                ("Capacitación BPA al personal", "Taller de buenas prácticas agrícolas.", "Sala", "N/A", "Baja", "COMPLETADA", "2026-10-11", "2026-10-11", "2026-10-11", operario(4)),
            ]
            for fila in ejemplo_tareas:
                cursor.execute(
                    f"INSERT INTO {TABLA_TAREAS} (titulo, descripcion, lote, cultivo, prioridad, "
                    f"estado_tarea, fecha_inicio, fecha_limite, fecha_completada, id_trabajador) "
                    f"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    fila,
                )
            conexion.commit()
            print(f"  {TABLA_TAREAS}: 10 registros de ejemplo creados.")

        cursor.close()
        conexion.close()

        print("\nEsquema listo. Las contraseñas de las cuentas semilla se toman de tu entorno (.env).")
    except Error as error:
        print(f"Error al inicializar la base de datos: {error}")


if __name__ == "__main__":
    # En local:  python app.py   ->  http://127.0.0.1:5000
    # En un servidor, el puerto lo define la variable de entorno PORT y
    # el modo depurador se activa solo con SGA_DEBUG=1.
    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", "5000")),
        debug=os.environ.get("SGA_DEBUG", "0") == "1",
    )
