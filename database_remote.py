import mysql.connector
import pandas as pd
import re
import secrets
from werkzeug.security import generate_password_hash, check_password_hash
from config import Config

class DBConnection:
    def __enter__(self):
        self.conn = mysql.connector.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            database=Config.MYSQL_DB
        )
        self.cursor = self.conn.cursor(dictionary=True)
        return self.cursor

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.conn.commit()
        self.cursor.close()
        self.conn.close()

def registrar_voto(estudiante_id, candidato_id):
    try:
        if ya_voto(estudiante_id):
            return "Este estudiante ya ha votado."
        
        with DBConnection() as cursor:
            cursor.execute("INSERT INTO votos (estudiante_id, candidato_id) VALUES (%s, %s)", (estudiante_id, candidato_id))
            cursor.execute("UPDATE estudiantes SET ha_votado = 1 WHERE id = %s", (estudiante_id,))
        
        return "Voto registrado exitosamente."
    except mysql.connector.Error as err:
        # Maneja los errores específicos de la base de datos aquí
        return str(err)

def obtener_candidatos():
    with DBConnection() as cursor:
        cursor.execute("SELECT id, nombre, COALESCE(imagen, 'default.png') as imagen FROM candidatos")
        return cursor.fetchall()

def obtener_estudiante_por_cedula(cedula):
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT id, nombre, apellido1, apellido2, cedula, nivel
            FROM estudiantes
            WHERE REPLACE(REPLACE(REPLACE(cedula, '-', ''), ' ', ''), '.', '') = %s
               OR cedula = %s
            LIMIT 1
        """, (cedula, cedula))
        return cursor.fetchone()

def obtener_resultados():
    with DBConnection() as cursor:
        cursor.execute("SELECT candidato_id, COUNT(*) as votos FROM votos GROUP BY candidato_id")
        return cursor.fetchall()

def ya_voto(estudiante_id):
    try:
        with DBConnection() as cursor:
            cursor.execute("SELECT EXISTS(SELECT 1 FROM votos WHERE estudiante_id = %s) AS votado", (estudiante_id,))
            result = cursor.fetchone()
            return bool(result['votado']) if result else False
    except mysql.connector.Error as err:
        # Maneja los errores específicos de la base de datos aquí
        return str(err)

def registrar_candidato(nombre, imagen_path=None):
    try:
        if not imagen_path:
            imagen_path = 'default.png'
        
        with DBConnection() as cursor:
            cursor.execute("INSERT INTO candidatos (nombre, imagen) VALUES (%s, %s)", (nombre, imagen_path))
    except mysql.connector.Error as err:
        # Maneja los errores específicos de la base de datos aquí
        return str(err)

def obtener_candidato_por_id(id):
    with DBConnection() as cursor:
        cursor.execute("SELECT * FROM candidatos WHERE id = %s", (id,))
        return cursor.fetchone()

def actualizar_candidato(id, nombre, imagen_path):
    with DBConnection() as cursor:
        if imagen_path:
            cursor.execute("UPDATE candidatos SET nombre = %s, imagen = %s WHERE id = %s", (nombre, imagen_path, id))
        else:
            cursor.execute("UPDATE candidatos SET nombre = %s WHERE id = %s", (nombre, id))

def eliminar_candidato(id):
    try:
        with DBConnection() as cursor:
            cursor.execute("DELETE FROM candidatos WHERE id = %s", (id,))
    except mysql.connector.Error as err:
        if err.errno == 1451:
            return False, "No se puede eliminar el candidato porque tiene votos asociados."
        else:
            raise
    return True, "Candidato eliminado correctamente."

def obtener_candidatos_activos():
    with DBConnection() as cursor:
        cursor.execute("SELECT * FROM candidatos WHERE activo = TRUE")
        return cursor.fetchall()

def obtener_todos_los_estudiantes():
    with DBConnection() as cursor:
        cursor.execute("SELECT * FROM estudiantes ORDER BY nombre, apellido1, apellido2")
        return cursor.fetchall()

def obtener_abstencionistas():
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT id, nombre, apellido1, apellido2, cedula, nivel
            FROM estudiantes
            WHERE ha_votado = 0
            ORDER BY nivel, apellido1, apellido2, nombre
        """)
        return cursor.fetchall()

def agregar_estudiante(nombre, apellido1, apellido2, nivel, cedula):
    with DBConnection() as cursor:
        cursor.execute("INSERT INTO estudiantes (nombre, apellido1, apellido2, nivel, cedula) VALUES (%s, %s, %s, %s, %s)", (nombre, apellido1, apellido2, nivel, cedula))

def actualizar_estudiante(id_estudiante, nombre, apellido1, apellido2, nivel, cedula):
    with DBConnection() as cursor:
        cursor.execute("UPDATE estudiantes SET nombre=%s, apellido1=%s, apellido2=%s, nivel=%s, cedula=%s WHERE id=%s", (nombre, apellido1, apellido2, nivel, cedula, id_estudiante))

def importar_estudiantes_desde_excel(archivo_excel):
    if archivo_excel.lower().endswith('.csv'):
        df = pd.read_csv(archivo_excel)
    else:
        df = pd.read_excel(archivo_excel, engine='openpyxl')

    # Normaliza encabezados para tolerar variaciones comunes.
    normalize = lambda v: re.sub(r'[^a-z0-9]', '', str(v).strip().lower())
    col_map = {normalize(c): c for c in df.columns}

    required = {
        "nombre": ["nombre", "nombres"],
        "apellido1": ["apellido1", "primerapellido", "apellido"],
        "apellido2": ["apellido2", "segundoapellido"],
        "cedula": ["cedula", "identificacion", "id"],
        "nivel": ["nivel", "grado", "seccion"],
    }

    resolved = {}
    for target, aliases in required.items():
        found = None
        for alias in aliases:
            if alias in col_map:
                found = col_map[alias]
                break
        if not found:
            raise ValueError(
                f"Falta la columna requerida: {target}. "
                "Columnas esperadas: Nombre, Apellido1, Apellido2, Cedula, Nivel."
            )
        resolved[target] = found

    df = df.fillna("")
    for key in resolved:
        df[resolved[key]] = df[resolved[key]].astype(str).str.strip()

    total_rows = len(df)
    empty_rows = 0
    upserted = 0

    with DBConnection() as cursor:
        query = """
        INSERT INTO estudiantes (nombre, apellido1, apellido2, cedula, nivel)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        nombre=VALUES(nombre), apellido1=VALUES(apellido1), apellido2=VALUES(apellido2), nivel=VALUES(nivel)
        """
        for _, row in df.iterrows():
            nombre = row[resolved["nombre"]]
            apellido1 = row[resolved["apellido1"]]
            apellido2 = row[resolved["apellido2"]]
            cedula = row[resolved["cedula"]]
            nivel = row[resolved["nivel"]]

            if not (nombre and apellido1 and apellido2 and cedula and nivel):
                empty_rows += 1
                continue

            data = (nombre, apellido1, apellido2, cedula, nivel)
            cursor.execute(query, data)
            upserted += 1

    return {
        "total_rows": total_rows,
        "upserted": upserted,
        "empty_rows": empty_rows,
    }

def get_voting_stats_by_candidate():
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT candidatos.nombre, candidatos.imagen, COUNT(votos.id) AS votos,
                   ROUND((COUNT(votos.id) * 100.0 / (SELECT COUNT(*) FROM votos)), 2) AS porcentaje
            FROM candidatos
            LEFT JOIN votos ON votos.candidato_id = candidatos.id
            GROUP BY candidatos.nombre, candidatos.imagen;
        """)
        return cursor.fetchall()

def get_participation_stats():
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT
                (SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 1) AS participantes,
                (SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 0) AS abstencionistas,
                ROUND((SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 1) * 100.0 / COUNT(*), 2) AS tasa_participacion,
                ROUND((SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 0) * 100.0 / COUNT(*), 2) AS tasa_abstencionismo
            FROM estudiantes;
        """)
        return cursor.fetchone()

def get_participation_by_level():
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT nivel, COUNT(*) AS votantes,
                   ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM estudiantes WHERE nivel = estudiantes.nivel)), 2) AS porcentaje
            FROM estudiantes
            WHERE ha_votado = 1
            GROUP BY nivel;
        """)
        return cursor.fetchall()

def obtener_datos_dashboard():
    with DBConnection() as cursor:
        # Votos por candidato y sus imágenes con porcentajes
        cursor.execute("""
        SELECT candidatos.nombre, candidatos.imagen, COUNT(votos.id) AS votos,
               ROUND((COUNT(votos.id) * 100.0 / (SELECT COUNT(*) FROM votos)), 2) AS porcentaje
        FROM candidatos
        LEFT JOIN votos ON votos.candidato_id = candidatos.id
        GROUP BY candidatos.id, candidatos.nombre, candidatos.imagen;
        """)
        votos_por_candidato = cursor.fetchall()

        # Participación y abstención
        cursor.execute("""
        SELECT
            (SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 1) AS participantes,
            (SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 0) AS abstencionistas,
            ROUND((SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 1) * 100.0 / COUNT(*), 2) AS tasa_participacion,
            ROUND((SELECT COUNT(*) FROM estudiantes WHERE ha_votado = 0) * 100.0 / COUNT(*), 2) AS tasa_abstencionismo
        FROM estudiantes;
        """)
        participacion = cursor.fetchone()

        # Votos por nivel educativo
        cursor.execute("""
        SELECT nivel, COUNT(*) AS votantes,
               ROUND((COUNT(*) * 100.0 / (SELECT COUNT(*) FROM estudiantes WHERE nivel = estudiantes.nivel)), 2) AS porcentaje
        FROM estudiantes
        WHERE ha_votado = 1
        GROUP BY nivel;
        """)
        votos_por_nivel = cursor.fetchall()

        return {
            "votos_por_candidato": votos_por_candidato,
            "participacion": participacion,
            "votos_por_nivel": votos_por_nivel
        }

def register_user(username, password):
    try:
        password_hash = generate_password_hash(password)
        print(password_hash)
        with DBConnection() as cursor:
            cursor.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
        return True, "Usuario registrado exitosamente."
    except mysql.connector.Error as err:
        return False, str(err)

def get_user_by_username(username):
    with DBConnection() as cursor:
        cursor.execute("SELECT * FROM users WHERE username = %s", (username,))
        return cursor.fetchone()

def get_user_by_id(user_id):
    with DBConnection() as cursor:
        cursor.execute("SELECT id, username FROM users WHERE id = %s", (user_id,))
        return cursor.fetchone()

def authenticate_user(username, password):
    user = get_user_by_username(username)
    if user and check_password_hash(user['password_hash'], password):
        return {'id': user['id'], 'username': user['username']}
    return None


def ensure_system_users_table():
    with DBConnection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS system_users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(120) NOT NULL UNIQUE,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(40) NOT NULL DEFAULT 'admin',
                active TINYINT(1) NOT NULL DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("SELECT COUNT(*) AS total FROM system_users")
        total = cursor.fetchone()["total"]
        if total == 0:
            # Migra usuarios existentes (tabla users) como admin.
            try:
                cursor.execute("SELECT username, password_hash FROM users")
                old_users = cursor.fetchall()
            except Exception:
                old_users = []
            for u in old_users:
                cursor.execute(
                    "INSERT IGNORE INTO system_users (username, password_hash, role, active) VALUES (%s, %s, 'admin', 1)",
                    (u["username"], u["password_hash"])
                )
            cursor.execute("SELECT COUNT(*) AS total2 FROM system_users")
            if cursor.fetchone()["total2"] == 0:
                # Fallback inicial si no existe ninguna cuenta.
                cursor.execute(
                    "INSERT INTO system_users (username, password_hash, role, active) VALUES (%s, %s, %s, 1)",
                    ('admin', generate_password_hash('Admin1234!'), 'admin')
                )


def list_system_users():
    ensure_system_users_table()
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT id, username, role, active, created_at, updated_at
            FROM system_users
            ORDER BY role, username
        """)
        return cursor.fetchall()


def get_system_user_by_id(user_id):
    ensure_system_users_table()
    with DBConnection() as cursor:
        cursor.execute("SELECT id, username, role, active FROM system_users WHERE id=%s", (user_id,))
        return cursor.fetchone()


def get_system_user_by_username(username):
    ensure_system_users_table()
    with DBConnection() as cursor:
        cursor.execute("SELECT * FROM system_users WHERE username=%s", (username,))
        return cursor.fetchone()


def create_system_user(username, password, role, active=True):
    ensure_system_users_table()
    pwd = generate_password_hash(password)
    with DBConnection() as cursor:
        cursor.execute(
            "INSERT INTO system_users (username, password_hash, role, active) VALUES (%s, %s, %s, %s)",
            (username, pwd, role, 1 if active else 0)
        )


def update_system_user(user_id, role, active):
    ensure_system_users_table()
    with DBConnection() as cursor:
        cursor.execute(
            "UPDATE system_users SET role=%s, active=%s WHERE id=%s",
            (role, 1 if active else 0, user_id)
        )


def set_system_user_password(user_id, new_password):
    ensure_system_users_table()
    pwd = generate_password_hash(new_password)
    with DBConnection() as cursor:
        cursor.execute("UPDATE system_users SET password_hash=%s WHERE id=%s", (pwd, user_id))


def authenticate_system_user(username, password, role=None):
    user = get_system_user_by_username(username)
    if not user:
        return None
    if not user.get("active"):
        return None
    if role and user.get("role") != role:
        return None
    if check_password_hash(user['password_hash'], password):
        return {'id': user['id'], 'username': user['username'], 'role': user['role']}
    return None


def ensure_builtin_role_user(username, password, role):
    ensure_system_users_table()
    if not username or not password:
        return
    existing = get_system_user_by_username(username)
    if existing:
        # Garantiza rol correcto y activo para cuenta builtin
        with DBConnection() as cursor:
            cursor.execute(
                "UPDATE system_users SET role=%s, active=1 WHERE id=%s",
                (role, existing["id"])
            )
        return
    create_system_user(username, password, role, active=True)


def ensure_voting_settings():
    with DBConnection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS voting_settings (
                id TINYINT NOT NULL PRIMARY KEY,
                voting_closed TINYINT(1) NOT NULL DEFAULT 0,
                updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)
        cursor.execute("SELECT COUNT(*) AS total FROM voting_settings WHERE id = 1")
        row = cursor.fetchone()
        if row["total"] == 0:
            cursor.execute("INSERT INTO voting_settings (id, voting_closed) VALUES (1, 0)")


def get_voting_status():
    ensure_voting_settings()
    with DBConnection() as cursor:
        cursor.execute("SELECT voting_closed, updated_at FROM voting_settings WHERE id = 1")
        row = cursor.fetchone()
        return {
            "voting_closed": bool(row["voting_closed"]) if row else False,
            "updated_at": row["updated_at"] if row else None
        }


def set_voting_closed(closed):
    ensure_voting_settings()
    with DBConnection() as cursor:
        cursor.execute(
            "UPDATE voting_settings SET voting_closed = %s WHERE id = 1",
            (1 if closed else 0,)
        )


def ensure_terminales_table():
    with DBConnection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS terminales_votacion (
                id INT AUTO_INCREMENT PRIMARY KEY,
                codigo VARCHAR(64) NOT NULL UNIQUE,
                nombre VARCHAR(120) NOT NULL,
                ubicacion VARCHAR(120) NULL,
                token VARCHAR(128) NOT NULL,
                activa TINYINT(1) NOT NULL DEFAULT 1,
                last_seen DATETIME NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)


def listar_terminales():
    ensure_terminales_table()
    with DBConnection() as cursor:
        cursor.execute("""
            SELECT id, codigo, nombre, ubicacion, activa, last_seen,
                   CASE
                     WHEN activa = 0 THEN 'inactiva'
                     WHEN last_seen IS NOT NULL AND TIMESTAMPDIFF(SECOND, last_seen, NOW()) <= 120 THEN 'en_linea'
                     ELSE 'fuera_de_linea'
                   END AS estado
            FROM terminales_votacion
            ORDER BY nombre, codigo
        """)
        return cursor.fetchall()


def crear_terminal(codigo, nombre, ubicacion):
    ensure_terminales_table()
    token = secrets.token_urlsafe(24)
    with DBConnection() as cursor:
        cursor.execute(
            """
            INSERT INTO terminales_votacion (codigo, nombre, ubicacion, token, activa)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (codigo, nombre, ubicacion or None, token)
        )
    return token


def obtener_terminal_por_codigo(codigo):
    ensure_terminales_table()
    with DBConnection() as cursor:
        cursor.execute(
            "SELECT id, codigo, nombre, ubicacion, token, activa FROM terminales_votacion WHERE codigo = %s LIMIT 1",
            (codigo,)
        )
        return cursor.fetchone()


def obtener_terminal_por_id(terminal_id):
    ensure_terminales_table()
    with DBConnection() as cursor:
        cursor.execute(
            "SELECT id, codigo, nombre, ubicacion, token, activa, last_seen FROM terminales_votacion WHERE id = %s LIMIT 1",
            (terminal_id,)
        )
        return cursor.fetchone()


def actualizar_terminal(terminal_id, nombre, ubicacion, activa):
    ensure_terminales_table()
    with DBConnection() as cursor:
        cursor.execute(
            "UPDATE terminales_votacion SET nombre=%s, ubicacion=%s, activa=%s WHERE id=%s",
            (nombre, ubicacion or None, 1 if activa else 0, terminal_id)
        )


def rotar_token_terminal(terminal_id):
    ensure_terminales_table()
    token = secrets.token_urlsafe(24)
    with DBConnection() as cursor:
        cursor.execute("UPDATE terminales_votacion SET token=%s WHERE id=%s", (token, terminal_id))
    return token


def eliminar_terminal(terminal_id):
    ensure_terminales_table()
    with DBConnection() as cursor:
        cursor.execute("DELETE FROM terminales_votacion WHERE id = %s", (terminal_id,))


def marcar_terminal_en_linea(terminal_id):
    ensure_terminales_table()
    with DBConnection() as cursor:
        cursor.execute("UPDATE terminales_votacion SET last_seen = NOW() WHERE id=%s", (terminal_id,))


def autoregistrar_terminal(codigo, nombre=None, ubicacion=None):
    ensure_terminales_table()
    token = secrets.token_urlsafe(24)
    nombre_final = (nombre or codigo or "Terminal").strip()
    with DBConnection() as cursor:
        cursor.execute(
            "SELECT id FROM terminales_votacion WHERE codigo=%s LIMIT 1",
            (codigo,)
        )
        row = cursor.fetchone()
        if row:
            cursor.execute(
                """
                UPDATE terminales_votacion
                SET nombre=%s, ubicacion=%s, token=%s, activa=1, updated_at=NOW()
                WHERE id=%s
                """,
                (nombre_final, ubicacion or None, token, row["id"])
            )
            return {"terminal_id": row["id"], "token": token, "action": "updated"}
        cursor.execute(
            """
            INSERT INTO terminales_votacion (codigo, nombre, ubicacion, token, activa)
            VALUES (%s, %s, %s, %s, 1)
            """,
            (codigo, nombre_final, ubicacion or None, token)
        )
        new_id = cursor.lastrowid
        return {"terminal_id": new_id, "token": token, "action": "created"}


def ensure_bitacora_table():
    with DBConnection() as cursor:
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bitacora_critica (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                actor VARCHAR(120) NOT NULL,
                accion VARCHAR(120) NOT NULL,
                detalle TEXT NULL,
                ip_origen VARCHAR(64) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
        """)


def registrar_evento_critico(actor, accion, detalle=None, ip_origen=None):
    ensure_bitacora_table()
    with DBConnection() as cursor:
        cursor.execute(
            "INSERT INTO bitacora_critica (actor, accion, detalle, ip_origen) VALUES (%s, %s, %s, %s)",
            (actor, accion, detalle, ip_origen)
        )


def obtener_bitacora_critica(limit=300):
    ensure_bitacora_table()
    with DBConnection() as cursor:
        cursor.execute(
            """
            SELECT id, actor, accion, detalle, ip_origen, created_at
            FROM bitacora_critica
            ORDER BY id DESC
            LIMIT %s
            """,
            (limit,)
        )
        return cursor.fetchall()
