# Sistema Nacional de Learning Analytics
## Prediccion de Riesgo Academico en Educacion Tecnologica
### Arquitectura de Microservicios (Fase 2)

**Autores:** Karol Stefany Saavedra Suarez, Edson Julian Diaz Pinilla
**Arquitectura:** Microservicios · MVVM · API Gateway · Database per Service
**Stack:** FastAPI · Docker · Scikit-Learn · Chart.js

---

## Arquitectura Final

```
Cliente (Browser)
    |
    | HTTP :80
    v
nginx (Frontend SPA)
    |                    Red Docker: learning-analytics-net
    | /api/*                                  |
    v                                          |
api-gateway (FastAPI, :8000)                   |
    |                                          |
    | HTTP :8001  :8002  :8003  :8004          |
    v        v      v      v                   v
event-service  analytics  alert-service  dashboard-service
  (:8001)      -service   (:8003)         (:8004) [Aggregator]
               (:8002)
                   | 
                   | HTTP (chained call)
                   v
              alert-service
              (genera alerta)
```

### Microservicios

| Microservicio | Puerto | Responsabilidad | Patron |
|---|---|---|---|
| **api-gateway** | 8000 | Proxy inverso, health check global, documentacion | API Gateway |
| **event-service** | 8001 | Captura y consulta de eventos academicos | DB in-memory |
| **analytics-service** | 8002 | Prediccion ML (RF+LR), clustering K-Means | Database per Service |
| **alert-service** | 8003 | Gestion de alertas academicas | DB in-memory |
| **dashboard-service** | 8004 | Agregador de datos multi-servicio | Aggregator / Chained |
| **frontend** | 80 | SPA con Chart.js, MVVM en JS | Static nginx |

### Patrones de Arquitectura Implementados

1. **API Gateway** — Entrada unica a traves de `api-gateway`, enrutamiento por prefijo de ruta
2. **Database per Service** — Cada servicio mantiene su propia base de datos en memoria
3. **Health Check** — Endpoint `/health` en cada microservicio
4. **Aggregator** — `dashboard-service` agrega datos de analytics y alert services
5. **Chained Microservice** — `analytics-service` llama a `alert-service` tras una prediccion de alto riesgo
6. **Asynchronous Messaging (simulado)** — Logs estructurados como traza de eventos

---

## Ejecucion con Docker Compose

### Requisitos

- Docker Engine 24+
- Docker Compose v2+

### Levantar toda la solucion

```bash
# Clonar y entrar
cd learning-analytics

# Construir e iniciar todos los servicios
docker compose up --build

# Verificar estado
docker compose ps

# Ver logs en vivo
docker compose logs -f
```

### Probar los servicios

```bash
# Health Check del Gateway
curl http://localhost:8000/health

# Health Check de todos los servicios
curl http://localhost:8000/health/all

# Predecir riesgo academico (comunicacion encadenada analytics -> alert)
curl -X POST http://localhost:8000/api/analytics/predict \
  -H "Content-Type: application/json" \
  -d '{"student_id":"s999","institution_id":"UNAL","avg_score":2.5,"attendance_rate":0.3,"late_submissions":12,"login_frequency":1}'

# Listar alertas
curl http://localhost:8000/api/alerts/

# Dashboard (aggregator)
curl http://localhost:8000/api/dashboard/summary
```

### Suite de pruebas automatizada

```bash
# Asegurarse de que los servicios esten arriba
docker compose up -d

# Ejecutar pruebas
bash pruebas.sh
```

### Detener la solucion

```bash
docker compose down
```

---

## Frontend (Interfaz de Usuario)

Disponible en: **http://localhost:80**

- Dashboard con KPIs animados
- Graficos de tendencia, donut, barras y area polar (Chart.js)
- Panel de alertas academicas en tiempo real
- Formulario de prediccion con IA (Random Forest + Logistic Regression)
- Tabla de instituciones con tasas de riesgo
- Reportes nacionales

### MVVM en Frontend

```
View (index.html)
   | data-binding (observables)
ViewModel (dashboard_vm.js)
   | async / fetch
Model (api.js)
   | HTTP /api/
API Gateway -> Microservicios
```

---

## Flujo de Comunicacion entre Servicios

### Flujo principal: Prediccion de Riesgo

```
1. Usuario ingresa datos en formulario IA Predictiva
2. Frontend -> POST /api/analytics/predict
3. API Gateway -> analytics-service:8002
4. analytics-service ejecuta Random Forest (60%) + Logistic Regression (40%)
5. Si riesgo >= MEDIO: analytics-service -> POST /api/alerts/generate
6. alert-service almacena alerta en DB in-memory
7. Respuesta al frontend con prediccion + alerta generada
```

### Flujo Aggregator: Dashboard

```
1. Frontend -> GET /api/dashboard/summary
2. API Gateway -> dashboard-service:8004
3. dashboard-service -> GET analytics-service:8002/stats
4. dashboard-service -> GET alert-service:8003/unread-count
5. dashboard-service combina y responde
```

---

## Manejo de Fallos (Test del Mono)

| Escenario | Comportamiento |
|---|---|
| Servicio caido | API Gateway retorna 503 con mensaje descriptivo |
| Timeout en llamado encadenado | El servicio continúa con datos locales/mock |
| Ruta inexistente | 404 con lista de servicios disponibles |
| Redis/Cache no disponible | Operacion continua sin cache |

---

## Variables de Entorno

Ver `.env.example` para configuracion completa.

---

## Coleccion de Pruebas (Postman/cURL)

Incluida en `pruebas.sh` — pruebas automatizadas de:
- Health checks individuales y globales
- CRUD de eventos
- Prediccion con ML
- Alertas y marcado como leidas
- Dashboard aggregator
- Flujo completo encadenado
- Test del mono (servicio caido)

---

## Estructura del Repositorio

```
learning-analytics/
  api-gateway/            # FastAPI - Proxy inverso
    Dockerfile
    app/main.py
  event-service/          # Microservicio de eventos
    Dockerfile
    app/main.py
  analytics-service/      # ML + IA Predictiva
    Dockerfile
    app/main.py
    app/viewmodel.py
  alert-service/          # Alertas academicas
    Dockerfile
    app/main.py
  dashboard-service/      # Aggregator
    Dockerfile
    app/main.py
  frontend/               # SPA con nginx
    Dockerfile
    nginx.conf
    index.html
    src/models/api.js
    src/models/firebase.js
    src/viewmodels/dashboard_vm.js
  backend/                # (Original - monolito Fase 1)
  docker-compose.yml
  .env.example
  pruebas.sh
  README.md
```

---

## Comparacion Fase 1 vs Fase 2

| Aspecto | Fase 1 (Monolito) | Fase 2 (Microservicios) |
|---|---|---|
| Estructura | Un solo backend FastAPI | 4 microservicios independientes + API Gateway |
| Despliegue | `uvicorn app.main:app` | `docker compose up --build` |
| Comunicacion | Llamadas a funciones internas | HTTP/REST entre contenedores |
| Persistencia | Firebase + MongoDB compartidos | DB in-memory por servicio |
| Patrones | MVVM | API Gateway, DB per Service, Aggregator, Health Check |
| Aislamiento | Modulos en el mismo proceso | Contenedores independientes |
| Frontend | Mock data inline | API calls con fallback a mock |
| Escalabilidad | Vertical (un solo proceso) | Horizontal (replicar contenedores) |

---

## Stack Tecnologico

- **FastAPI** — Microservicios REST
- **Docker / Docker Compose** — Contenedores y orquestacion
- **Scikit-Learn** — Random Forest, Logistic Regression, K-Means
- **Chart.js** — Visualizacion en frontend
- **nginx** — Servidor web y proxy inverso
- **Python 3.12** — Lenguaje backend
- **Vanilla JS** — Frontend SPA sin frameworks

---

## Evidencias de Validacion

Las pruebas automatizadas en `pruebas.sh` cubren:
- 8 escenarios de validacion
- Health checks de todos los servicios
- Operaciones CRUD en eventos
- Prediccion ML con comunicacion encadenada
- Dashboard aggregation multi-servicio
- Manejo de errores y rutas inexistentes
