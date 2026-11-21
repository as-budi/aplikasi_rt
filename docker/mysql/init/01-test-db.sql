-- Izinkan user aplikasi membuat database tes (pytest-django membuat `test_aplikasi_rt`).
-- Hanya dijalankan saat volume database pertama kali dibuat (pengembangan).
GRANT ALL PRIVILEGES ON `test_aplikasi_rt`.* TO 'rt'@'%';
FLUSH PRIVILEGES;
