from datetime import datetime
import io
import os
import csv
from functools import wraps
from flask import Flask, flash, jsonify, request, render_template, send_file, redirect, session, url_for
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required

from werkzeug.utils import secure_filename
import pandas as pd
import util.database as db
import util.pdf_generator as pdf_gen

app = Flask(__name__, static_url_path='/votaciones_backend/static')
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app.config['UPLOAD_FOLDER'] = os.path.join(BASE_DIR, 'static', 'uploads')
app.config['APPLICATION_ROOT'] = '/votaciones'
app.secret_key = '123'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
db.ensure_voting_settings()
db.ensure_terminales_table()
db.ensure_bitacora_table()
db.ensure_system_users_table()



@app.route('/votaciones')
def index():
    return votar()


@app.route('/votaciones/')
def index_slash():
    return votar()

login_manager = LoginManager()
login_manager.init_app(app)

TERMINAL_ADMIN_USER = os.getenv('TERMINAL_ADMIN_USER', 'terminaladmin')
TERMINAL_ADMIN_PASS = os.getenv('TERMINAL_ADMIN_PASS', 'Cambiar-12345')
VIEWER_USER = os.getenv('VIEWER_USER', 'visor')
VIEWER_PASS = os.getenv('VIEWER_PASS', 'Cambiar-12345')
db.ensure_builtin_role_user(TERMINAL_ADMIN_USER, TERMINAL_ADMIN_PASS, 'terminal_admin')
db.ensure_builtin_role_user(VIEWER_USER, VIEWER_PASS, 'viewer')

VIEWER_ALLOWED_ENDPOINTS = {
    'viewer_login',
    'viewer_logout',
    'viewer_dashboard',
    'voting_stats',
    'descargar_corte',
    'static',
}

class User(UserMixin):
    def __init__(self, id, username, role='admin'):
        self.id = id
        self.username = username
        self.role = role

    def get_id(self):
        return str(self.id)


@login_manager.user_loader
def load_user(user_id):
    user = db.get_system_user_by_id(user_id)
    if not user:
        return None
    return User(user['id'], user['username'], user.get('role', 'admin'))


def _current_terminal():
    terminal_id = session.get('terminal_id')
    if not terminal_id:
        return None
    terminal = db.obtener_terminal_por_id(terminal_id)
    if not terminal:
        session.pop('terminal_id', None)
        session.pop('terminal_code', None)
        return None
    if not terminal.get('activa'):
        session.pop('terminal_id', None)
        session.pop('terminal_code', None)
        return None
    return terminal


def require_terminal_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        terminal = _current_terminal()
        if not terminal:
            if request.path.startswith('/votaciones/terminal/'):
                return fn(*args, **kwargs)
            flash('Terminal no autorizada. Ingrese codigo y token de terminal.', 'error')
            return redirect(url_for('terminal_login', next=request.path))
        db.marcar_terminal_en_linea(terminal['id'])
        return fn(*args, **kwargs)
    return wrapper


def terminal_admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('terminal_admin_auth'):
            return redirect(url_for('terminal_admin_login'))
        return fn(*args, **kwargs)
    return wrapper


def dashboard_access_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if session.get('viewer_auth') or session.get('_user_id'):
            return fn(*args, **kwargs)
        return redirect(url_for('viewer_login'))
    return wrapper


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not session.get('_user_id'):
            return redirect(url_for('login'))
        if session.get('user_role') != 'admin':
            flash('Acceso solo para administradores.', 'error')
            return redirect(url_for('mantenimiento'))
        return fn(*args, **kwargs)
    return wrapper


def _actor_name():
    if session.get('terminal_admin_auth'):
        return f"terminal_admin:{session.get('terminal_admin_user', 'unknown')}"
    return f"admin:{session.get('_user_id', 'unknown')}"


@app.before_request
def restrict_viewer_scope():
    # Si la sesion es de visor, bloquear cualquier ruta fuera de su alcance.
    if session.get('viewer_auth'):
        endpoint = request.endpoint or ''
        if endpoint not in VIEWER_ALLOWED_ENDPOINTS:
            flash('Acceso no permitido para usuario visor.', 'error')
            return redirect(url_for('viewer_dashboard'))


@app.route('/votaciones/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = db.authenticate_system_user(username, password, role='admin')
        if user:
            login_user(User(user['id'], user['username'], user.get('role', 'admin')))
            session['user_role'] = user.get('role', 'admin')
            flash('Inicio de sesión exitoso', 'success')
            return redirect(url_for('mantenimiento'))
        else:
            flash('Credenciales incorrectas', 'error')
    return render_template('login.html')


@app.route('/votaciones/logout')
@login_required
def logout():
    logout_user()
    session.pop('user_role', None)
    flash('Sesión cerrada exitosamente', 'success')
    return redirect(url_for('login'))

@app.route('/votaciones/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash('Las contraseñas no coinciden', 'error')
            return redirect('/votaciones/register')

        success, message = db.register_user(username, password)

        if success:
            flash(message, 'success')
            return redirect('/votaciones/login')
        else:
            flash(message, 'error')
            return redirect('/votaciones/register')

    return render_template('register.html')


@app.route('/votaciones/api/voting-stats')
@dashboard_access_required
def voting_stats():
    status = db.get_voting_status()
    # El visor nunca ve resultados por candidato.
    if session.get('viewer_auth'):
        candidate_stats = []
    else:
        candidate_stats = db.get_voting_stats_by_candidate() if status["voting_closed"] else []
    participation_stats = db.get_participation_stats()
    level_stats = db.get_participation_by_level()
    return jsonify({
        'voting_closed': status["voting_closed"],
        'is_viewer': bool(session.get('viewer_auth')),
        'candidates': candidate_stats,
        'participation': participation_stats,
        'levels': level_stats
    })


@app.route('/votaciones/votar', methods=['GET', 'POST'])
@require_terminal_auth
def votar():
    if request.method == 'POST':
        cedula = (request.form.get('cedula') or '').strip()
        cedula_normalizada = ''.join(ch for ch in cedula if ch.isalnum())
        estudiante = db.obtener_estudiante_por_cedula(cedula_normalizada)
        if estudiante:
            if db.ya_voto(estudiante['id']):
                flash('Ya has votado. No puedes votar más de una vez.', 'error')
                return redirect(url_for('votar'))
            session['estudiante_id'] = estudiante['id']
            return render_template('confirmar_estudiante.html', estudiante=estudiante)
        else:
            flash('Estudiante no encontrado', 'error')
            return redirect(url_for('votar'))
    return render_template('solicitar_cedula.html')


@app.route('/votaciones/descargar_acta')
@dashboard_access_required
def descargar_acta():
    if session.get('viewer_auth'):
        flash('El usuario visor no puede generar acta final.', 'error')
        return redirect(url_for('viewer_dashboard'))
    status = db.get_voting_status()
    if not status["voting_closed"]:
        flash('El acta final solo se puede generar cuando la votacion este cerrada.', 'error')
        return redirect(url_for('mantenimiento'))
    datos = db.obtener_datos_dashboard()
    pdf_bytes = pdf_gen.generar_pdf_acta(datos)
    # Obtener la fecha actual
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    
    # Concatenar la fecha actual al nombre del archivo
    download_name = f'ActaFinalCierre_{fecha_actual}.pdf'
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )

@app.route('/votaciones/descargar_corte')
@dashboard_access_required
def descargar_corte():
    # Corte sin informacion de candidatos (solo participacion/abstencion y nivel).
    datos_completos = db.obtener_datos_dashboard()
    datos = {
        "votos_por_candidato": [],
        "participacion": datos_completos.get("participacion"),
        "votos_por_nivel": datos_completos.get("votos_por_nivel", [])
    }
    pdf_bytes = pdf_gen.generar_pdf_corte(datos)
    # Obtener la fecha actual
    fecha_actual = datetime.now().strftime("%Y-%m-%d_%H-%M")
    
    # Concatenar la fecha actual al nombre del archivo
    download_name = f'Corte_{fecha_actual}.pdf'
    return send_file(
        io.BytesIO(pdf_bytes),
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf'
    )

@app.route('/votaciones/candidatos', methods=['GET', 'POST'])
@admin_required
def candidatos():
    if request.method == 'POST':
        candidato_id = request.form.get('candidato_id')
        nombre = request.form['nombre']
        imagen = request.files.get('imagen')
        filename = None

        if imagen and imagen.filename:
            filename = secure_filename(imagen.filename)
            imagen_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            imagen.save(imagen_path)

        if candidato_id:
            db.actualizar_candidato(candidato_id, nombre, filename)
        else:
            db.registrar_candidato(nombre, filename)

        flash('Operación completada correctamente', 'success')
        return redirect(url_for('candidatos'))
    else:
        candidatos = db.obtener_candidatos()
        return render_template('mantenimiento_candidatos.html', candidatos=candidatos)


@app.route('/votaciones/actualizar_candidato/<int:id>', methods=['GET', 'POST'])
@admin_required
def actualizar_candidato(id):
    if request.method == 'POST':
        nombre = request.form['nombre']
        imagen = request.files['imagen']
        filename = secure_filename(imagen.filename) if imagen else None

        if filename:
            imagen_path = filename
            imagen.save(imagen_path)
        db.actualizar_candidato(id, nombre, imagen_path if filename else None)
        flash('Candidato actualizado correctamente', 'success')
        return redirect(url_for('candidatos'))
    else:
        candidato = db.obtener_candidato_por_id(id)
        return render_template('actualizar_candidato.html', candidato=candidato)


@app.route('/votaciones/eliminar_candidato/<int:id>', methods=['POST'])
@admin_required
def eliminar_candidato(id):
    success, message = db.eliminar_candidato(id)
    if not success:
        flash(message, 'error')
    else:
        flash('Candidato eliminado correctamente', 'success')
    return redirect(url_for('candidatos'))


@app.route('/votaciones/mostrar_candidatos', methods=['GET'])
@require_terminal_auth
def mostrar_candidatos():
    if 'estudiante_id' not in session:
        return redirect(url_for('votar'))
    
    candidatos = db.obtener_candidatos_activos()
    return render_template('lista_candidatos.html', candidatos=candidatos)


@app.route('/votaciones/procesar_voto', methods=['POST'])
@require_terminal_auth
def procesar_voto():
    candidato_id = request.form.get('candidato_id')
    estudiante_id = session.pop('estudiante_id', None)
    if estudiante_id and not db.ya_voto(estudiante_id):
        db.registrar_voto(estudiante_id, candidato_id)
        return redirect(url_for('gracias'))
    else:
        flash("Error en la votación o ya has votado.", 'error')
        return redirect(url_for('votar'))


@app.route('/votaciones/estudiantes', methods=['GET', 'POST'])
@admin_required
def estudiantes():
    if request.method == 'POST':
        id_estudiante = request.form.get('id_estudiante')
        nombre = request.form['nombre']
        apellido1 = request.form['apellido1']
        apellido2 = request.form['apellido2']
        nivel = request.form['nivel']
        cedula = request.form['cedula']

        if id_estudiante:
            db.actualizar_estudiante(id_estudiante, nombre, apellido1, apellido2, nivel, cedula)
        else:
            db.agregar_estudiante(nombre, apellido1, apellido2, nivel, cedula)

        flash('Operación completada correctamente', 'success')
        return redirect(url_for('estudiantes'))
    
    estudiantes = db.obtener_todos_los_estudiantes()
    return render_template('mantenimiento_estudiantes.html', estudiantes=estudiantes)


@app.route('/votaciones/upload', methods=['GET', 'POST'])
@admin_required
def upload_file():
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No se selecciono ningun archivo', 'error')
            return redirect(request.url)

        file = request.files['file']
        if file.filename == '':
            flash('No se selecciono ningun archivo', 'error')
            return redirect(request.url)

        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        if ext not in ('xlsx', 'xls', 'csv'):
            flash('Formato no permitido. Usa .xlsx, .xls o .csv', 'error')
            return redirect(request.url)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)

        try:
            result = db.importar_estudiantes_desde_excel(file_path)
            flash(
                f"Carga completada: {result['upserted']} registros procesados, "
                f"{result['empty_rows']} filas omitidas de {result['total_rows']}.",
                'success'
            )
        except Exception as e:
            flash(f'Error al importar archivo: {e}', 'error')

        return redirect(url_for('upload_file'))

    return render_template('upload.html')


@app.route('/votaciones/upload/plantilla-csv')
@admin_required
def plantilla_estudiantes_csv():
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Nombre', 'Apellido1', 'Apellido2', 'Cedula', 'Nivel'])
    writer.writerow(['AARON', 'SOTO', 'NAVARRO', '120420584', '10-5'])
    writer.writerow(['MARIA', 'ROJAS', 'MORA', '116780923', '11-2'])
    mem = io.BytesIO(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    return send_file(
        mem,
        as_attachment=True,
        download_name='plantilla_padron_estudiantes.csv',
        mimetype='text/csv'
    )


@app.route('/votaciones/upload/plantilla-xlsx')
@admin_required
def plantilla_estudiantes_xlsx():
    df = pd.DataFrame([
        {'Nombre': 'AARON', 'Apellido1': 'SOTO', 'Apellido2': 'NAVARRO', 'Cedula': '120420584', 'Nivel': '10-5'},
        {'Nombre': 'MARIA', 'Apellido1': 'ROJAS', 'Apellido2': 'MORA', 'Cedula': '116780923', 'Nivel': '11-2'}
    ])
    mem = io.BytesIO()
    with pd.ExcelWriter(mem, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Padron')
    mem.seek(0)
    return send_file(
        mem,
        as_attachment=True,
        download_name='plantilla_padron_estudiantes.xlsx',
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )

@app.route('/votaciones/gracias')
def gracias():
    return render_template('gracias.html')


@app.route('/votaciones/mantenimiento')
@admin_required
def mantenimiento():
    voting_status = db.get_voting_status()
    return render_template('mantenimiento.html', voting_closed=voting_status["voting_closed"], is_viewer=False)


@app.route('/votaciones/visor/login', methods=['GET', 'POST'])
def viewer_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = db.authenticate_system_user(username, password, role='viewer')
        if user:
            session['viewer_auth'] = True
            session['viewer_user'] = user['username']
            db.registrar_evento_critico(f"viewer:{user['username']}", 'login_viewer', 'Inicio sesion visor dashboard', request.remote_addr)
            return redirect(url_for('viewer_dashboard'))
        flash('Credenciales invalidas', 'error')
    return render_template('viewer_login.html')


@app.route('/votaciones/visor/logout', methods=['POST'])
def viewer_logout():
    if session.get('viewer_auth'):
        db.registrar_evento_critico(
            f"viewer:{session.get('viewer_user', 'unknown')}",
            'logout_viewer',
            'Cierre sesion visor dashboard',
            request.remote_addr
        )
    session.pop('viewer_auth', None)
    session.pop('viewer_user', None)
    flash('Sesion cerrada.', 'success')
    return redirect(url_for('viewer_login'))


@app.route('/votaciones/visor/dashboard')
@dashboard_access_required
def viewer_dashboard():
    voting_status = db.get_voting_status()
    return render_template('mantenimiento.html', voting_closed=voting_status["voting_closed"], is_viewer=True)


@app.route('/votaciones/mantenimiento/cerrar-votacion', methods=['POST'])
@admin_required
def cerrar_votacion():
    db.set_voting_closed(True)
    db.registrar_evento_critico(_actor_name(), 'cerrar_votacion', 'Se cerro la votacion', request.remote_addr)
    flash('Votacion cerrada. Ahora se pueden ver resultados finales.', 'success')
    return redirect(url_for('mantenimiento'))


@app.route('/votaciones/mantenimiento/abrir-votacion', methods=['POST'])
@admin_required
def abrir_votacion():
    db.set_voting_closed(False)
    db.registrar_evento_critico(_actor_name(), 'abrir_votacion', 'Se reabrio la votacion', request.remote_addr)
    flash('Votacion reabierta. Los resultados vuelven a ocultarse.', 'success')
    return redirect(url_for('mantenimiento'))


@app.route('/votaciones/mantenimiento-sitio')
@admin_required
def mantenimiento_sitio():
    terminales = db.listar_terminales()
    return render_template('mantenimiento_sitio.html', terminales=terminales)


@app.route('/votaciones/terminal/login', methods=['GET', 'POST'])
def terminal_login():
    if request.method == 'POST':
        codigo = (request.form.get('codigo') or '').strip()
        token = (request.form.get('token') or '').strip()
        terminal = db.obtener_terminal_por_codigo(codigo)
        if not terminal or not terminal.get('activa') or terminal.get('token') != token:
            flash('Credenciales de terminal invalidas.', 'error')
            return redirect(url_for('terminal_login'))
        session['terminal_id'] = terminal['id']
        session['terminal_code'] = terminal['codigo']
        db.marcar_terminal_en_linea(terminal['id'])
        flash(f"Terminal autorizada: {terminal['nombre']}", 'success')
        next_url = request.args.get('next') or url_for('votar')
        return redirect(next_url)
    return render_template('terminal_login.html')


@app.route('/votaciones/terminal/autoregistro', methods=['GET', 'POST'])
def terminal_autoregistro():
    if request.method == 'POST':
        admin_user = (request.form.get('admin_user') or '').strip()
        admin_pass = request.form.get('admin_pass') or ''
        codigo = (request.form.get('codigo') or '').strip()
        nombre = (request.form.get('nombre') or '').strip()
        ubicacion = (request.form.get('ubicacion') or '').strip()

        auth_user = db.authenticate_system_user(admin_user, admin_pass, role='terminal_admin')
        if not auth_user:
            flash('Credenciales de autorizacion invalidas.', 'error')
            return redirect(url_for('terminal_autoregistro'))
        if not codigo:
            flash('Debe ingresar el codigo de la terminal.', 'error')
            return redirect(url_for('terminal_autoregistro'))

        result = db.autoregistrar_terminal(codigo, nombre, ubicacion)
        terminal = db.obtener_terminal_por_codigo(codigo)
        session['terminal_id'] = terminal['id']
        session['terminal_code'] = terminal['codigo']
        db.marcar_terminal_en_linea(terminal['id'])
        db.registrar_evento_critico(
            f"autoregistro:{auth_user['username']}",
            'autoregistro_terminal',
            f"codigo={codigo}, action={result['action']}",
            request.remote_addr
        )
        flash(f"Terminal activa. Token generado: {result['token']}", 'success')
        return redirect(url_for('terminal_login'))
    return render_template('terminal_autoregistro.html')


@app.route('/votaciones/terminal/logout', methods=['POST'])
def terminal_logout():
    session.pop('terminal_id', None)
    session.pop('terminal_code', None)
    flash('Terminal desvinculada.', 'success')
    return redirect(url_for('terminal_login'))


@app.route('/votaciones/terminal/ping', methods=['POST'])
@require_terminal_auth
def terminal_ping():
    return jsonify({"ok": True, "terminal": session.get("terminal_code")})


@app.route('/votaciones/mantenimiento/terminales/crear', methods=['POST'])
@admin_required
def crear_terminal():
    codigo = (request.form.get('codigo') or '').strip()
    nombre = (request.form.get('nombre') or '').strip()
    ubicacion = (request.form.get('ubicacion') or '').strip()
    if not codigo or not nombre:
        flash('Codigo y nombre son obligatorios.', 'error')
        return redirect(url_for('mantenimiento_sitio'))
    try:
        token = db.crear_terminal(codigo, nombre, ubicacion)
    except Exception as e:
        flash(f'No se pudo crear terminal: {e}', 'error')
        return redirect(url_for('mantenimiento_sitio'))
    db.registrar_evento_critico(_actor_name(), 'crear_terminal', f'codigo={codigo}, nombre={nombre}, ubicacion={ubicacion}', request.remote_addr)
    flash(f'Terminal creada. Token: {token}', 'success')
    return redirect(url_for('mantenimiento_sitio'))


@app.route('/votaciones/mantenimiento/terminales/actualizar/<int:terminal_id>', methods=['POST'])
@admin_required
def actualizar_terminal(terminal_id):
    nombre = (request.form.get('nombre') or '').strip()
    ubicacion = (request.form.get('ubicacion') or '').strip()
    activa = request.form.get('activa') == '1'
    if not nombre:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('mantenimiento_sitio'))
    db.actualizar_terminal(terminal_id, nombre, ubicacion, activa)
    db.registrar_evento_critico(_actor_name(), 'actualizar_terminal', f'id={terminal_id}, activa={activa}, nombre={nombre}', request.remote_addr)
    flash('Terminal actualizada.', 'success')
    return redirect(url_for('mantenimiento_sitio'))


@app.route('/votaciones/mantenimiento/terminales/rotar-token/<int:terminal_id>', methods=['POST'])
@admin_required
def rotar_token_terminal(terminal_id):
    token = db.rotar_token_terminal(terminal_id)
    db.registrar_evento_critico(_actor_name(), 'rotar_token_terminal', f'id={terminal_id}', request.remote_addr)
    flash(f'Nuevo token generado: {token}', 'success')
    return redirect(url_for('mantenimiento_sitio'))


@app.route('/votaciones/mantenimiento/terminales/eliminar/<int:terminal_id>', methods=['POST'])
@admin_required
def eliminar_terminal(terminal_id):
    db.eliminar_terminal(terminal_id)
    db.registrar_evento_critico(_actor_name(), 'eliminar_terminal', f'id={terminal_id}', request.remote_addr)
    flash('Terminal eliminada.', 'success')
    return redirect(url_for('mantenimiento_sitio'))


@app.route('/votaciones/terminal-admin/login', methods=['GET', 'POST'])
def terminal_admin_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        user = db.authenticate_system_user(username, password, role='terminal_admin')
        if user:
            session['terminal_admin_auth'] = True
            session['terminal_admin_user'] = user['username']
            db.registrar_evento_critico(f"terminal_admin:{user['username']}", 'login_terminal_admin', 'Inicio de sesion de terminal admin', request.remote_addr)
            return redirect(url_for('terminal_admin_panel'))
        flash('Credenciales invalidas', 'error')
    return render_template('terminal_admin_login.html')


@app.route('/votaciones/terminal-admin/logout', methods=['POST'])
@terminal_admin_required
def terminal_admin_logout():
    actor = f"terminal_admin:{session.get('terminal_admin_user', 'unknown')}"
    session.pop('terminal_admin_auth', None)
    session.pop('terminal_admin_user', None)
    db.registrar_evento_critico(actor, 'logout_terminal_admin', 'Cierre de sesion de terminal admin', request.remote_addr)
    flash('Sesion cerrada.', 'success')
    return redirect(url_for('terminal_admin_login'))


@app.route('/votaciones/terminal-admin')
@terminal_admin_required
def terminal_admin_panel():
    terminales = db.listar_terminales()
    bitacora = db.obtener_bitacora_critica(200)
    return render_template('terminal_admin.html', terminales=terminales, bitacora=bitacora)


@app.route('/votaciones/terminal-admin/terminales/crear', methods=['POST'])
@terminal_admin_required
def terminal_admin_crear_terminal():
    codigo = (request.form.get('codigo') or '').strip()
    nombre = (request.form.get('nombre') or '').strip()
    ubicacion = (request.form.get('ubicacion') or '').strip()
    if not codigo or not nombre:
        flash('Codigo y nombre son obligatorios.', 'error')
        return redirect(url_for('terminal_admin_panel'))
    try:
        token = db.crear_terminal(codigo, nombre, ubicacion)
    except Exception as e:
        flash(f'No se pudo crear terminal: {e}', 'error')
        return redirect(url_for('terminal_admin_panel'))
    db.registrar_evento_critico(_actor_name(), 'crear_terminal', f'codigo={codigo}, nombre={nombre}, ubicacion={ubicacion}', request.remote_addr)
    flash(f'Terminal creada. Token: {token}', 'success')
    return redirect(url_for('terminal_admin_panel'))


@app.route('/votaciones/terminal-admin/terminales/actualizar/<int:terminal_id>', methods=['POST'])
@terminal_admin_required
def terminal_admin_actualizar_terminal(terminal_id):
    nombre = (request.form.get('nombre') or '').strip()
    ubicacion = (request.form.get('ubicacion') or '').strip()
    activa = request.form.get('activa') == '1'
    if not nombre:
        flash('El nombre es obligatorio.', 'error')
        return redirect(url_for('terminal_admin_panel'))
    db.actualizar_terminal(terminal_id, nombre, ubicacion, activa)
    db.registrar_evento_critico(_actor_name(), 'actualizar_terminal', f'id={terminal_id}, activa={activa}, nombre={nombre}', request.remote_addr)
    flash('Terminal actualizada.', 'success')
    return redirect(url_for('terminal_admin_panel'))


@app.route('/votaciones/terminal-admin/terminales/rotar-token/<int:terminal_id>', methods=['POST'])
@terminal_admin_required
def terminal_admin_rotar_token_terminal(terminal_id):
    token = db.rotar_token_terminal(terminal_id)
    db.registrar_evento_critico(_actor_name(), 'rotar_token_terminal', f'id={terminal_id}', request.remote_addr)
    flash(f'Nuevo token generado: {token}', 'success')
    return redirect(url_for('terminal_admin_panel'))


@app.route('/votaciones/terminal-admin/terminales/eliminar/<int:terminal_id>', methods=['POST'])
@terminal_admin_required
def terminal_admin_eliminar_terminal(terminal_id):
    db.eliminar_terminal(terminal_id)
    db.registrar_evento_critico(_actor_name(), 'eliminar_terminal', f'id={terminal_id}', request.remote_addr)
    flash('Terminal eliminada.', 'success')
    return redirect(url_for('terminal_admin_panel'))


@app.route('/votaciones/abstencionistas')
@admin_required
def abstencionistas():
    data = db.obtener_abstencionistas()
    return render_template('abstencionistas.html', abstencionistas=data, total=len(data))


@app.route('/votaciones/abstencionistas/exportar')
@admin_required
def exportar_abstencionistas():
    data = db.obtener_abstencionistas()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['ID', 'Nombre', 'Apellido1', 'Apellido2', 'Cedula', 'Nivel'])
    for r in data:
        writer.writerow([r['id'], r['nombre'], r['apellido1'], r['apellido2'], r['cedula'], r['nivel']])

    mem = io.BytesIO()
    mem.write(output.getvalue().encode('utf-8-sig'))
    mem.seek(0)
    filename = f"abstencionistas_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"
    return send_file(mem, as_attachment=True, download_name=filename, mimetype='text/csv')


@app.route('/votaciones/usuarios', methods=['GET', 'POST'])
@admin_required
def usuarios():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = request.form.get('password') or ''
        role = (request.form.get('role') or 'admin').strip()
        active = request.form.get('active') == '1'
        if not username or not password:
            flash('Usuario y contrasena son obligatorios.', 'error')
            return redirect(url_for('usuarios'))
        try:
            db.create_system_user(username, password, role, active=active)
            db.registrar_evento_critico(_actor_name(), 'crear_usuario', f'username={username}, role={role}, active={active}', request.remote_addr)
            flash('Usuario creado.', 'success')
        except Exception as e:
            flash(f'No se pudo crear usuario: {e}', 'error')
        return redirect(url_for('usuarios'))
    users = db.list_system_users()
    return render_template('usuarios.html', users=users)


@app.route('/votaciones/usuarios/actualizar/<int:user_id>', methods=['POST'])
@admin_required
def actualizar_usuario(user_id):
    role = (request.form.get('role') or 'admin').strip()
    active = request.form.get('active') == '1'
    db.update_system_user(user_id, role, active)
    db.registrar_evento_critico(_actor_name(), 'actualizar_usuario', f'user_id={user_id}, role={role}, active={active}', request.remote_addr)
    flash('Usuario actualizado.', 'success')
    return redirect(url_for('usuarios'))


@app.route('/votaciones/usuarios/password/<int:user_id>', methods=['POST'])
@admin_required
def cambiar_password_usuario(user_id):
    new_password = request.form.get('new_password') or ''
    if len(new_password) < 8:
        flash('La contrasena debe tener al menos 8 caracteres.', 'error')
        return redirect(url_for('usuarios'))
    db.set_system_user_password(user_id, new_password)
    db.registrar_evento_critico(_actor_name(), 'cambiar_password_usuario', f'user_id={user_id}', request.remote_addr)
    flash('Contrasena actualizada.', 'success')
    return redirect(url_for('usuarios'))


@app.route('/votaciones/bitacora')
@admin_required
def bitacora_sistema():
    eventos = db.obtener_bitacora_critica(500)
    return render_template('bitacora.html', eventos=eventos)


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
