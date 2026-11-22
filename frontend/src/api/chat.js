import apiClient from './client'

export async function listConversations() {
  const { data } = await apiClient.get('/conversations')
  return data
}

export async function createConversation(body = {}) {
  const { data } = await apiClient.post('/conversations', body)
  return data
}

export async function getConversation(id) {
  const { data } = await apiClient.get(`/conversations/${id}`)
  return data
}

export async function updateConversation(id, changes) {
  const { data } = await apiClient.patch(`/conversations/${id}`, changes)
  return data
}

export async function deleteConversation(id) {
  await apiClient.delete(`/conversations/${id}`)
}

export async function askQuestion(conversationId, { content, answerLanguage = 'auto', documentIds }) {
  const { data } = await apiClient.post(
    `/conversations/${conversationId}/messages`,
    { content, answer_language: answerLanguage, document_ids: documentIds ?? null },
    { timeout: 180000 }, // retrieval + LLM + verification on CPU can take a while
  )
  return data // { user_message, assistant_message }
}
