# Auditoría y normalización relacional

Estado: trabajo local; no desplegado.

## Principios

- Cada catálogo tiene una sola fuente de verdad y se referencia mediante llave foránea.
- Los nombres, códigos o descripciones de un catálogo no se duplican en tablas operativas.
- Los textos históricos se conservan únicamente en tablas de auditoría o instantáneas explícitas.
- Toda llave foránea define su comportamiento de borrado y dispone de índice.
- Las asociaciones de varios elementos se representan con filas, no con JSON ni listas de texto.
- Las restricciones de unicidad y dominio se aplican en la base de datos, no solamente en Python.

## Hallazgos

| Área | Duplicación o debilidad | Diseño objetivo |
|---|---|---|
| Proyecto / colegio | `projects.institution_name` junto a `institution_id` | Solo `institution_id`; el nombre sale de `institutions` |
| Proyecto / categoría | `projects.category` junto a `category_id` | Solo `category_id` |
| Proyecto / sección | `grade_level` junto a información de integrantes | La sección pertenece a cada integrante mediante `section_id` |
| Proyecto / especialidad | `projects.specialty` y especialidades de integrantes | `project_members.specialty_id`; no resumen textual persistido |
| Integrante / sección | `section_name` sin FK | `section_id -> sections.id` |
| Integrante / especialidad | `specialty` junto a `specialty_id` | Solo `specialty_id` |
| Proyecto / tutor | `tutor_id` y siete columnas `advisor_*` | Solo `tutor_id`; los datos salen de `tutors` |
| Mentor | Siete columnas embebidas en `projects` | Entidad `mentors` y `projects.mentor_id` |
| Evaluación / tipo | `evaluation_type` textual pese a `evaluation_types` | `evaluation_type_id -> evaluation_types.id` |
| Evaluación / puntajes | `criteria_1..4` junto a `evaluation_scores` | Solo filas en `evaluation_scores` |
| Usuario / rol | `role` junto a `is_admin` | Solo `role`, con dominio controlado |
| Usuario / institución | `institution` junto a `institution_id` | Colegio mediante FK; empleador externo con nombre semántico distinto |
| Requisitos | lista textual, JSON y varias banderas | Catálogo y tabla asociativa por proyecto |

## Datos que deben permanecer como texto

No todo texto es desnormalización. Permanecen como atributos: nombres personales, correos,
teléfonos, descripción, observaciones, rutas de archivos, identificadores externos y detalles
de auditoría. Las tablas de historial pueden conservar instantáneas porque su propósito es
registrar el valor que existía en el momento del evento.

## Orden de migración

1. Crear las llaves y tablas normalizadas que faltan.
2. Convertir los datos heredados y detener la migración si queda algún valor sin correspondencia.
3. Cambiar todas las escrituras y lecturas para utilizar relaciones.
4. Agregar restricciones, índices y reglas de borrado.
5. Eliminar columnas duplicadas únicamente después de comprobar que quedaron sin consumidores.
6. Ejecutar pruebas de integridad, migración ascendente y reversión sobre una copia local.
