# Flujo de trabajo con GitHub

El repositorio ya está inicializado y utiliza `main`. Esta guía evita repetir la configuración histórica de un repositorio nuevo.

## Preparar una computadora nueva

```powershell
git clone https://github.com/vegabryan22/expotecnica.git
cd expotecnica
git checkout main
git config core.hooksPath .githooks
```

Continúe con la instalación descrita en `README.md` y `docs/GUIA_OTRA_MAQUINA.md`.

## Revisar antes de guardar cambios

```powershell
git status --short
git diff --check
python -m pytest -q
python scripts/check_text_encoding.py
```

Revise que no se incluyan respaldos privados, archivos `.env`, credenciales, resultados temporales ni uploads ajenos al cambio.

## Publicar directamente en main

Si el equipo decidió trabajar directamente en `main`:

```powershell
git checkout main
git pull --ff-only origin main
git add <archivos revisados>
git commit -m "tipo: descripción clara"
git push origin main
```

Use `git add` con rutas concretas; evite agregar automáticamente archivos no revisados.

## Mensajes recomendados

- `feat: agregar nueva capacidad`
- `fix: corregir comportamiento`
- `style: mejorar presentación sin cambiar lógica`
- `docs: actualizar documentación`
- `refactor: reorganizar código sin cambiar el resultado`
- `test: ampliar cobertura`
- `chore: mantenimiento técnico`

## Actualizar una instalación existente

```powershell
git status --short
git pull --ff-only origin main
python -m pip install -r requirements.txt
```

Antes del pull, conserve o respalde cambios locales. Nunca use `git reset --hard` para resolverlos sin verificar qué se perderá.

## Respaldos y base de datos

El hook `pre-commit` puede generar un respaldo SQL si `.githooks` está activo. Confirme que el respaldo no contiene datos que deban permanecer fuera de Git. Los cambios de esquema o parches de datos deben documentarse expresamente en el commit y en `CHANGELOG.md`.

## Versiones

Antes de etiquetar una versión:

1. Actualice `VERSION`.
2. Mueva los cambios desde “Sin publicar” en `CHANGELOG.md` a una versión fechada.
3. Actualice README y documentos relacionados.
4. Ejecute pruebas y verificación UTF-8.
5. Cree y publique el tag solo después de subir el commit.
