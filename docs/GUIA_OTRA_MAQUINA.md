# Guia de despliegue en otra maquina (desde Git)

Esta guia sirve para clonar/actualizar el proyecto en otra maquina y dejarlo funcionando con:
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
USE expotecnica_db;
SOURCE sql/backups/expotecnica_latest.sql;
```

## 5) Verificar datos esperados

```sql
SELECT COUNT(*) AS projects FROM projects;
SELECT COUNT(*) AS judges FROM judges;
```

Valores esperados para este backup:
- `projects = 68`
- `judges = 26`

## 6) Verificar uploads versionados

Estos archivos deben existir despues del pull:
- `app/static/uploads/institution/*`
- `app/static/uploads/maintenance/*`
- `app/static/uploads/members/*`
- `app/static/uploads/projects/documents/*`
- `app/static/uploads/projects/logos/*`

## 7) Configurar conexion y ejecutar

Opcional (si no usas el default de `config.py`):

```bash
set DATABASE_URL=mysql+pymysql://expotecnica_user:expotecnica123@localhost/expotecnica_db?charset=utf8mb4
```

Ejecutar app:

```bash
python run.py
```

## Nota

Si `mysql` no esta en PATH, abre MySQL Command Line Client o MySQL Workbench y ejecuta los scripts SQL desde ahi.
