import apiClient from './client'

export async function searchDocuments({ query, mode = 'hybrid', rerank = true, topK = 5, documentIds }) {
  const { data } = await apiClient.post(
    '/search',
    { query, mode, rerank, top_k: topK, document_ids: documentIds?.length ? documentIds : null },
    { timeout: 60000 }, // the first search may wait for models to load
  )
  return data
}
