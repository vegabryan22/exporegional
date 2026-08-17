-- Correccion puntual de reconfirmacion Expo.
-- Sustituye en el conteo a Neithan Piedra Fonseca por Gabriel Solano Chaves.
-- No modifica asignaciones, tokens ni ejecuta procesos de correo.

START TRANSACTION;

SET @replacement_email = _utf8mb4'gabsc28@gmail.com' COLLATE utf8mb4_unicode_ci;
SET @withdrawn_email = _utf8mb4'neythancr2007@gmail.com' COLLATE utf8mb4_unicode_ci;

-- La correccion solo se habilita si ambos registros existen una sola vez y
-- Gabriel ya confirmo asistencia general con fecha de respuesta.
SET @replacement_ready = (
    SELECT IF(
        (SELECT COUNT(*) FROM judges WHERE email = @replacement_email AND role = 'judge') = 1
        AND (SELECT COUNT(*) FROM judges WHERE email = @withdrawn_email AND role = 'judge') = 1
        AND (SELECT attendance_confirmed FROM judges WHERE email = @replacement_email AND role = 'judge') = 1
        AND (SELECT attendance_responded_at FROM judges WHERE email = @replacement_email AND role = 'judge') IS NOT NULL,
        1,
        0
    )
);

-- Estado previo y validacion. replacement_ready debe mostrar 1.
SELECT
    @replacement_ready AS replacement_ready,
    id,
    full_name,
    email,
    attendance_confirmed,
    attendance_responded_at,
    exposition_invitation_sent_at,
    exposition_attendance_confirmed,
    exposition_attendance_responded_at
FROM judges
WHERE email IN (@replacement_email, @withdrawn_email)
ORDER BY email;

-- Copia la confirmacion general real de Gabriel al ciclo de reconfirmacion Expo.
UPDATE judges
SET
    exposition_invitation_sent_at = COALESCE(attendance_invitation_sent_at, attendance_responded_at),
    exposition_attendance_confirmed = 1,
    exposition_attendance_responded_at = attendance_responded_at
WHERE email = @replacement_email
  AND role = 'judge'
  AND @replacement_ready = 1;

SET @replacement_rows = ROW_COUNT();

-- Retira a Neithan solo del ciclo de reconfirmacion Expo.
-- Sus asignaciones documentales y el resto de su historial permanecen intactos.
UPDATE judges
SET
    exposition_invitation_sent_at = NULL,
    exposition_attendance_confirmed = NULL,
    exposition_attendance_responded_at = NULL
WHERE email = @withdrawn_email
  AND role = 'judge'
  AND @replacement_ready = 1;

SET @withdrawn_rows = ROW_COUNT();

-- Registra la intervencion si produjo algun cambio efectivo.
INSERT INTO system_audit_logs (
    actor_name,
    actor_email,
    actor_role,
    action,
    entity,
    entity_id,
    detail,
    ip_address,
    user_agent,
    created_at
)
SELECT
    'Parche SQL autorizado',
    NULL,
    'system',
    'admin.judge.expo_reconfirmation.replace',
    'judge',
    (SELECT id FROM judges WHERE email = @replacement_email AND role = 'judge'),
    CONCAT(
        'Reconfirmacion Expo corregida sin correos: ',
        @withdrawn_email,
        ' => ',
        @replacement_email
    ),
    NULL,
    'patch_expo_reconfirmation_gabriel_neithan_20260817.sql',
    UTC_TIMESTAMP()
WHERE @replacement_ready = 1
  AND (@replacement_rows > 0 OR @withdrawn_rows > 0);

COMMIT;

-- Verificacion final esperada: 31 total, 28 confirmados, 0 no asisten y 3 pendientes.
SELECT
    COUNT(*) AS total_expo,
    SUM(exposition_attendance_confirmed = 1) AS confirmados,
    SUM(exposition_attendance_confirmed = 0) AS no_asisten,
    SUM(exposition_attendance_confirmed IS NULL) AS pendientes
FROM judges
WHERE role = 'judge'
  AND (
      exposition_invitation_sent_at IS NOT NULL
      OR exposition_attendance_confirmed IS NOT NULL
  );

-- Verifica que las asignaciones no fueron alteradas.
SELECT
    j.full_name,
    SUM(a.can_evaluate_documentation = 1) AS asignaciones_documento,
    SUM(a.can_evaluate_exposition = 1) AS asignaciones_exposicion,
    COUNT(*) AS asignaciones_totales
FROM judges AS j
LEFT JOIN assignments AS a ON a.judge_id = j.id
WHERE j.email IN (@replacement_email, @withdrawn_email)
GROUP BY j.id, j.full_name
ORDER BY j.full_name;
