-- =====================================================
-- Script para poblar datos de error de invitación
-- (para testing de la funcionalidad de error display)
-- =====================================================

-- Opción 1: Actualizar por email (Sheyla Blandon Betancourt)
UPDATE judges 
SET 
    attendance_invitation_error = '554 5.7.0 Your message could not be sent. The limit on the number of allowed outgoing messages was exceeded. Try again later.',
    attendance_invitation_sent_at = NOW()
WHERE email = 'betancourthey20@gmail.com';

-- Opción 2: Actualizar por ID (si conoces el ID del juez)
-- UPDATE judges 
-- SET 
--     attendance_invitation_error = 'Error de ejemplo',
--     attendance_invitation_sent_at = NOW()
-- WHERE id = <JUDGE_ID>;

-- Verificar actualización
SELECT 
    id,
    full_name,
    email,
    attendance_token,
    attendance_invitation_sent_at,
    attendance_invitation_error
FROM judges 
WHERE email = 'betancourthey20@gmail.com';

-- Limpiar error (para reset)
-- UPDATE judges 
-- SET attendance_invitation_error = NULL 
-- WHERE email = 'betancourthey20@gmail.com';
