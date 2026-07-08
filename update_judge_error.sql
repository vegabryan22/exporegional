-- Update judge record with invitation error for testing
UPDATE judges 
SET 
    attendance_invitation_error = '554 5.7.0 Your message could not be sent. The limit on the number of allowed outgoing messages was exceeded. Try again later.',
    attendance_invitation_sent_at = NOW()
WHERE email = 'betancourthey20@gmail.com';

-- Verify update
SELECT 
    id,
    full_name,
    email,
    attendance_token,
    attendance_invitation_sent_at,
    attendance_invitation_error
FROM judges 
WHERE email = 'betancourthey20@gmail.com';
