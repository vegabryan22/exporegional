# Operación de producción

## Servicios

- `exporegional.service`: plataforma regional, Gunicorn en `127.0.0.1:8011`.
- `expotecnica-institucional.service`: plataforma institucional, Gunicorn en `0.0.0.0:5055`.
- `expotecnica-healthcheck.timer`: ejecuta el control de salud cada minuto.
- `expotecnica-healthcheck.service`: verifica y recupera las aplicaciones.

Las dos aplicaciones esperan que `mysql.service` esté disponible antes de
iniciar. Ambas usan `Restart=always`, con cinco segundos entre intentos.

## Control de salud

El programa `/usr/local/sbin/expotecnica-healthcheck` verifica:

- MySQL en el puerto `3306`.
- nginx.
- plataforma institucional en `/registro-jueces` por el puerto `5055`.
- plataforma regional en `/` por el puerto `8011`.
- resolución pública del dominio regional.

Una aplicación se reinicia después de dos fallos consecutivos. Los eventos se
guardan en el journal con la etiqueta `expotecnica-watchdog`.

```bash
sudo journalctl -t expotecnica-watchdog
sudo systemctl status expotecnica-healthcheck.timer
sudo systemctl list-timers expotecnica-healthcheck.timer
```

Los errores DNS se notifican en el journal, pero no provocan reinicios: un
problema de resolución externa no implica que Gunicorn esté caído.

## Comprobaciones manuales

```bash
sudo systemctl status exporegional.service
sudo systemctl status expotecnica-institucional.service
curl -f http://127.0.0.1:8011/
curl -f http://127.0.0.1:5055/registro-jueces
```

## Respaldo de la configuración anterior

La instalación del 4 de agosto de 2026 dejó un respaldo previo en
`/www/backup/service-hardening/20260804-103054`.

## Validación de recuperación

Se realizó una prueba controlada terminando el proceso principal de cada
servicio. systemd generó un PID nuevo para ambos y las dos rutas regresaron a
HTTP 200 automáticamente.
