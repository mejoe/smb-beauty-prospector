import axios from 'axios'

const BASE_URL = import.meta.env.VITE_API_URL || '/api'

export const api = axios.create({
  baseURL: BASE_URL,
  headers: { 'Content-Type': 'application/json' },
})

// Attach access token to every request
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Auto-refresh on 401
api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const originalRequest = error.config
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true
      try {
        const refreshToken = localStorage.getItem('refresh_token')
        if (!refreshToken) throw new Error('No refresh token')
        const resp = await axios.post(`${BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })
        const { access_token, refresh_token } = resp.data
        localStorage.setItem('access_token', access_token)
        localStorage.setItem('refresh_token', refresh_token)
        originalRequest.headers.Authorization = `Bearer ${access_token}`
        return api(originalRequest)
      } catch {
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

// Auth API
export const authApi = {
  register: (email: string, password: string, name?: string) =>
    api.post('/auth/register', { email, password, name }),
  login: (email: string, password: string) =>
    api.post('/auth/login', { email, password }),
  logout: () => api.delete('/auth/logout'),
  me: () => api.get('/auth/me'),
}

// Sessions API
export const sessionsApi = {
  list: () => api.get('/sessions'),
  create: (name: string, description?: string) =>
    api.post('/sessions', { name, description }),
  get: (id: string) => api.get(`/sessions/${id}`),
  update: (id: string, data: object) => api.put(`/sessions/${id}`, data),
  delete: (id: string) => api.delete(`/sessions/${id}`),
}

// Companies API
export const companiesApi = {
  list: (params?: object) => api.get('/companies', { params }),
  create: (data: object) => api.post('/companies', data),
  get: (id: string) => api.get(`/companies/${id}`),
  update: (id: string, data: object) => api.put(`/companies/${id}`, data),
  delete: (id: string) => api.delete(`/companies/${id}`),
  search: (sessionId: string, searchConfig?: object) =>
    api.post('/companies/search', { session_id: sessionId, search_config: searchConfig }),
  import: (file: File, sessionId?: string) => {
    const form = new FormData()
    form.append('file', file)
    return api.post(`/companies/import${sessionId ? `?session_id=${sessionId}` : ''}`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
  },
  export: (params?: object) =>
    api.get('/companies/export', { params, responseType: 'blob' }),
}

// Contacts API
export const contactsApi = {
  list: (params?: object) => api.get('/contacts', { params }),
  create: (data: object) => api.post('/contacts', data),
  get: (id: string) => api.get(`/contacts/${id}`),
  update: (id: string, data: object) => api.put(`/contacts/${id}`, data),
  delete: (id: string) => api.delete(`/contacts/${id}`),
  enrich: (id: string) => api.post(`/contacts/${id}/enrich`),
  bulkEnrich: (ids: string[]) => api.post('/contacts/bulk-enrich', ids),
  discover: (companyId: string) => api.post(`/contacts/discover/${companyId}`),
  importCsv: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/contacts/import', form, { headers: { 'Content-Type': 'multipart/form-data' } })
  },
  exportCsv: (params?: object) =>
    api.get('/contacts/export', { params, responseType: 'blob' }),
}

// Outreach API
export const outreachApi = {
  listCampaigns: () => api.get('/outreach/campaigns'),
  createCampaign: (data: object) => api.post('/outreach/campaigns', data),
  updateCampaign: (id: string, data: object) =>
    api.put(`/outreach/campaigns/${id}`, data),
  startCampaign: (id: string) =>
    api.post(`/outreach/campaigns/${id}/send`),
  pauseCampaign: (id: string) =>
    api.post(`/outreach/campaigns/${id}/pause`),
  getMessages: (id: string, params?: object) =>
    api.get(`/outreach/campaigns/${id}/messages`, { params }),
}

// Instagram API
export const instagramApi = {
  sessionStatus: () => api.get('/instagram/session-status'),
  saveSession: (username: string, cookiesJson: string) =>
    api.post('/instagram/session', { username, cookies_json: cookiesJson }),
  deleteSession: () => api.delete('/instagram/session'),
}

// Jobs API
export const jobsApi = {
  list: (params?: object) => api.get('/jobs', { params }),
  get: (id: string) => api.get(`/jobs/${id}`),
}
