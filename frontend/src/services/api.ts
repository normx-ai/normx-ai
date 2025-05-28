// src/services/api.ts
import axios from 'axios';

// Configuration de base pour l'API avec Vite
const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Afficher l'URL utilisée en développement
if (import.meta.env.DEV) {
  console.log('API URL:', API_BASE_URL);
}

// Créer une instance axios avec la configuration de base
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Intercepteur pour ajouter le token d'authentification si nécessaire
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Intercepteur pour gérer les erreurs
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (import.meta.env.DEV) {
      console.error('API Error:', error.response?.data || error.message);
    }
    return Promise.reject(error);
  }
);

// Services pour les comptes
export const comptesService = {
  getAll: (params?: any) => {
    if (import.meta.env.DEV) {
      console.log('Fetching comptes with params:', params);
    }
    return api.get('/comptes/', { params });
  },
  getById: (id: number) => api.get(`/comptes/${id}/`),
  create: (data: any) => api.post('/comptes/', data),
  update: (id: number, data: any) => api.put(`/comptes/${id}/`, data),
  delete: (id: number) => api.delete(`/comptes/${id}/`),
  // Actions spéciales
  getActifs: () => api.get('/comptes/actifs/'),
  getParClasse: () => api.get('/comptes/par_classe/'),
  getStats: (id: number) => api.get(`/comptes/${id}/stats/`),
  search: (query: string) => api.get('/comptes/search/', { params: { q: query } }),
};

// Services pour les journaux
export const journauxService = {
  getAll: (params?: any) => api.get('/journaux/', { params }),
  getById: (id: number) => api.get(`/journaux/${id}/`),
  create: (data: any) => api.post('/journaux/', data),
  update: (id: number, data: any) => api.put(`/journaux/${id}/`, data),
  delete: (id: number) => api.delete(`/journaux/${id}/`),
};

// Services pour les tiers
export const tiersService = {
  getAll: (params?: any) => api.get('/tiers/', { params }),
  getById: (id: number) => api.get(`/tiers/${id}/`),
  create: (data: any) => api.post('/tiers/', data),
  update: (id: number, data: any) => api.put(`/tiers/${id}/`, data),
  delete: (id: number) => api.delete(`/tiers/${id}/`),
};

// Services pour les exercices
export const exercicesService = {
  getAll: (params?: any) => api.get('/exercices/', { params }),
  getById: (id: number) => api.get(`/exercices/${id}/`),
  create: (data: any) => api.post('/exercices/', data),
  update: (id: number, data: any) => api.put(`/exercices/${id}/`, data),
  delete: (id: number) => api.delete(`/exercices/${id}/`),
  ouvrir: (id: number) => api.post(`/exercices/${id}/ouvrir/`),
  cloturer: (id: number) => api.post(`/exercices/${id}/cloturer/`),
  genererPeriodes: (id: number) => api.post(`/exercices/${id}/generer_periodes/`),
  getStats: (id: number) => api.get(`/exercices/${id}/stats/`),
  getPeriodes: (id: number) => api.get(`/exercices/${id}/periodes/`),
};

// Services pour les écritures
export const ecrituresService = {
  getAll: (params?: any) => api.get('/ecritures/', { params }),
  getById: (id: number) => api.get(`/ecritures/${id}/`),
  create: (data: any) => api.post('/ecritures/', data),
  update: (id: number, data: any) => api.put(`/ecritures/${id}/`, data),
  delete: (id: number) => api.delete(`/ecritures/${id}/`),
  valider: (id: number) => api.post(`/ecritures/${id}/valider/`),
  dupliquer: (id: number) => api.post(`/ecritures/${id}/dupliquer/`),
  getLignes: (id: number) => api.get(`/ecritures/${id}/lignes/`),
};

// Services pour les périodes
export const periodesService = {
  getAll: (params?: any) => api.get('/periodes/', { params }),
  getById: (id: number) => api.get(`/periodes/${id}/`),
  cloturer: (id: number) => api.post(`/periodes/${id}/cloturer/`),
  rouvrir: (id: number) => api.post(`/periodes/${id}/rouvrir/`),
  getByExercice: (exerciceId: number) => api.get(`/periodes/par_exercice/${exerciceId}/`),
};

// Export de l'instance API pour utilisation directe si nécessaire
export default api;