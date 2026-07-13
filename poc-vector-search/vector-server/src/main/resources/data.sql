-- 초기 admin 계정 (비밀번호: admin1234 → BCrypt)
INSERT INTO users (username, email, password, role)
SELECT 'admin', 'admin@poc.com', '$2b$10$3apYfhkAj8ahXoBT8iuGI.x1DAmbKNDucWzBup9bXEVgw.KVSsEly', 'ADMIN'
WHERE NOT EXISTS (SELECT 1 FROM users WHERE email = 'admin@poc.com');
