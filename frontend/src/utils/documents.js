export const isInProgress = (doc) => doc.status === 'uploaded' || doc.status === 'processing'

const STAGE_LABELS = {
  extracting: 'Extracting text, tables and images',
  describing: 'Describing figures',
  chunking: 'Splitting into passages',
  embedding: 'Creating embeddings',
}

export function stageLabel(doc) {
  if (doc.status === 'uploaded') return 'Waiting to be processed'
  return STAGE_LABELS[doc.processing_stage] ?? 'Processing'
}
