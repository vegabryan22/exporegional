# ExpoTécnica (Flask + MySQL, MVC)

App web para feria científica con:
- inscripción de proyectos (`STEAM` y `Emprendimiento`)
- login de jueces y admin
- evaluación por rúbrica
- panel admin para asignaciones, mantenimiento y reportes

## 1) Requisitos
- Python 3.11+
- MySQL Server

## 2) Crear base de datos y usuario en MySQL
Con root local:

```sql
SOURCE sql/setup.sql;
```

O manual:

```sql
CREATE DATABASE IF NOT EXISTS expotecnica_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER IF NOT EXISTS 'expotecnica_user'@'localhost' IDENTIFIED BY 'expotecnica123';
GRANT ALL PRIVILEGES ON expotecnica_db.* TO 'expotecnica_user'@'localhost';
FLUSH PRIVILEGES;
```

## 3) Instalar dependencias

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

`requirements.txt` incluye `reportlab` para generación de PDF.

## 4) Configuración
Por defecto:

```text
mysql+pymysql://root:123456@localhost/expotecnica_db?charset=utf8mb4
```

Opcional:

```text
set DATABASE_URL=mysql+pymysql://expotecnica_user:expotecnica123@localhost/expotecnica_db?charset=utf8mb4
```

## 5) Ejecutar

```bash
python run.py
```

## 6) Hooks automáticos (respaldo + sync de paquetes)

Este repo incluye hooks en `.githooks` para:
- `pre-commit`: respaldo SQL automático
- `post-merge`: si cambia `requirements.txt`, ejecuta `python -m pip install -r requirements.txt`
- `post-checkout`: lo mismo cuando cambias de rama y cambian dependencias

Actívalos una vez por clon:

```bash
git config core.hooksPath .githooks
```

Nota para Windows: estos hooks usan `sh`, `grep` y utilidades tipo POSIX. Funcionan bien con Git for Windows usando Git Bash. Si tu entorno no tiene ese soporte, ejecuta manualmente `python -m pip install -r requirements.txt` cuando cambie `requirements.txt`.

## 7) Comandos útiles

Crear juez:

```bash
flask --app run.py create-judge
```

Crear admin:

```bash
flask --app run.py create-admin
```

Asignar proyecto:

```bash
flask --app run.py assign-project
```

## Arquitectura MVC
- Modelo: `app/models/*`
- Controlador: `app/controllers/*`
- Vista: `app/templates/*`
- Rutas: `app/routes/*`

## Versionamiento
- Versión actual: `VERSION`
- Historial: `CHANGELOG.md`
- Evidencia por sprint: `docs/sprints/`
