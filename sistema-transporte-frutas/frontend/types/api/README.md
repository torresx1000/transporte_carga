# Tipos de la API

`schema.d.ts` se genera desde el contrato OpenAPI de FastAPI. Para actualizarlo después de cambiar endpoints o esquemas:

1. Desde `backend/`, ejecuta `venv\\Scripts\\python.exe scripts/export_openapi.py` (o el Python del entorno virtual equivalente). Esto actualiza `backend/openapi.json` sin iniciar el servidor.
2. Desde `frontend/`, ejecuta `npm run gen:api`. Esto regenera `types/api/schema.d.ts`.

Los tipos generados reflejan el contrato OpenAPI publicado. Las respuestas que el backend no declara con `response_model` aparecen como `unknown` o sin esquema concreto.
