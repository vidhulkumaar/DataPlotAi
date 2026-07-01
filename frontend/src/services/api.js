import axios from 'axios'
import toast from 'react-hot-toast'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

api.interceptors.response.use(
  res => res,
  err => {
    const msg = err.response?.data?.detail || err.message || 'An error occurred'
    if (err.response?.status === 401) {
      localStorage.removeItem('dp_token')
      window.location.href = '/login'
    } else if (err.response?.status !== 404) {
      toast.error(typeof msg === 'string' ? msg : JSON.stringify(msg))
    }
    return Promise.reject(err)
  }
)

export default api