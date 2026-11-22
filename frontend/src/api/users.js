import apiClient from './client'

export async function updateProfile(changes) {
  const { data } = await apiClient.patch('/users/me', changes)
  return data
}

export async function changePassword(currentPassword, newPassword) {
  await apiClient.post('/users/me/password', {
    current_password: currentPassword,
    new_password: newPassword,
  })
}

export async function deleteAccount(password) {
  await apiClient.delete('/users/me', { data: { password } })
}
