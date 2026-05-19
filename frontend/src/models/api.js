// API Service — Model Layer (communicates with FastAPI backend)
const BASE_URL = "http://localhost:8000/api";

const api = {
  async get(path) {
    try {
      const r = await fetch(`${BASE_URL}${path}`);
      return await r.json();
    } catch {
      return null;
    }
  },
  async post(path, body) {
    try {
      const r = await fetch(`${BASE_URL}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      return await r.json();
    } catch {
      return null;
    }
  }
};

export const EventsModel = {
  getRecent: () => api.get("/events/recent"),
  getStats:  () => api.get("/events/stats"),
  capture:   (e) => api.post("/events/", e),
};

export const AnalyticsModel = {
  getStats:      () => api.get("/analytics/stats"),
  getTrends:     () => api.get("/analytics/trends"),
  getTopCourses: () => api.get("/analytics/top-risk-courses"),
  predict:       (p) => api.post("/analytics/predict", p),
};

export const AlertsModel = {
  getAll:       () => api.get("/alerts/"),
  getUnread:    () => api.get("/alerts/unread-count"),
};

export const DashboardModel = {
  getSummary:      () => api.get("/dashboard/summary"),
  getInstitutions: () => api.get("/dashboard/institutions"),
};

export const ReportsModel = {
  getNational: () => api.get("/reports/national"),
};
