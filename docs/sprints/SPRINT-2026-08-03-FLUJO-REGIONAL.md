# Sprint — flujo manual regional

## Objetivo

Permitir que un colegio sin plataforma institucional registre sus ganadores, los envíe y reciba una decisión de la coordinación regional sin acceder a información de otros centros.

## Componentes

- `regional_project_service.py`: máquina de estados y autorización por actor.
- `school_controller.py`: panel, formulario, archivos y envío del colegio.
- `school_routes.py`: rutas bajo `/colegio`.
- `school/*`: vistas del portal coordinador.
- `regional_review.html`: bandeja regional.
- Administración de cuentas coordinadoras desde `/admin/colegios`.

## Controles

- Consulta de proyectos filtrada siempre por `current_user.institution_id`.
- Verificación de propiedad antes de editar o enviar.
- Edición limitada a borradores y proyectos devueltos.
- Documento PDF obligatorio antes del envío.
- Observación obligatoria al devolver.
- Historial inmutable por transición.

## Verificación

- Compilación Python satisfactoria.
- 49 pruebas aprobadas.
- Pruebas explícitas de proyecto propio y proyecto ajeno.
- Pruebas de secuencia administrativa hasta aprobación.
