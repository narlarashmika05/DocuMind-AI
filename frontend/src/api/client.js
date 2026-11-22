import axios from 'axios'
import { API_URL } from '../config'

// Shared Axios instance: every API call goes through here.
const apiClient = axios.create({
  baseURL: API_URL,
  timeout: 15000,
  withCredentials: true, // send the httpOnly refresh cookie to /auth/* endpoints
})

// The access token lives only in memory, never in localStorage, so a malicious
// script injected into the page cannot read it from storage.
let accessToken = null
let onSessionExpired = () => {}
let refreshPromise = null

export function setAccessToken(token) {
  accessToken = token
}

export function setSessionExpiredHandler(handler) {
  onSessionExpired = handler
}

/**
 * Exchange the refresh cookie for a new access token.
 * Each refresh token works only once, so simultaneous callers share one request.
 */
export function refreshSession() {
  refreshPromise ??= apiClient
    .post('/auth/refresh')
    .then(({ data }) => {
      accessToken = data.access_token
      return data
    })
    .finally(() => {
      refreshPromise = null
    })
  return refreshPromise
}

apiClient.interceptors.request.use((config) => {
  if (accessToken) config.headers.Authorization = `Bearer ${accessToken}`
  return config
})

// Access tokens expire after 15 minutes. On a 401, refresh once and retry the request.
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const original = error.config
    const isAuthCall = original?.url?.startsWith('/auth/')
    if (error.response?.status === 401 && original && !original._retried && !isAuthCall) {
      original._retried = true
      try {
        await refreshSession()
        return apiClient(original)
      } catch {
        accessToken = null
        onSessionExpired()
      }
    }
    return Promise.reject(error)
  },
)

/** Turn any Axios error into a sentence that can be shown to the user. */
export function getErrorMessage(error, fallback = 'Something went wrong. Please try again.') {
  const detail = error?.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail) && detail.length) {
    // FastAPI validation errors: [{ loc, msg }, ...]
    return detail.map((item) => item.msg.replace(/^Value error, /, '')).join('. ')
  }
  if (error?.code === 'ECONNABORTED') return 'The request timed out. Please try again.'
  if (!error?.response) return 'Cannot reach the server. Is the backend running?'
  return fallback
}

export default apiClient
