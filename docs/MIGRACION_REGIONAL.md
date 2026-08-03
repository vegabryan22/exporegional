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
7. `evaluated` — Evaluado.
8. `regional_winner` — Ganador regional.

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

## Verificación

- Reconstrucción completa del esquema en base temporal: satisfactoria.
- Reversión de la migración regional hacia la línea base heredada: satisfactoria.
- Aplicación de migraciones sobre `exporegional`: satisfactoria.
- Pruebas automatizadas: 44 aprobadas.
- Compilación de módulos Python: satisfactoria.
- Respuesta local de portada: HTTP 200.

La revisión visual automatizada mediante el navegador integrado no estuvo disponible en el entorno de ejecución. La respuesta HTTP y el contenido se verificaron, pero se mantiene pendiente una revisión visual manual de escritorio y móvil.

El fondo de certificados institucional no se reutiliza. Los certificados regionales permanecen con fondo neutro hasta recibir un recurso gráfico regional aprobado con el nombre `regional_bg.jpg`.

La revisión base heredada está diseñada como punto de partida reproducible, no como una operación para destruir toda la base. Su `upgrade` fue validado desde cero; no debe ejecutarse `downgrade base` sobre ambientes con datos. Las migraciones regionales posteriores sí deben ofrecer reversión hasta esta línea base.

## Próximas etapas

1. Servicio central de transiciones de estado con reglas y auditoría.
2. Asociación obligatoria de nuevos proyectos con colegio y categoría regional.
3. Portal y permisos de coordinador de colegio.
4. Inscripción manual regional con revisión, devolución y reenvío.
5. Credenciales por colegio y API regional versionada e idempotente.
6. Configuración de categorías, rúbricas, jueces y reportes regionales.
7. Aplicación de escudo y paleta oficial cuando estén disponibles.
