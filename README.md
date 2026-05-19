# 🎓 Sistema Nacional de Learning Analytics
## Predicción de Riesgo Académico en Educación Tecnológica

**Autores:** Karol Stefany Saavedra Suarez, Edson Julián Diaz Pinilla  
**Arquitectura:** Microservicios · Modelo C4 · Patrón MVVM  
**Stack:** FastAPI · Firebase · MongoDB · Scikit-Learn · Chart.js

---

## 📁 Estructura del Proyecto

```
learning-analytics/
├── backend/                    # FastAPI — Microservicios
│   ├── app/
│   │   ├── main.py             # API Gateway (FastAPI)
│   │   ├── core/
│   │   │   └── config.py       # Configuración & variables de entorno
│   │   ├── db/
│   │   │   ├── firebase.py     # Conexión Firebase Firestore (tiempo real)
│   │   │   └── mongodb.py      # Conexión MongoDB (datos históricos)
│   │   ├── models/
│   │   │   └── schemas.py      # Modelos Pydantic (M en MVVM)
│   │   ├── viewmodels/         # ViewModels (VM en MVVM)
│   │   │   ├── analytics_vm.py # ML: Random Forest + Logistic Regression
│   │   │   └── alert_vm.py     # Gestión de alertas
│   │   └── api/routes/         # Routers por microservicio
│   │       ├── events.py       # Event Service
│   │       ├── analytics.py    # Analytics Service
│   │       ├── alerts.py       # Alert Service
│   │       ├── dashboard.py    # Dashboard Service
│   │       ├── institutions.py # Institution Service
│   │       └── reports.py      # Report Service
│   ├── requirements.txt
│   └── .env.example
│
├── frontend/                   # SPA con patrón MVVM
│   ├── index.html              # Vista principal (dashboard)
│   └── src/
│       ├── models/
│       │   ├── firebase.js     # Modelo Firebase (M)
│       │   └── api.js          # Modelo API (M)
│       └── viewmodels/
│           └── dashboard_vm.js # ViewModel del Dashboard (VM)
│
└── README.md
```

---

## 🚀 Instalación y Ejecución

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env       # Editar con tus credenciales
uvicorn app.main:app --reload --port 8000
```

**Documentación Swagger:** http://localhost:8000/api/docs

### Frontend

```bash
cd frontend
# Opción 1: Live Server en VS Code (recomendado)
# Opción 2:
python -m http.server 3000
# Abrir: http://localhost:3000
```

---

## 🏗️ Arquitectura — Modelo C4

### Nivel 1 — Contexto
Actores: Estudiante, Institución, Administrador, Ministerio de Educación  
Sistemas externos: Sistemas Académicos Universitarios, Firebase Firestore

### Nivel 2 — Contenedores (Microservicios)
| Contenedor | Tecnología | Responsabilidad |
|---|---|---|
| Frontend Web | HTML/CSS/JS | Dashboards, alertas, visualización |
| API Gateway | FastAPI | Punto único de entrada, autenticación |
| Event Service | Python/FastAPI | Captura eventos académicos |
| Analytics Service | Python/Scikit-Learn | IA predictiva, clustering |
| Alert Service | Python/Firebase | Alertas automáticas |
| Dashboard Service | FastAPI/JS | Estadísticas nacionales |
| Firebase Firestore | NoSQL/Realtime | Datos en tiempo real |
| MongoDB | NoSQL | Data Lake, históricos |

### Nivel 3 — Componentes internos
- **Event Service:** Receiver → Validator → Formatter → Storage → Sender
- **Analytics Service:** Collector → Feature Processor → Prediction Model → Clustering → Risk Analyzer
- **Alert Service:** Prediction Receiver → Alert Analyzer → Generator → Notification Sender

---

## 🤖 IA Predictiva

Los modelos usados (Scikit-Learn):
- **Random Forest Classifier** (60% peso): identifica patrones complejos
- **Logistic Regression** (40% peso): clasifica nivel de riesgo
- **K-Means Clustering** (k=4): agrupa estudiantes por comportamiento

**Variables analizadas:**
- Promedio de notas
- Tasa de asistencia
- Entregas tardías
- Frecuencia de login
- Tiempo de conexión

**Niveles de riesgo:** Bajo (<30%) · Medio (30–60%) · Alto (60–80%) · Crítico (>80%)

---

## 🔥 Firebase

```javascript
// Config en frontend/src/models/firebase.js
const firebaseConfig = {
  apiKey: "AIzaSyDhug3B-1Kq6YseNYVmLRO8Qvk7P4tCkbU",
  authDomain: "prediccionriesgoacademico.firebaseapp.com",
  projectId: "prediccionriesgoacademico",
  ...
};
```

Colecciones Firestore:
- `alerts/` — Alertas académicas en tiempo real
- `predictions/` — Resultados de predicciones recientes
- `events/` — Eventos académicos capturados
- `dashboards/` — Métricas para visualización

---

## 📐 Patrón MVVM

```
View (HTML/DOM)
   ↕ data-binding
ViewModel (dashboard_vm.js / analytics_vm.py)
   ↕ observables / async
Model (api.js / firebase.js / schemas.py)
   ↕ HTTP / Firestore SDK
Data Sources (FastAPI / Firebase / MongoDB)
```

---

## ❓ Justificaciones de Arquitectura

**¿Cómo se procesan eventos masivos?**  
Microservicios desacoplados + MongoDB para almacenamiento histórico masivo + Firestore para tiempo real.

**¿Mecanismo de mensajería?**  
API REST (FastAPI) entre microservicios; Firestore actúa como bus de eventos en tiempo real.

**¿Cómo se desacoplan los módulos?**  
Cada microservicio tiene su propio dominio y base de datos. El API Gateway centraliza el acceso.

**¿Cómo se generan predicciones?**  
Pipeline: Feature extraction → StandardScaler → Random Forest (60%) + Logistic Regression (40%) → Risk level.

**¿Qué ocurre si falla el procesamiento?**  
Los eventos se almacenan en MongoDB con estado `processed=False` para reprocesamiento posterior.
