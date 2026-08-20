# Guía de despliegue en otra máquina (desde Git)

Esta guía sirve para clonar/actualizar el proyecto en otra máquina y dejarlo funcionando con:
- codigo mas reciente
- base de datos con data de ejemplo
- archivos de uploads de desarrollo

## 1) Obtener la ultima version del repo

Si es primera vez:

```bash
git clone https://github.com/vegabryan22/expotecnica.git
cd expotecnica
git checkout main
```

Si ya existe el repo local:

```bash
git checkout main
git pull origin main
```

## 2) Instalar dependencias

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 3) Crear base de datos base

Entrar a MySQL y ejecutar:

```sql
SOURCE sql/setup.sql;
```

## 4) Cargar la data del backup del repo

En MySQL, ejecutar:

```sql
USE exporegional;
SOURCE sql/backups/expotecnica_latest.sql;
```

## 5) Verificar datos esperados

```sql
SELECT COUNT(*) AS projects FROM projects;
SELECT COUNT(*) AS judges FROM judges;
```

Los valores dependen de la fecha del respaldo. No use cantidades históricas como criterio de éxito. Compare los conteos antes y después de importar y verifique además campañas, integrantes, asignaciones y evaluaciones.

```sql
SELECT COUNT(*) AS campaigns FROM campaigns;
SELECT COUNT(*) AS members FROM project_members;
SELECT COUNT(*) AS assignments FROM assignments;
SELECT COUNT(*) AS evaluations FROM evaluations;
```

## 6) Verificar uploads versionados

Estos archivos deben existir después del pull:
- `app/static/uploads/institution/*`
- `app/static/uploads/maintenance/*`
- `app/static/uploads/members/*`
- `app/static/uploads/projects/documents/*`
- `app/static/uploads/projects/logos/*`

## 7) Configurar conexion y ejecutar

Opcional (si no usas el default de `config.py`):

```bash
set DATABASE_URL=mysql+pymysql://exporegional_user:exporegional123@localhost/exporegional?charset=utf8mb4
```

Ejecutar app:

```bash
python run.py
```

## Nota

Si `mysql` no está en PATH, abre MySQL Command Line Client o MySQL Workbench y ejecuta los scripts SQL desde ahí.

Antes de usar esta guía en producción, configure `SECRET_KEY`, `DATABASE_URL`, SMTP y permisos de `app/static/uploads`. Ejecute también las pruebas y el verificador de codificación indicados en el README.
