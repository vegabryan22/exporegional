# API de integración institucional

## Propósito

La plataforma regional recibe una copia de los proyectos ganadores. Cada plataforma institucional conserva su propia base de datos y se comunica exclusivamente por HTTPS/JSON y carga multipart. La credencial determina el colegio propietario; el cliente no puede elegir otro colegio en el contenido enviado.

En la etapa regional el tutor es únicamente un nombre asociado al proyecto. Si se envía el objeto `tutor`, solo se utiliza `tutor.name`; correo, teléfono y demás datos personales no se almacenan ni se requieren.

## Credenciales

Desde **Administración > Colegios participantes** se genera un token para un colegio habilitado. El valor completo se muestra una sola vez y la base regional conserva únicamente su hash SHA-256. Debe enviarse como `Authorization: Bearer <token>`.

Para rotar una credencial: crear una nueva, configurarla y probarla en el sistema institucional, y luego revocar la anterior. Nunca registrar el token en Git, capturas, bitácoras ni documentos.

## Contrato v1

Base local: `http://127.0.0.1:5001/api/v1`. En producción debe utilizarse HTTPS.

- `POST /regional-projects`: crea o actualiza un ganador.
- `POST /regional-projects/{external_project_id}/files`: adjunta `project_document`, `project_logo` y fotografías `member_photo_1` a `member_photo_3` como multipart.
- `GET /regional-projects/{external_project_id}/status`: consulta estado y observaciones regionales.

La cabecera `Idempotency-Key` debe ser estable por proyecto. Además, la combinación colegio + `external_project_id` es única: un reintento actualiza el mismo registro mientras siga en `received` o `returned`.

Ejemplo mínimo del JSON:

```json
{
  "external_project_id": "CTPRGV-000123",
  "external_source": "ExpoTécnica institucional",
  "payload_version": "1.0",
  "title": "Proyecto ganador",
  "team_name": "Equipo",
  "category_code": "steam",
  "description": "Descripción",
  "tutor": {"name": "Tutor", "email": "tutor@example.com", "phone": "8888-8888"},
  "students": [{"name": "Estudiante", "email": "estudiante@example.com"}],
  "institutional_result": {"winner": true}
}
```

Se aceptan entre uno y tres estudiantes. La categoría debe existir y estar activa en la plataforma regional. El sufijo numérico de cada fotografía corresponde a `student_number` y permite vincularla con el integrante correcto.

## Respuestas y operación

Las respuestas siempre son JSON. Los éxitos usan `ok: true`; los errores usan `ok: false` y un objeto `error` con `code`, `message` y, cuando aplica, `field`.

- `200`: actualización, archivos o consulta correcta.
- `201`: proyecto creado.
- `400`: JSON inválido.
- `401`: token ausente, inválido o vencido.
- `403`: colegio deshabilitado.
- `404`: proyecto no encontrado para ese colegio.
- `409`: el proyecto ya avanzó y está bloqueado para reemplazo.
- `422`: datos, categoría, estudiantes o archivos inválidos.

Cada intento autenticado queda auditado en `project_import_events`. Los reintentos son seguros si conservan el identificador externo. La regional nunca consulta directamente la base institucional.
