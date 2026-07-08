-- =====================================================
-- Script para SINCRONIZAR ERRORES DE INVITACIÓN
-- desde la bitácora a los registros de jueces
-- =====================================================

-- PASO 1: Ver todos los errores registrados en bitácora
-- Ejecuta esto primero para ver qué errores hay
SELECT 
    sal.id,
    j.id as judge_id,
    j.full_name,
    j.email,
    sal.action,
    sal.detail,
    sal.created_at
FROM system_audit_logs sal
LEFT JOIN judges j ON sal.entity = 'judge' AND sal.entity_id = j.id
WHERE sal.action LIKE '%attendance_invite%'
   OR sal.detail LIKE '%error%'
   OR sal.detail LIKE '%Error%'
   OR sal.detail LIKE '%could not be sent%'
ORDER BY sal.created_at DESC
LIMIT 100;

-- =====================================================
-- PASO 2: Sincronizar AUTOMÁTICAMENTE jueces con errores
-- (Ejecuta después de revisar el PASO 1)
-- =====================================================

-- Sincronizar errores específicos por email
-- Descomenta la línea que corresponda al juez o ejecuta todas:

-- Windell Jarquin Alvarado
UPDATE judges j
SET 
    attendance_invitation_error = '554 5.7.0 Your message could not be sent. The limit on the number of allowed outgoing messages was exceeded. Try again later.',
    attendance_invitation_sent_at = COALESCE(attendance_invitation_sent_at, NOW() - INTERVAL 1 DAY)
WHERE j.email = 'windelljarquin44@gmail.com'
  AND (attendance_invitation_error IS NULL OR attendance_invitation_error = '');

-- Sheyla Blandon Betancourt  
UPDATE judges j
SET 
    attendance_invitation_error = '554 5.7.0 Your message could not be sent. The limit on the number of allowed outgoing messages was exceeded. Try again later.',
    attendance_invitation_sent_at = COALESCE(attendance_invitation_sent_at, NOW() - INTERVAL 1 DAY)
WHERE j.email = 'betancourthey20@gmail.com'
  AND (attendance_invitation_error IS NULL OR attendance_invitation_error = '');

-- O SINCRONIZAR TODOS a la vez desde la bitácora:
UPDATE judges j
SET 
    attendance_invitation_error = COALESCE(
        (SELECT SUBSTRING(sal.detail, 1, 500)
         FROM system_audit_logs sal
         WHERE sal.entity = 'judge' 
         AND sal.entity_id = j.id
         AND (sal.detail LIKE '%error%' OR sal.detail LIKE '%Error%' OR sal.detail LIKE '%could not be sent%')
         ORDER BY sal.created_at DESC
         LIMIT 1),
        attendance_invitation_error
    ),
    attendance_invitation_sent_at = COALESCE(
        (SELECT MAX(sal.created_at)
         FROM system_audit_logs sal
         WHERE sal.entity = 'judge' 
         AND sal.entity_id = j.id
         AND (sal.detail LIKE '%error%' OR sal.detail LIKE '%Error%' OR sal.detail LIKE '%could not be sent%')
         LIMIT 1),
        attendance_invitation_sent_at
    )
WHERE EXISTS (
    SELECT 1 FROM system_audit_logs sal
    WHERE sal.entity = 'judge' 
    AND sal.entity_id = j.id
    AND (sal.detail LIKE '%error%' OR sal.detail LIKE '%Error%' OR sal.detail LIKE '%could not be sent%')
);

-- =====================================================
-- PASO 3: Verificar que se sincronizaron correctamente
-- =====================================================
SELECT 
    j.id,
    j.full_name,
    j.email,
    j.attendance_token,
    j.attendance_invitation_sent_at,
    LEFT(j.attendance_invitation_error, 100) as error_preview
FROM judges j
WHERE j.attendance_invitation_error IS NOT NULL
ORDER BY j.attendance_invitation_sent_at DESC;
