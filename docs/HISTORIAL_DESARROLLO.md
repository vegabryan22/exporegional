# Historial de desarrollo de ExpoTécnica

## Alcance

Este documento resume los 456 commits existentes entre el 10 de marzo y el 19 de agosto de 2026. No sustituye `git log`: organiza el historial en etapas funcionales para explicar cómo llegó el sistema a su estado actual.

| Periodo | Commits | Enfoque dominante |
| --- | ---: | --- |
| Marzo de 2026 | 13 | Fundación, MVC, inscripción, evaluación y administración modular. |
| Mayo de 2026 | 11 | Recuperación del proyecto, experiencia móvil y GitOps. |
| Junio de 2026 | 154 | Expansión operativa: jueces, logística, respaldos, mantenimiento y documentos. |
| Julio de 2026 | 200 | Consolidación de flujos, UX, reportes, correo, tutores, integrantes y calidad. |
| Agosto de 2026 | 78 | Operación de feria, recintos, regional, reconfirmación, WhatsApp, identidad y documentos oficiales. |

## Etapa 1 — Fundación y primeras versiones (marzo)

- Se creó la aplicación Flask con arquitectura MVC, autenticación, proyectos, jueces, evaluaciones y panel administrativo.
- Se incorporaron categorías STEAM y Emprendimiento, fotos de integrantes y portada pública de proyectos.
- Se parametrizaron campañas, categorías, niveles, secciones, especialidades, talleres, tipos de proyecto y rúbricas.
- El formulario público evolucionó al formato ExpoTEC-1.
- Se modularizó el panel y se separaron flujos públicos, de jueces y administrativos.
- Se añadieron roles, departamentos y matriz de permisos.
- Se incorporaron actas PDF, mejoras móviles, reportes, datos demostrativos y documentación de QA.
- Se establecieron respaldos automáticos previos al commit y sincronización de dependencias mediante hooks.

Versiones representativas: `v0.1.0` a `v0.8.0`.

## Etapa 2 — Recuperación, despliegue y GitOps (mayo)

- Se versionaron recursos cargados necesarios para ambientes de desarrollo.
- Se creó la guía de despliegue en otra máquina y el flujo de restauración desde respaldo.
- Se refinó la portada interna y la experiencia móvil.
- Se eliminaron artefactos ajenos al dominio ExpoTécnica.
- Se creó el módulo GitOps administrativo para inspeccionar cambios, sincronizar repositorio y controlar el servicio.
- Se hicieron explícitas las operaciones de Git y se mejoró la presentación de archivos locales.

## Etapa 3 — Expansión operativa (junio)

### Jueces y acceso

- Registro público de jueces, alias de acceso y contenido institucional.
- Administración de perfiles, disponibilidad, capacidades de evaluación y credenciales.
- Mejoras de autenticación, roles y protección de accesos administrativos.

### Proyectos e inscripción

- Ajuste del registro a especialidades técnicas.
- Validación de documentos de identidad y normalización de datos.
- Paquete imprimible de documentos por proyecto con logos institucionales.
- Gestión ampliada de integrantes, fotografías y documentos.

### Logística y mantenimiento

- Revisión de requisitos firmados, consentimientos y evidencias.
- Acceso logístico desde el panel.
- Limpieza anual con reglas de conservación.
- Respaldos y restauración con trazabilidad visual.
- Bitácora, configuración, dependencias y herramientas de diagnóstico.

### Evaluación y resultados

- Ajustes al flujo de evaluación, rúbricas, asignaciones y reportes.
- Mejoras en actas, PDFs, certificados y visualización de resultados.

## Etapa 4 — Consolidación funcional y de experiencia (julio)

Julio concentra 200 commits y la mayor parte de la estabilización del producto.

### Integrantes y correcciones

- Solicitud pública de correcciones con motivo obligatorio.
- Búsqueda directa, aprobación o rechazo administrativo y notificaciones.
- Historial de cambios por integrante.
- Rediseño de fichas, editor de fotografías y modales anidados.
- Consentimientos individuales y control de cédulas de encargado y estudiante.

### Estadísticas y paneles

- Estadísticas de estudiantes con gráficas por sección, especialidad, género y tutor.
- Ajustes de etiquetas, leyendas, tamaños y comportamiento adaptable.
- Resúmenes operativos para asignaciones, logística y tutores.

### Jueces, asistencia y asignaciones

- Confirmación de asistencia, parqueo y estados de participación.
- Distinción de jueces de inglés.
- Asignación rápida, masiva, automática y análisis de carga.
- Planificación de cupos presenciales y reportes para operación.

### Correo y recordatorios

- Configuración SMTP guiada para Gmail y Google Workspace.
- Contraseñas de aplicación y mensajes de error seguros.
- Recordatorios individuales y masivos por lotes.
- Consolidación de pendientes por tutor para evitar correos duplicados.
- Correcciones a endpoints JSON, redirecciones y persistencia de resultados.

### Proyectos, logística y requerimientos

- Separación entre expediente logístico y recursos técnicos.
- Estado efectivo calculado a partir de evidencias reales.
- Requerimientos con guardado automático, búsqueda y filtros.
- Recordatorios por pendientes documentales y envío de logos.
- Mejoras continuas de diseño adaptable y navegación dentro de modales.

### Reportes y documentos

- Centro único de reportes administrativos.
- Exportaciones de jueces, tutores, proyectos, asignaciones, edecanes y evaluaciones.
- Actas, certificados, paquetes documentales y matrices Excel.

Versiones representativas: `v0.9.0` a `v0.25.3` y series intermedias documentadas en `CHANGELOG.md`.

## Etapa 5 — Preparación institucional y regional (agosto)

### Integración regional

- Configuración de API regional y envío de ganadores.
- Identificador externo estable, reintentos idempotentes y consulta de estado.
- Transferencia de documentos, logos y fotografías individuales.
- Bases institucional y regional independientes, comunicadas por Bearer API.

### Recintos y operación del evento

- Catálogo de recintos y relación con proyectos.
- Mapa institucional interactivo con posiciones persistentes.
- Evolución desde prototipos y fotografías hasta plano digital 2026.
- PDF nativo de una página para mapa y directorio.
- Reportes de edecanes con proyectos, integrantes y ubicación.

### Reconfirmación y comunicaciones

- Segunda confirmación para jueces de exposición.
- Avance de reconfirmación en panel.
- Corrección de reasignaciones manuales mediante parche y reconciliación de arranque.
- Recordatorios por WhatsApp normal, registro de enviados y modal continuo.
- Endpoint JSON robusto y dirección mediante Waze.

### Evaluación y documentación oficial

- Rúbrica de inglés alineada con el Excel oficial.
- Descripciones editables por criterio y escala textual en encabezado.
- Revisión de rubros de exposición.
- Acta de ganadores con formato oficial, número de acta e institución corregidos.
- Fecha de nacimiento incluida junto a la cédula en la matriz institucional.

### Identidad y administración

- Integración visual de la identidad Costa Rica 205 con ExpoTécnica.
- Protección de roles operativos frente al formulario público de jueces.
- Reorganización progresiva del panel, navegación, dashboard, tablas, acciones y modales.

## Cambios locales posteriores al último commit

Al momento de actualizar este documento existen cambios locales no publicados:

- Reorganización del menú administrativo por flujo de trabajo.
- Dashboard orientado a prioridades, preparación, asistencia, logística y evaluaciones pendientes.
- Consolidación adicional del centro de reportes.
- Sistema visual de botones con iconos, colores semánticos y acciones principales descriptivas.
- Rediseño de campañas, configuración académica y tarjetas de proyectos.
- Estandarización gradual de tablas y modales.
- Mejoras al expediente logístico, carga de archivos y documentos.
- Activación o desactivación de proyectos desde la tarjeta mediante una operación asíncrona.

Estos cambios no están incluidos en los 456 commits y no deben considerarse publicados hasta crear el commit correspondiente.

## Cómo consultar el detalle exacto

```powershell
git log --oneline --decorate --all
git log --date=short --pretty=format:'%h %ad %s'
git show <hash>
git log -- app/templates/admin/projects.html
git log -- app/controllers/admin_controller.py
```

`CHANGELOG.md` ofrece el detalle por versiones; los documentos de `docs/sprints/` conservan evidencia de trabajo por sprint.
