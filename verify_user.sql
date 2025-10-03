-- Verificar que el usuario admin_plataforma@academia.com existe y tiene el rol correcto
SELECT u.id, u.email, u.rol_id, r.nombre AS rol_nombre
FROM Usuario u
JOIN Rol_Usuario r ON u.rol_id = r.id
WHERE u.email = 'admin_plataforma@academia.com';