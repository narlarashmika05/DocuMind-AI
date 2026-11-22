import apiClient from './client'

export async function listDocuments() {
  const { data } = await apiClient.get('/documents')
  return data
}

export async function getDocument(id) {
  const { data } = await apiClient.get(`/documents/${id}`)
  return data
}

export async function uploadDocuments(files, onProgress) {
  const form = new FormData()
  files.forEach((file) => form.append('files', file))
  const { data } = await apiClient.post('/documents', form, {
    timeout: 0, // large uploads on slow connections can take minutes
    onUploadProgress: (event) => {
      if (event.total) onProgress?.(Math.round((event.loaded * 100) / event.total))
    },
  })
  return data // { uploaded: [...], rejected: [{ filename, reason }] }
}

export async function reprocessDocument(id) {
  const { data } = await apiClient.post(`/documents/${id}/reprocess`)
  return data
}

export async function deleteDocument(id) {
  await apiClient.delete(`/documents/${id}`)
}

export async function fetchDocumentFile(id) {
  // Fetched with the auth header as a Blob; a plain <a href> could not send the token.
  const { data } = await apiClient.get(`/documents/${id}/file`, { responseType: 'blob' })
  return data
}

export async function listPages(id) {
  const { data } = await apiClient.get(`/documents/${id}/pages`)
  return data
}

export async function getPage(id, pageNumber) {
  const { data } = await apiClient.get(`/documents/${id}/pages/${pageNumber}`)
  return data
}

export async function listElements(id, params = {}) {
  const { data } = await apiClient.get(`/documents/${id}/elements`, { params })
  return data
}

export function pageImagePath(id, pageNumber, zoom = 1.5) {
  return `/documents/${id}/pages/${pageNumber}/image?zoom=${zoom}`
}

export function elementImagePath(id, elementId) {
  return `/documents/${id}/elements/${elementId}/image`
}

/** Fetch any protected image as a Blob (an <img src> cannot send the Authorization header). */
export async function fetchImageBlob(path) {
  const { data } = await apiClient.get(path, { responseType: 'blob' })
  return data
}
