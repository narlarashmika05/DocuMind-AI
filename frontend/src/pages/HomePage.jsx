import { Link } from 'react-router'
import BackendStatus from '../components/BackendStatus'
import ThemeToggle from '../components/ui/ThemeToggle'
import useAuth from '../hooks/useAuth'

const LINK_STYLES = {
  primary: 'bg-indigo-600 text-white hover:bg-indigo-700',
  secondary:
    'border border-slate-300 bg-white text-slate-700 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-200 dark:hover:bg-slate-800',
}

const FEATURES = [
  {
    title: 'Answers with evidence',
    text: 'Every answer cites the exact document and page. Click a citation to see the passage and the original page.',
  },
  {
    title: 'Hallucination checks',
    text: 'Each statement is checked against its sources by a separate model and marked supported, partly supported or not supported.',
  },
  {
    title: 'English and తెలుగు',
    text: 'Ask in English or Telugu about English documents, and choose the language of the answer.',
  },
  {
    title: 'Tables, charts and scans',
    text: 'Tables become structured data, charts are described by a vision model, and scanned pages are read with OCR.',
  },
]

const STEPS = [
  ['Upload', 'Add research papers, notes or textbooks as PDF.'],
  ['Process', 'Text, tables and figures are extracted, split into passages and indexed for meaning and keywords.'],
  ['Ask', 'Get a cited answer, with every statement checked against the evidence — or an honest "not in your documents".'],
]

function LinkButton({ to, variant = 'primary', children }) {
  return (
    <Link to={to} className={`rounded-lg px-5 py-2.5 font-medium ${LINK_STYLES[variant]}`}>
      {children}
    </Link>
  )
}

export default function HomePage() {
  const { status } = useAuth()

  return (
    <div className="min-h-screen">
      <header className="mx-auto flex max-w-6xl items-center justify-between px-4 py-4">
        <span className="text-lg font-bold tracking-tight">
          DocuMind <span className="text-indigo-600 dark:text-indigo-400">AI</span>
        </span>
        <div className="flex items-center gap-2">
          <ThemeToggle />
          {status !== 'authenticated' && (
            <Link to="/login" className="rounded-lg px-3 py-1.5 text-sm font-medium hover:bg-slate-100 dark:hover:bg-slate-800">
              Log in
            </Link>
          )}
        </div>
      </header>

      <main className="mx-auto max-w-6xl space-y-20 px-4 pb-20 pt-12">
        <section className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Research answers you can <span className="text-indigo-600 dark:text-indigo-400">verify</span>
          </h1>
          <p className="mt-5 text-lg text-slate-600 dark:text-slate-400">
            DocuMind AI is a multimodal, multilingual research assistant. Ask questions about your own documents in English
            or Telugu and get answers grounded in cited evidence — with every statement checked for hallucinations.
          </p>
          <div className="mt-8 flex flex-wrap justify-center gap-3">
            {status === 'authenticated' ? (
              <LinkButton to="/chat">Open the assistant</LinkButton>
            ) : (
              <>
                <LinkButton to="/register">Get started free</LinkButton>
                <LinkButton to="/login" variant="secondary">
                  Log in
                </LinkButton>
              </>
            )}
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {FEATURES.map((feature) => (
            <article
              key={feature.title}
              className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900"
            >
              <h2 className="font-semibold">{feature.title}</h2>
              <p className="mt-2 text-sm leading-relaxed text-slate-600 dark:text-slate-400">{feature.text}</p>
            </article>
          ))}
        </section>

        <section>
          <h2 className="text-center text-2xl font-semibold">How it works</h2>
          <ol className="mt-8 grid gap-6 md:grid-cols-3">
            {STEPS.map(([title, text], index) => (
              <li key={title} className="flex gap-4">
                <span className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-600 font-semibold text-white">
                  {index + 1}
                </span>
                <div>
                  <h3 className="font-semibold">{title}</h3>
                  <p className="mt-1 text-sm text-slate-600 dark:text-slate-400">{text}</p>
                </div>
              </li>
            ))}
          </ol>
        </section>

        <section className="flex flex-col items-center gap-3">
          <BackendStatus />
          <p className="max-w-md text-center text-xs text-slate-500 dark:text-slate-400">
            Automatic verification greatly reduces, but cannot fully eliminate, incorrect answers. Always check important
            facts against the cited sources.
          </p>
        </section>
      </main>
    </div>
  )
}
