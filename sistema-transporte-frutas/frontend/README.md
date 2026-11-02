# TransFrutas · Frontend

Frontend Next.js App Router para el sistema de cargas y retornos. La comunicación HTTP usa Axios y TanStack Query; Zustand conserva la sesión del navegador y las validaciones de formularios usan React Hook Form y Zod.

## Arranque local

1. Configura `NEXT_PUBLIC_API_URL=http://localhost:8000/api/v1` en `.env.local`.
2. Inicia FastAPI en `http://localhost:8000`.
3. En `frontend/`, ejecuta `npm install` y luego `npm run dev`.
4. Abre `http://localhost:3000` e inicia sesión con una cuenta creada en el backend.

Comprobaciones disponibles: `npm run lint`, `npx tsc --noEmit` y `npm run build`.

## Integración

```text
app/
├── api/auth/{login,refresh,logout}/route.ts  # puente Next para cookies HttpOnly
├── login/page.tsx
├── (admin)/                                  # panel y módulos administrativos
└── (portal-cliente)/cliente/                 # portal conectado a /portal/*
lib/
├── api/{client,endpoints,errors}.ts
├── auth/{authStore,tokenStorage,useAuth}.ts
└── query/{keys,queryClient}.ts
services/                                     # servicios HTTP por módulo
hooks/                                        # hooks React Query por módulo
types/api/                                    # tipos de request y response
features/                                     # vistas con el diseño existente
proxy.ts                                      # protección de rutas en Next 16
```

Las suites automatizadas de frontend se retiraron por solicitud del proyecto.

Los endpoints REST usados son `/clientes`, `/cargas`, `/conductores`, `/vehiculos`, `/rutas`, `/viajes`, `/cotizaciones`, `/retornos`, `/documentos`, `/gastos`, `/combustible`, `/mantenimiento`, `/pagos`, `/usuarios` y `/configuracion`. Los reportes usan `/reportes/dashboard`, `/reportes/consumo-combustible`, `/reportes/jabas-pendientes` y `/reportes/rentabilidad-viaje/{id}`. El portal cliente usa `/portal/me`, `/portal/cargas`, `/portal/viajes`, `/portal/documentos` y `/portal/pagos`.

El access token se guarda en el almacenamiento local del navegador; el refresh token y las cookies de sesión/rol se guardan como HttpOnly desde route handlers de Next. El proxy de Next controla el acceso visual; FastAPI sigue siendo quien valida JWT y permisos reales.

## Datos reales y alcance

- No existe endpoint de carga de fotos/archivos; la interfaz permite seleccionarlos y avisa que no quedan guardados.
- No existe endpoint de posición GPS; el dashboard deja el espacio de seguimiento sin marcadores ficticios.
- El dashboard solo expone contadores; los importes agregados y la serie temporal de costos no se inventan desde el frontend.
- Los listados, formularios y cambios de estado de los módulos administrativos consultan la API. Si la base de datos no tiene registros, la interfaz muestra el estado vacío para permitir el ingreso de información real.
