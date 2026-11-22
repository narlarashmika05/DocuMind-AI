import { useEffect, useState } from 'react'
import { fetchImageBlob } from '../../api/documents'
import Spinner from './Spinner'

/** <img> for API images that require login: fetched with the token, shown via a blob: URL. */
export default function AuthImage({ path, alt, className = '' }) {
  const [state, setState] = useState({ path: null, url: null, failed: false })

  useEffect(() => {
    let active = true
    let objectUrl = null
    fetchImageBlob(path)
      .then((blob) => {
        if (!active) return
        objectUrl = URL.createObjectURL(blob)
        setState({ path, url: objectUrl, failed: false })
      })
      .catch(() => active && setState({ path, url: null, failed: true }))
    return () => {
      active = false
      if (objectUrl) URL.revokeObjectURL(objectUrl) // free memory when the image changes
    }
  }, [path])

  if (state.path !== path) {
    return (
      <div className={`flex items-center justify-center bg-slate-100 dark:bg-slate-800 ${className}`}>
        <Spinner />
      </div>
    )
  }
  if (state.failed) {
    return <div className={`flex items-center justify-center bg-slate-100 dark:bg-slate-800 text-sm text-slate-500 dark:text-slate-400 ${className}`}>Image unavailable</div>
  }
  return <img src={state.url} alt={alt} className={className} />
}
