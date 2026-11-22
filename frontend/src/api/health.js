import apiClient from './client'

export async function getHealth() {
  try {
    const { data } = await apiClient.get('/health')
    return data
  } catch (error) {
    // A 503 still carries a JSON body saying which part is down, so return it.
    if (error.response?.data?.status) return error.response.data
    throw error
  }
}
