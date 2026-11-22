// How each verification verdict is shown. The wording avoids claiming certainty:
// NLI-based checking is a strong signal, not proof.
export const VERDICTS = {
  supported: {
    label: 'Supported',
    icon: '✓',
    badge: 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300',
    text: '',
    help: 'The cited passage supports this statement.',
  },
  partially_supported: {
    label: 'Partly supported',
    icon: '~',
    badge: 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300',
    text: 'decoration-amber-400',
    help: 'The sources support only part of this statement. Check the evidence.',
  },
  unsupported: {
    label: 'Not supported',
    icon: '!',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    text: 'decoration-red-400',
    help: 'No source passage supports this statement. It may be a hallucination.',
  },
  contradicted: {
    label: 'Contradicted',
    icon: '✕',
    badge: 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-300',
    text: 'decoration-red-500',
    help: 'A source passage appears to say the opposite.',
  },
  not_checked: {
    label: 'Not checked',
    icon: '?',
    badge: 'bg-slate-100 text-slate-600 dark:bg-slate-800 dark:text-slate-300',
    text: '',
    help: 'This statement was not verified.',
  },
}

export const verdictInfo = (verdict) => VERDICTS[verdict] ?? VERDICTS.not_checked

export function summarize(claims) {
  const checked = claims.filter((c) => c.verdict !== 'not_checked')
  const supported = checked.filter((c) => c.verdict === 'supported').length
  const flagged = checked.filter((c) => ['unsupported', 'contradicted'].includes(c.verdict)).length
  return { total: claims.length, checked: checked.length, supported, flagged }
}
