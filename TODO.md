# TODO - Roadmap Profesional de GameVault

## Fase 1 - Seguridad y operacion

- [x] Mover configuracion sensible a variables de entorno
- [x] Preparar entrada `wsgi.py` para produccion
- [x] Desactivar dependencia en `debug=True` para produccion
- [x] Endurecer cookies de sesion
- [x] Agregar CSRF y rate limiting
- [x] Cambiar acciones sensibles a `POST`
- [x] Separar `/demo` de `/dashboard`
- [x] Agregar `healthz`
- [x] Configurar logging estructurado y Sentry opcional
- [x] Preparar uploads firmados a S3

## Fase 2 - Beta publica

- [x] Simplificar onboarding
- [x] Agregar busqueda, filtros, orden y paginacion
- [x] Crear pagina de perfil
- [x] Completar trazabilidad de auth y CRUD principal
- [x] Crear landing y paginas legales basicas
- [x] Fijar dependencias y documentacion operativa
- [ ] Agregar verificacion de email antes de habilitar funciones premium
- [ ] Medir embudo de conversion visita > registro > primer juego

## Fase 3 - Escalado tecnico

- [x] Crear indice para buscar `reset_token` sin scan
- [x] Agregar TTL para logs y tokens
- [x] Agregar `created_at` y `updated_at` en nuevos registros
- [x] Preparar indice global para consultar logs por tiempo
- [x] Añadir CI basico y pruebas de smoke
- [ ] Mover estadisticas agregadas a consultas/materializaciones dedicadas
- [ ] Añadir backups y runbook operativo formal
- [ ] Evaluar CloudFront para entrega de imagenes a gran escala

## Hosting actual recomendado

- `PythonAnywhere Developer` para la app Flask
- `DynamoDB + S3 + SES` como servicios administrados en AWS
