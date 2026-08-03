# Migración de ExpoTécnica institucional a ExpoTécnica Regional

## Propósito

Este repositorio es una plataforma regional independiente. No representa al CTP Roberto Gamboa Valverde ni comparte su base de datos. Su objetivo es centralizar colegios participantes, recibir proyectos ganadores, validarlos y ejecutar la evaluación regional.

## Aislamiento confirmado

- Repositorio: `https://github.com/vegabryan22/exporegional.git`.
- Base local: `exporegional`.
- Usuario local de aplicación: `exporegional_user`.
- Puerto local regional: `5001`.
- La instancia institucional conserva el puerto `5000` y no fue intervenida.

## Decisiones de arquitectura

### Migraciones

Se incorporó Flask-Migrate/Alembic. La revisión `c43b8abbefe3` reproduce las 22 tablas heredadas desde una base vacía. La revisión `963e78601998` agrega el núcleo regional.

La aplicación conserva temporalmente `AUTO_INIT_DB=1` para compatibilidad con las conciliaciones históricas de datos. Los comandos Alembic y las pruebas deben utilizar `AUTO_INIT_DB=0`. Los nuevos cambios estructurales se implementarán exclusivamente mediante migraciones.

### Colegio participante

Responsabilidad operativa:

- La coordinación regional consulta el directorio, habilita o suspende participación y proporciona el acceso técnico.
- Cada colegio mantiene su propio perfil, responsable, ubicación y escudo desde una cuenta coordinadora aislada.
- Los colegios sin plataforma registran ganadores desde su portal; los que tienen plataforma institucional envían copias mediante API.
- El panel regional no edita directamente la identidad ni los datos operativos del colegio.
- Un administrador general activo puede abrir una sesión de soporte como coordinación del colegio; la suplantación es visible, auditada y reversible sin conocer la contraseña.

La entidad `Institution` representa un centro educativo participante y conserva:

- código único;
- nombre;
- circuito y dirección regional;
- dirección física;
- responsable, correo y teléfono;
- uso o no de plataforma institucional;
- estado de participación y activación;
- relación con usuarios y proyectos.

La cantidad de proyectos se deriva de la relación y no se almacena como contador mutable.

### Proyecto regional

Cada proyecto puede asociarse con un colegio y una categoría mediante claves foráneas. Se añadieron:

- origen `institutional_api` o `regional_manual`;
- estado regional;
- identificador externo idempotente por colegio;
- procedencia y versión de payload;
- fechas de envío, recepción y aprobación;
- responsable de aprobación y notas regionales;
- historial de cambios de estado.

Estados iniciales:

1. `draft` — Borrador.
2. `submitted_by_school` — Enviado por colegio.
3. `received` — Recibido.
4. `under_review` — En revisión.
5. `approved_for_evaluation` — Aprobado para evaluación.
6. `returned_for_correction` — Devuelto para corrección.
7. `evaluated` — Evaluado, asignado automáticamente al completar todas las evaluaciones requeridas.
8. `regional_winner` — Ganador regional, calculado automáticamente por categoría cuando todos sus proyectos están evaluados.

### Usuarios

Se definió el rol `school_coordinator`, separado de jueces y administradores regionales. Todavía no se habilita su portal: la siguiente etapa debe implementar autorización estricta por `institution_id` antes de permitir acceso operativo.

## Identidad regional

Se eliminaron de las pantallas principales las referencias al CTP Roberto Gamboa Valverde, CTPRGV, etapa institucional y proyectos institucionales. La configuración global ahora utiliza “ExpoTécnica Regional”.

Mientras no exista un escudo oficial se usa una paleta temporal neutra en grises azulados. Los colores principales están centralizados como variables CSS en `app/static/style.css`. Cuando se reciba el escudo se documentarán y aplicarán colores extraídos de la identidad aprobada.

No debe utilizarse un logo institucional de un colegio como reemplazo temporal del escudo regional.

## Funcionalidad entregada

- Módulo administrativo `/admin/colegios`.
- Alta y edición de colegios.
- Activación y desactivación.
- Modalidad API o inscripción manual.
- Estados de participación.
- Conteo derivado de proyectos.
- Auditoría de altas, cambios y activación.
- Creación de cuentas coordinadoras vinculadas con contraseña temporal y cambio obligatorio.
- Portal `/colegio/panel` aislado por colegio.
- Registro manual de proyectos ganadores como borradores.
- Carga de PDF, logo, tutor y hasta tres estudiantes.
- Envío y reenvío controlado hacia coordinación regional.
- Bandeja `/admin/revision-regional` para recepción, revisión, devolución y aprobación.
- Servicio único de transiciones utilizado por colegio y administración.

## Reglas operativas de estados

- Colegio: `draft → submitted_by_school`.
- Coordinación regional: `submitted_by_school → received → under_review`.
- Revisión: `under_review → approved_for_evaluation` o `returned_for_correction`.
- Colegio: `returned_for_correction → submitted_by_school`.
- Resultado automático: `approved_for_evaluation → evaluated → regional_winner`; no existen botones administrativos para declarar estos estados.

No se permiten saltos de estado. Cada transición crea un registro en `project_status_history` con usuario, fecha y observación.

## Verificación

- Reconstrucción completa del esquema en base temporal: satisfactoria.
- Reversión de la migración regional hacia la línea base heredada: satisfactoria.
- Aplicación de migraciones sobre `exporegional`: satisfactoria.
- Pruebas automatizadas: 49 aprobadas.
- Compilación de módulos Python: satisfactoria.
- Respuesta local de portada: HTTP 200.

La revisión visual automatizada mediante el navegador integrado no estuvo disponible en el entorno de ejecución. La respuesta HTTP y el contenido se verificaron, pero se mantiene pendiente una revisión visual manual de escritorio y móvil.

El fondo de certificados institucional no se reutiliza. Los certificados regionales permanecen con fondo neutro hasta recibir un recurso gráfico regional aprobado con el nombre `regional_bg.jpg`.

La revisión base heredada está diseñada como punto de partida reproducible, no como una operación para destruir toda la base. Su `upgrade` fue validado desde cero; no debe ejecutarse `downgrade base` sobre ambientes con datos. Las migraciones regionales posteriores sí deben ofrecer reversión hasta esta línea base.

## Próximas etapas

1. Credenciales por colegio y API regional versionada e idempotente.
2. Notificaciones por correo para envío, devolución y aprobación.
3. Validaciones documentales regionales más detalladas.
4. Configuración de categorías, rúbricas, jueces y reportes regionales.
5. Aplicación de escudo y paleta oficial cuando estén disponibles.

## Formularios regionales

La inscripción manual desde el portal de un colegio reutiliza el formulario oficial ExpoTEC-1 y su controlador de validación. No existe un segundo formulario simplificado para crear proyectos. La ruta regional determina el colegio desde la sesión, asigna el origen `regional_manual` y guarda inicialmente el proyecto en estado `draft`. El envío a coordinación continúa siendo una acción posterior y explícita desde el panel del colegio.

## Responsabilidad logística y documental

Cada colegio administra los recursos, necesidades operativas, logo y fotografías de sus proyectos. Para los registros manuales, el colegio también carga el PDF y no puede enviar el proyecto mientras falten el documento, el logo o alguna fotografía. La coordinación regional no completa ni aprueba logística: revisa el PDF y resuelve el expediente documental. Si el colegio reemplaza el documento, su validación regional se reinicia.

El administrador regional conserva autoridad para corregir o eliminar colegios. Cada edición registra valores anteriores y posteriores. La eliminación exige escribir el código exacto, conserva los proyectos históricos sin institución activa, desactiva cuentas coordinadoras y elimina credenciales API.
