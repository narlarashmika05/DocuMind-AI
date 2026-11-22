import { useEffect, useRef } from 'react'

/** Call `callback` every `intervalMs` while `active` is true (e.g. while documents are processing). */
export default function usePolling(callback, active, intervalMs = 3000) {
  const saved = useRef(callback)

  useEffect(() => {
    saved.current = callback
  }, [callback])

  useEffect(() => {
    if (!active) return undefined
    const id = setInterval(() => saved.current(), intervalMs)
    return () => clearInterval(id)
  }, [active, intervalMs])
}
