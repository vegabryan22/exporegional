# Referencia funcional actual

## Propósito

Esta referencia describe el sistema vigente a agosto de 2026. Sirve para administración, QA, soporte y desarrollo.

## Flujo completo

1. Administración configura campaña, parámetros académicos, categorías y rúbricas.
2. Estudiantes y tutores registran proyectos durante una campaña activa.
3. Administración revisa integrantes, documento, fotografías, consentimientos, cédulas, logo y recursos.
4. Los jueces se registran, confirman asistencia e indican disponibilidad y capacidades.
5. Administración asigna cobertura documental, exposición e inglés.
6. Los jueces califican únicamente los proyectos y tipos autorizados.
7. El sistema acumula resultados, genera actas, reportes y certificados.
8. Los ganadores institucionales pueden enviarse a la plataforma regional.

## Navegación administrativa

### Inicio

- Panel de control con prioridades y accesos operativos.

### Preparación de la Expo

- Inscripción y calendario.
- Configuración académica.
- Categorías.
- Rúbricas de evaluación.

### Participantes

- Proyectos.
- Tutores.
- Gestión de jueces.
- Participación estudiantil y correcciones.

### Operación del evento

- Asignación de jueces.
- Recursos solicitados.
- Espacios y ubicaciones.
- Operación de edecanes.

### Resultados y cierre

- Avance y resultados.
- Reportes.
- Actas y certificados.
- Integración regional.

### Administración y sistema avanzado

- Usuarios, permisos, institución, correo, dependencias, base de datos, GitOps, mantenimiento y bitácora.

## Reglas de negocio relevantes

- Solo los proyectos activos aparecen en los flujos públicos y operativos aplicables.
- Una campaña activa controla la disponibilidad de la inscripción.
- Cada proyecto admite de uno a tres integrantes.
- La logística y los requerimientos técnicos son estados distintos.
- El estado logístico se deriva de evidencias; no debe editarse manualmente como texto libre.
- Activar o desactivar un proyecto es una acción independiente del guardado logístico.
- Las asignaciones determinan qué juez puede evaluar documentación, exposición o inglés.
- Las rúbricas conservan valor numérico aunque la interfaz muestre escalas textuales.
- Los ganadores dependen de evaluaciones completas y reglas de resultados.
- Los recordatorios de WhatsApp normal abren conversaciones individuales; no existe envío masivo automático sin Business API.
- Los cambios sensibles deben dejar registro en la bitácora.

## Entidades principales

| Área | Entidades |
| --- | --- |
| Acceso | `Judge`, `SystemSetting`, `SystemAuditLog` |
| Inscripción | `Campaign`, `Category`, `Level`, `Section`, `Specialty`, `Workshop`, `ThematicAxis`, `ProjectType` |
| Proyectos | `Project`, `ProjectMember`, `Tutor`, `ProjectMemberChange`, `ProjectMemberEditRequest`, `ProjectDocumentRevision` |
| Evaluación | `Assignment`, `EvaluationType`, `RubricCriterion`, `Evaluation`, `EvaluationScore` |
| Evento | `Venue` |
| Regional | `RegionalSubmission` |

## Servicios

- `assignment_service.py`: asignaciones y cobertura.
- `evaluation_service.py`: cálculo y reglas de evaluación.
- `exposition_capacity_service.py`: planificación presencial.
- `mail_service.py`: SMTP, invitaciones y recordatorios.
- `audit_service.py`: trazabilidad de acciones.
- `institutional_matrix_service.py`: matriz institucional Excel.
- `regional_integration_service.py`: contrato y transferencia regional.
- `parameter_service.py` y `specialty_service.py`: catálogos y normalización.
- `identity_lookup_service.py`: apoyo para datos de identidad.

## Reportes y salidas

- Excel de proyectos y matriz institucional.
- Reportes de jueces, tutores, asignaciones, asistencia y edecanes.
- Pendientes logísticos y de evaluación.
- Evaluaciones por juez, proyecto y consolidado.
- Acta general, acta oficial de ganadores y certificados.
- Mapa institucional PDF y paquetes documentales por proyecto.

## Integraciones

### Correo

SMTP configurable, con modo guiado para Gmail/Google Workspace. Las credenciales no deben exponerse en vistas ni logs.

### WhatsApp normal

Genera enlaces individuales con mensajes preparados. El usuario debe revisar y pulsar Enviar en WhatsApp.

### Plataforma regional

API independiente con autenticación Bearer, identificadores estables, reintentos y transferencia de archivos. Consulte `docs/INTEGRACION_REGIONAL.md`.

## Operación y soporte

- Desde **Avance y resultados**, el botón **Quién falta Expo** descarga el control de exposiciones pendientes con juez, proyecto, contacto, participación, estado de la asignación y observaciones para seguimiento.
- El módulo **Actualización y salud del sistema** organiza el despliegue en tres pasos: buscar actualizaciones, aplicarlas y ejecutar el diagnóstico.
- El estado se considera operativo solo cuando están disponibles el proceso WSGI, la aplicación ExpoTécnica y la base de datos; también se muestran versión y tiempo de respuesta.
- El endpoint público `GET /health` devuelve JSON mínimo para monitoreo y no depende de formularios funcionales como el registro de jueces.
- La recarga y el reinicio están diferenciados visualmente. La reversión a una versión anterior se mantiene en una sección de recuperación de emergencia con confirmación explícita.
- Use el centro de reportes como punto principal de descarga.
- Revise la bitácora antes de corregir datos directamente en MySQL.
- Genere respaldo antes de restauraciones, limpiezas o parches manuales.
- No mezcle cambios institucionales y regionales sin confirmar el entorno.
- Verifique `VERSION`, pruebas y codificación antes de publicar.

## Verificación mínima antes de producción

```powershell
python -m pytest -q
python scripts/check_text_encoding.py
git status --short
git diff --check
```

Además, valide manualmente inscripción, login, asignación, evaluación, reportes críticos, acta de ganadores y permisos por rol.
