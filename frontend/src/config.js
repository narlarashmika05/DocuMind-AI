export const API_URL = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1'

// Mirrors backend limits so users get instant feedback. The backend still enforces them.
export const MAX_FILE_SIZE_MB = 25
export const MAX_FILES_PER_UPLOAD = 10
