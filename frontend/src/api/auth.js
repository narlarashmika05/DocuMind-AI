import apiClient from './client'

export async function register({ fullName, email, password }) {
  const { data } = await apiClient.post('/auth/register', { full_name: fullName, email, password })
  return data
}

export async function login(email, password) {
  // OAuth2 password flow: form-encoded `username` + `password` (username = email)
  const form = new URLSearchParams({ username: email, password })
  const { data } = await apiClient.post('/auth/login', form)
  return data
}

export async function logout() {
  await apiClient.post('/auth/logout')
}
