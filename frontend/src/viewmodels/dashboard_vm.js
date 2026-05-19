// Dashboard ViewModel — MVVM pattern
// Bridges models (API data) with views (DOM/HTML)
import { AnalyticsModel, AlertsModel, DashboardModel, EventsModel } from "../models/api.js";

export const DashboardViewModel = {
  state: {
    stats: null,
    alerts: [],
    institutions: [],
    trends: [],
    events: [],
    loading: true,
  },

  observers: [],

  subscribe(fn) {
    this.observers.push(fn);
  },

  notify() {
    this.observers.forEach(fn => fn(this.state));
  },

  async loadAll() {
    this.state.loading = true;
    this.notify();

    // Parallel fetch
    const [stats, alertsData, institutions, trendsData, eventsData] = await Promise.all([
      AnalyticsModel.getStats(),
      AlertsModel.getAll(),
      DashboardModel.getInstitutions(),
      AnalyticsModel.getTrends(),
      EventsModel.getRecent(),
    ]);

    this.state.stats = stats || this._mockStats();
    this.state.alerts = alertsData?.alerts || this._mockAlerts();
    this.state.institutions = institutions?.institutions || [];
    this.state.trends = trendsData?.trend || this.state.stats?.risk_trend || [];
    this.state.events = eventsData?.events || [];
    this.state.loading = false;
    this.notify();
  },

  _mockStats() {
    return {
      total_students: 12450,
      students_high_risk: 1876,
      students_medium_risk: 3210,
      students_low_risk: 7364,
      active_alerts: 234,
      institutions_count: 47,
      national_dropout_rate: 0.187,
      weekly_events: 98432,
      risk_trend: [
        { week: "Sem 1", high: 120, medium: 280, low: 600 },
        { week: "Sem 2", high: 145, medium: 310, low: 545 },
        { week: "Sem 3", high: 189, medium: 295, low: 516 },
        { week: "Sem 4", high: 201, medium: 330, low: 469 },
        { week: "Sem 5", high: 187, medium: 321, low: 492 },
        { week: "Sem 6", high: 220, medium: 340, low: 440 },
      ],
      top_risk_courses: [
        { course: "Cálculo I", risk_rate: 0.34 },
        { course: "Programación I", risk_rate: 0.28 },
        { course: "Álgebra Lineal", risk_rate: 0.25 },
        { course: "IA Fundamentos", risk_rate: 0.22 },
        { course: "Estadística", risk_rate: 0.19 },
      ],
      cluster_distribution: [
        { cluster: "Alto rendimiento", count: 4200, pct: 33.7 },
        { cluster: "Riesgo moderado", count: 3860, pct: 31.0 },
        { cluster: "En riesgo", count: 2890, pct: 23.2 },
        { cluster: "Crítico", count: 1500, pct: 12.1 },
      ]
    };
  },

  _mockAlerts() {
    return [
      { id: "a1", student_name: "Ana García", institution_id: "UNAL", risk_level: "critical", message: "Riesgo inminente de deserción", factors: ["Promedio 2.8", "Asistencia 45%"], read: false },
      { id: "a2", student_name: "Carlos Martínez", institution_id: "UDEA", risk_level: "high", message: "Alto riesgo detectado", factors: ["7 entregas tardías"], read: false },
      { id: "a3", student_name: "María López", institution_id: "UNAL", risk_level: "medium", message: "Riesgo moderado", factors: ["Asistencia 68%"], read: true },
      { id: "a4", student_name: "José Rodríguez", institution_id: "ITBA", risk_level: "high", message: "Sin actividad 10 días", factors: ["Sin acceso reciente"], read: false },
      { id: "a5", student_name: "Laura Sánchez", institution_id: "UDISTRITAL", risk_level: "medium", message: "Baja participación", factors: ["Tiempo de conexión reducido"], read: false },
    ];
  }
};
