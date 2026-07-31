# Changelog

## [0.23.0] - 2026-07-31

### Añadido

- El editor de integrantes permite eliminar la fotografía actual mediante una acción independiente con confirmación.
- La eliminación borra el archivo local, limpia la referencia, registra la bitácora y recalcula el control fotográfico del proyecto.

### Cambiado

- El formulario de edición presenta un encabezado identificable, campos compactos, bloques visuales uniformes y un editor de fotografía separado.
- La fotografía utiliza una vista previa amplia, selector de archivo estilizado y acciones claras para reemplazar o eliminar.
- El diálogo se adapta a escritorio y móvil, con acciones de guardado visibles al desplazarse.

## [0.22.2] - 2026-07-31

### Corregido

- El envío masivo obtiene la URL desde el atributo HTML del formulario y evita la colisión entre `form.action` y el campo oculto llamado `action`.
- Los lotes ya no intentan acceder a una ruta inexistente antes de iniciar, eliminando el error 404 con cero lotes procesados.

## [0.22.1] - 2026-07-31

### Corregido

- Los lotes de recordatorios responden directamente con JSON y ya no siguen una redirección administrativa que podía terminar en un error 404.
- El navegador valida la respuesta de cada lote antes de avanzar y conserva los mensajes finales para la recarga de la página.

## [0.22.0] - 2026-07-31

### Cambiado

- Cada tutor recibe un único correo consolidado con todos sus proyectos pendientes, ordenados alfabéticamente.
- Cada proyecto del resumen separa requisitos generales, pendientes individuales por estudiante e instrucciones para enviar el logo cuando corresponda.
- El envío masivo conserva lotes individuales para estudiantes, pero agrupa los proyectos por correo de tutor para evitar mensajes duplicados.
- El envío puntual al tutor también incorpora todos sus proyectos activos con pendientes.
- Las métricas del centro cuentan tutores únicos en lugar de contar un tutor una vez por proyecto.

## [0.21.1] - 2026-07-31

### Corregido

- El indicador TLS muestra correctamente «Sí» en lugar de una entidad HTML visible.
- Usuario y remitente ocupan filas más amplias para evitar cortes innecesarios en direcciones de correo largas.
- El resumen SMTP conserva una cuadrícula adaptable en escritorio, tableta y móvil.

## [0.21.0] - 2026-07-31

### Añadido

- Configuración guiada para enviar notificaciones mediante una cuenta Gmail o Google Workspace.
- El modo Gmail establece automáticamente `smtp.gmail.com`, puerto `587`, TLS y el remitente de la cuenta.
- La pantalla enlaza la creación de contraseñas de aplicación y conserva el envío de prueba.

### Seguridad

- Gmail exige cuenta completa y contraseña de aplicación antes de considerarse configurado.
- La contraseña guardada nunca se devuelve al navegador y puede conservarse dejando el campo vacío.
- Los rechazos de autenticación de Google muestran una explicación específica sin revelar credenciales.

## [0.20.2] - 2026-07-31

### Corregido

- Proyectos muestra un acceso visible al Centro de recordatorios directamente en su encabezado.
- El acceso se adapta a pantallas estrechas y conserva junto a él el total de proyectos.

## [0.20.1] - 2026-07-31

### Añadido

- El centro de recordatorios permite configurar el correo institucional destinado a recibir los logos de los proyectos.
- Los correos para estudiantes y tutores incluyen un enlace directo a esa dirección cuando el proyecto todavía no ha cargado su logo.

### Corregido

- Un logo ya cargado pero pendiente de validación continúa apareciendo como requisito logístico, pero el recordatorio no solicita enviarlo nuevamente.

## [0.20.0] - 2026-07-31

### Cambiado

- El porcentaje logístico de cada tutor mide el avance real acumulado de las evidencias de sus proyectos activos.
- Se consideran siete controles: documento adjunto, documento validado, logo cargado, logo validado, fotografías, formulario firmado y consentimientos.
- La etiqueta de pendientes cuenta proyectos únicos y evita sumar dos veces un mismo proyecto por logística y requerimientos.

## [0.19.10] - 2026-07-31

### Corregido

- Las métricas de cada tutor utilizan bloques rectangulares compactos y uniformes en lugar de círculos desproporcionados.
- Las acciones de edición y disponibilidad tienen el mismo ancho y altura, sin espacios vacíos excesivos.

## [0.19.9] - 2026-07-31

### Corregido

- Los nombres y especialidades del selector de tutores se muestran con capitalización natural.
- Conectores como «de», «del», «a» y «y» permanecen en minúscula sin alterar los datos almacenados.

## [0.19.8] - 2026-07-31

### Corregido

- Las inscripciones simultáneas con la misma cédula de tutor utilizan una operación atómica de MySQL.
- Si otra solicitud crea primero el perfil, las demás recuperan ese mismo tutor y continúan guardando sus proyectos sin duplicados ni errores de clave única.

## [0.19.7] - 2026-07-31

### Corregido

- La descarga Excel de Tutores ahora es un botón compacto con icono de tamaño controlado y no deforma el encabezado.

## [0.19.6] - 2026-07-31

### Corregido

- La cuadrícula de una columna de la declaración ya no es sobrescrita por la regla general de tres columnas de los paneles de registro.

## [0.19.5] - 2026-07-31

### Corregido

- La aceptación de la declaración ocupa correctamente todo el ancho disponible sin comprimir el texto.
- Los estilos estáticos utilizan la versión de la aplicación como identificador de caché, evitando que el navegador conserve diseños anteriores después de una actualización.

## [0.19.4] - 2026-07-31

### Corregido

- Se restauró la distribución original de los contenedores de tutoría y cierre de inscripción.
- Se conserva únicamente el ajuste solicitado para la aceptación visual de la declaración.

## [0.19.3] - 2026-07-31

### Corregido

- El cierre de inscripción utiliza dos áreas paralelas para mentoría y declaración en computadora y tableta.
- Los bloques de tutoría y cierre aprovechan el ancho completo; la disposición de una columna queda reservada para celulares.

## [0.19.2] - 2026-07-31

### Corregido

- La aceptación final ahora utiliza una franja horizontal proporcionada, con casilla visible, jerarquía tipográfica clara y adaptación móvil.

## [0.19.1] - 2026-07-31

### Corregido

- Los datos de la persona mentora solo aparecen y se exigen cuando se confirma que el proyecto cuenta con mentoría.
- La declaración final se presenta como una aceptación obligatoria única; se eliminó la opción inviable «No acepto».

## [0.19.0] - 2026-07-31

### Añadido

- Catálogo persistente de tutores con relación directa entre cada perfil y sus proyectos.
- Migración automática y no destructiva de los datos de tutores existentes al catálogo central.
- Selector de tutor registrado en el formulario público y alternativa para registrar uno nuevo.
- Control administrativo para mostrar u ocultar tutores en nuevas inscripciones.

### Cambiado

- Los datos personales del tutor se guardan una sola vez y se reutilizan al inscribir otros proyectos.
- El formulario público muestra únicamente nombre y especialidad de los tutores disponibles; no expone cédula, nacimiento, teléfono ni correo.
- Los proyectos conservan una copia histórica de los datos del tutor para sus formularios y documentos oficiales.

## [0.18.0] - 2026-07-31

### Añadido

- Módulo administrativo de Tutores con información centralizada por cédula, correo o nombre.
- Estadísticas de proyectos, estudiantes, categorías, avance logístico y requerimientos pendientes por tutor.
- Filtros por texto y estado, detalle desplegable de proyectos y acceso directo a cada inscripción.
- Reporte Excel consolidado de tutores y proyectos asociados.
- Edición conjunta y unificación explícita de registros duplicados.

### Cambiado

- La tabla de tutores dejó de estar incrustada en Proyectos; fue sustituida por un enlace compacto al módulo especializado.
- Los permisos existentes con acceso a Proyectos incorporan automáticamente el acceso a Tutores.

## [0.17.2] - 2026-07-31

### Corregido

- La validación de fotografías se activa automáticamente cuando todos los integrantes del proyecto tienen foto.
- Los proyectos existentes se reconcilian al iniciar la aplicación para eliminar pendientes manuales desactualizados.
- Al agregar, actualizar o eliminar integrantes se recalculan inmediatamente las fotografías y el estado logístico.
- La casilla de fotografías se presenta como un indicador automático y ya no como un control manual.

## [0.17.1] - 2026-07-31

### Corregido

- El acceso al reporte Excel de proyectos ahora usa una barra compacta y un icono de tamaño controlado.
- Se eliminó el botón desproporcionado que ocupaba gran parte de la página de Proyectos.

## [0.17.0] - 2026-07-31

### Añadido

- Reporte Excel general de proyectos inscritos disponible desde Administración → Proyectos.
- Hoja de proyectos con datos académicos, responsables, fechas, estados y requerimientos.
- Hoja de integrantes con sección, especialidad, contacto y controles documentales relevantes.

### Cambiado

- Los nombres de representantes, tutores, mentores e integrantes se exportan con capitalización natural sin modificar la base de datos.
- La página de proyectos incorpora un acceso visible y adaptable para descargar el reporte.

## [0.16.0] - 2026-07-30

### Añadido

- Desglose estructurado de insumos por proyecto con nombre, cantidad, unidad y observación.
- Confirmación administrativa independiente para cada insumo o material solicitado.
- Editor dinámico de insumos en el formulario de inscripción y en el módulo de requerimientos.

### Cambiado

- Las tarjetas de requerimientos muestran el detalle completo y el estado de cada insumo.
- Los textos históricos de insumos se conservan como elementos pendientes de desglosar.
- Los pendientes identifican ahora los insumos concretos que aún no han sido confirmados.

## [0.15.0] - 2026-07-30

### Añadido

- Reporte Excel editable para que los edecanes ubiquen a los jueces en sus proyectos de exposición.
- Columnas operativas para registrar recinto o ubicación y el estado de atención durante el evento.
- Filtros, encabezado fijo, lista de estados y formato visual para facilitar el trabajo en campo.

### Cambiado

- La descarga principal para edecanes ahora es Excel en lugar de PDF.
- El reporte continúa excluyendo evaluaciones exclusivas de documentación y no presupone recintos.

## [0.14.0] - 2026-07-30
### Added
- Reporte PDF operativo para edecanes con jueces y proyectos asignados a evaluación de exposición.
- Columnas en blanco para que los edecanes registren recinto, ubicación y atención durante el evento.
- Acceso directo al reporte desde Asignaciones de jueces.

### Changed
- El reporte excluye borradores, proyectos inactivos, jueces que no asistirán y asignaciones exclusivas de documentación.

## [0.13.1] - 2026-07-30
### Added
- Barra de progreso para envíos masivos de recordatorios.
- Mensaje de finalización o interrupción con cantidad de lotes procesados.

### Changed
- Los recordatorios masivos se procesan proyecto por proyecto mediante peticiones secuenciales.

### Fixed
- Se evita el error `504 Gateway Time-out` al enviar decenas de correos en una sola petición.

## [0.13.0] - 2026-07-30
### Added
- Centro de recordatorios logísticos con envíos a estudiantes, tutores o ambas audiencias.
- Envíos puntuales por proyecto y envío masivo configurable.
- Resumen de estudiantes y tutores con correo, además de destinatarios omitidos.
- Vista previa diferenciada del correo para estudiantes y para tutores.

### Changed
- Rediseño responsive de la pantalla de recordatorios con centro de mando, tarjetas de proyecto y acciones claras.
- La auditoría registra audiencia y proyectos incluidos en cada envío.

### Fixed
- Corrección de la plantilla de correo para tutores al mostrar pendientes individuales.

## [0.12.1] - 2026-07-30
### Fixed
- Se eliminó la definición duplicada de filtro automático en los reportes de pendientes.
- Excel ya no necesita reparar ni eliminar la tabla al abrir los archivos generados.

## [0.12.0] - 2026-07-30
### Added
- Reporte Excel descargable de pendientes logísticos con tipo de pendiente, persona afectada, sección, proyecto y tutor.
- Reportes específicos para fotografías, logos, documentos, logística incompleta, documentos en revisión y ediciones de datos.
- Descarga consolidada de todos los pendientes desde el resumen del panel.

### Changed
- Los contadores de pendientes de Logística ahora funcionan como accesos directos a su reporte detallado.

## [0.11.0] - 2026-07-30
### Added
- Resumen estadístico en Proyectos con activos, completados, pendientes, inactivos y porcentaje de avance.
- Desglose expandible de documentos y evidencias faltantes en cada proyecto.

### Changed
- Los indicadores y pendientes utilizan el mismo cálculo de cumplimiento logístico para evitar cifras contradictorias.
- Las nuevas métricas se adaptan a cuatro, dos o una columna según el tamaño del dispositivo.

## [0.10.0] - 2026-07-30
### Added
- Filtro por tutor en el mantenimiento de proyectos, con cantidad de proyectos por cada opción.
- Combinación del tutor con búsqueda, categoría, estado logístico y estado activo/inactivo.

### Changed
- Distribución adaptable de la barra de filtros para incorporar el tutor sin afectar la vista móvil.

## [0.9.2] - 2026-07-30
### Added
- Reconciliación automática de estados logísticos para proyectos registrados antes de `v0.9.1`.

### Fixed
- Los proyectos existentes que ya tienen documentos, logo, fotografías, formulario y consentimientos aprobados pasan a `Completo` al iniciar la aplicación.
- Los proyectos guardados como completos que vuelvan a tener un pendiente se corrigen a `Incompleto`.

## [0.9.1] - 2026-07-30
### Changed
- El estado logístico ahora se calcula automáticamente al guardar el control del proyecto.
- Se reemplazó el selector manual por un indicador que evita estados contradictorios.

### Fixed
- Un proyecto con todos los controles logísticos aprobados ya no permanece en estado `Revisión`.
- Al aparecer un pendiente, el proyecto vuelve automáticamente a estado `Incompleto`.

## [0.9.0] - 2026-07-30
### Added
- Módulo administrativo independiente de Requerimientos para gestionar electricidad, tomacorrientes, internet, agua, otros insumos y recursos detallados por proyecto.
- Estado, comprobaciones individuales y notas de seguimiento para los requerimientos técnicos.
- Permiso específico para asignar el nuevo módulo al departamento responsable sin incorporarlo automáticamente a Logística.
- Pruebas automatizadas que verifican la separación entre el cierre logístico y la atención de recursos.

### Changed
- Logística se concentra en la asignación de jueces, documentación, formularios, fotografías e integrantes.
- El cumplimiento logístico ya no depende de la disponibilidad o validación de insumos técnicos.
- Los recordatorios logísticos al tutor se limitan a pendientes documentales.

## [0.8.0] - 2026-03-20
### Added
- Actas de evaluación en PDF por proyecto y consolidado general, con vista previa HTML y opción de descarga/visualización directa.
- Nuevas rutas admin para reportes de actas y botones de acceso rápido desde el módulo de evaluaciones.
- Menú hamburguesa en móvil para navegación superior.

### Changed
- UI del panel de juez: acciones de evaluación más claras, botones compactos y mejor adaptación responsive en móvil.
- Textos visibles en vistas normalizados con acentos y caracteres en español.
- Selector de estado de campaña simplificado (activa/inactiva) para evitar confusiones del checkbox.

### Fixed
- Alineación del botón `Cerrar sesión` en la barra superior.
- Correcciones de codificación y labels mal renderizados en mantenimiento académico y menú lateral admin.
- Consistencia de etiquetas cortas de tipos de evaluación para evitar textos largos en celdas.

## [0.7.0] - 2026-03-17
### Added
- Logo propio de ExpoTecnica separado del logo institucional y reutilizado en home, formulario y login.
- Placeholders visuales para estudiantes sin foto y logo genérico para proyectos sin logo real.
- Centro de operaciones en el panel admin con indicadores de logística, jueces y evaluaciones pendientes.
- Documentación funcional para QA: arquitectura de módulos y modelo de pruebas con resultados esperados.

### Changed
- Reorganización operativa del módulo de asignaciones con mantenimiento rápido por proyecto y modales de gestión.
- Panel de permisos por departamento rediseñado a tarjetas con interruptores por módulo.
- Mantenimientos de rúbricas, proyectos, campañas, evaluaciones y usuarios con mejoras de lectura y consistencia visual.
- Branding y paleta del sitio alineados a ExpoTecnica, incluyendo login y cabeceras públicas.
- Tipos de evaluación con nombre corto y descripción larga para usar textos entendibles en UI.

### Fixed
- Validación de categorías para obligar una rúbrica de Exposición y una de Documentación.
- Identificación correcta de rúbricas de Exposición y Documentación en cálculo y dashboard de evaluaciones.
- Reglas de usuarios: jueces sin departamento y un solo usuario genérico por departamento.
- Contadores y reportes restringidos a proyectos activos cuando corresponde.
- Tipos de evaluación eliminados manualmente ya no se recrean automáticamente.

## [0.6.0] - 2026-03-11
### Added
- Campañas de inscripción y disponibilidad pública del formulario con validación por fechas activas.
- Mantenimiento de institución (nombre, dirección, teléfono, correo y logo) para reutilizar datos institucionales.
- Bitácora y auditoría de acciones administrativas relevantes con vista dedicada.
- Configuración de mantenimiento de proyectos con mensaje e imagen para visitantes.

### Changed
- Unificación visual de vistas administrativas en formato dashboard con tarjetas, modales y estilos consistentes.
- Ajustes de inscripción y proyectos para flujos de logística, enlaces de documentación y navegación de evaluación.
- Acciones de tablas con botones de ícono y botones de formularios con ícono y texto.

### Fixed
- Correcciones de codificación UTF-8 en vistas y textos.
- Arreglo del script de respaldo SQL para serializar correctamente campos `date` y `time`.

## [0.5.0] - 2026-03-11
### Added
- Mantenimiento académico normalizado con tablas de `niveles`, `secciones`, `especialidades` y `talleres`.
- Carga de documentación de proyecto en inscripción y mantenimiento logístico de fotos de integrantes.
- CRUD de integrantes en panel admin: agregar, editar, eliminar y actualizar foto.
- Vista pública de proyectos e inscripción alineadas al flujo ExpoTEC-1 con validaciones STEAM y Emprendimiento.

### Changed
- Rediseño global del panel admin a formato tabla con acciones por modal para todos los mantenimientos.
- Rúbricas mejoradas con listado principal por `ID` y gestión por modal de tipo de evaluación.
- Parametrización ampliada para evitar datos quemados en código en módulos administrativos.

### Fixed
- Correcciones de experiencia de edición en mantenimientos para reducir saturación visual.
- Ajustes de consistencia entre backend y vistas de administración y proyectos.

## [0.4.0] - 2026-03-11
### Added
- Panel de administración modular con menú lateral y rutas separadas por módulo.
- Parametrización completa de categorías, tipos de evaluación, rúbricas y configuración SMTP.
- Servicio SMTP con prueba de envío y notificaciones automáticas para credenciales y asignaciones.
- Formulario ExpoTEC-1 en 6 secciones con validaciones condicionales para 1 a 3 estudiantes.
- Campos extendidos para estudiantes, tutor y requerimientos del proyecto.
- Soporte de versionado del sprint mediante archivos `VERSION` y notas en `docs/sprints/`.

### Changed
- Rediseño visual institucional del sitio: header, cards, botones, dashboard y footer.
- Home pública organizada por categorías con información ampliada de proyectos.
- Modelo de evaluación desacoplado de valores quemados y conectado a parámetros de BD.

### Fixed
- Limpieza de referencias de mantenimiento y normalización de rutas de panel admin.
- Correcciones de render en formulario de inscripción con datos multivalor.

## [0.3.0] - 2026-03-11
### Added
- Respaldo automático de base de datos en cada commit usando hook `pre-commit`.
- Script de exportación SQL versionado en `scripts/backup_db.py`.
- Respaldo de referencia en `sql/backups/expotecnica_latest.sql`.

### Changed
- Documentación del flujo de respaldo en README.

## [0.2.0] - 2026-03-11
### Added
- Portada publica con proyectos por categoria.
- Carga de fotos de integrantes al servidor y visualizacion en home.
- Modelo inicial de integrantes de proyecto (`ProjectMember`).

### Changed
- Ruta principal `/` migrada de landing simple a portada de proyectos.
- Estilos globales modernizados para vistas publicas.

## [0.1.0] - 2026-03-11
### Added
- Base de la aplicacion Flask con arquitectura MVC.
- Modulos de autenticacion, panel de jueces y panel administrativo.
- Registro de proyectos y flujo de evaluacion por rubrica.
- Estructura inicial de base de datos MySQL y comandos CLI operativos.
