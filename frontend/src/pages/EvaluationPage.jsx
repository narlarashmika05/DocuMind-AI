import { useEffect, useState } from 'react'
import apiClient, { getErrorMessage } from '../api/client'
import { DataTable } from '../components/charts/ChartFrame'
import GroupedBarChart from '../components/charts/GroupedBarChart'
import LineChart from '../components/charts/LineChart'
import Alert from '../components/ui/Alert'
import Spinner from '../components/ui/Spinner'

const LANGUAGE_LABELS = { en: 'English questions', te: 'Telugu questions', te_raw: 'Telugu, no translation' }
const MODEL_LABELS = {
  'minilm-en': 'MiniLM (English-only)',
  'multilingual-e5-small': 'Multilingual E5 small',
  'multilingual-e5-base': 'Multilingual E5 base',
  'bge-m3': 'BGE-M3',
}

function StatTile({ label, value, note }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <p className="text-sm text-slate-500 dark:text-slate-400">{label}</p>
      <p className="mt-1 text-3xl font-semibold tabular-nums">{value}</p>
      {note && <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">{note}</p>}
    </div>
  )
}

function pivot(rows, groupKey, seriesKey, metric, groupLabels = {}, seriesLabels = {}) {
  const groups = [...new Set(rows.map((r) => r[groupKey]))]
  const seriesNames = [...new Set(rows.map((r) => r[seriesKey]))]
  return {
    groups: groups.map((g) => groupLabels[g] ?? g),
    series: seriesNames.map((s) => ({
      label: seriesLabels[s] ?? s,
      values: groups.map((g) => rows.find((r) => r[groupKey] === g && r[seriesKey] === s)?.[metric] ?? 0),
    })),
  }
}

function RetrievalSection({ run }) {
  const { experiments, gate, dataset } = run
  const models = experiments.embedding_models?.rows ?? []
  const modes = (experiments.retrieval_modes?.rows ?? []).map((r) => ({ ...r, config: `${r.mode}${r.rerank ? ' + rerank' : ''}` }))
  const chunking = experiments.chunking?.rows ?? []
  const find = (rows, match) => rows.find((r) => Object.entries(match).every(([k, v]) => r[k] === v))
  const e5Te = find(models, { model: 'multilingual-e5-base', language: 'te' })
  const miniTe = find(models, { model: 'minilm-en', language: 'te' })
  const best = [...modes].filter((r) => r.language === 'en').sort((a, b) => b.mrr - a.mrr)[0]

  return (
    <section className="space-y-6">
      <h2 className="text-xl font-semibold">Retrieval</h2>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {dataset.answerable} answerable questions over {dataset.documents} documents ({dataset.pages} pages), each asked in
        English and Telugu. A retrieved passage counts as relevant if it comes from a gold page.
      </p>
      <div className="grid gap-4 sm:grid-cols-3">
        {best && <StatTile label="Best English MRR" value={best.mrr.toFixed(3)} note={`${best.config}, recall@5 ${best['recall@5'].toFixed(2)}`} />}
        {e5Te && <StatTile label="Telugu → English MRR (multilingual)" value={e5Te.mrr.toFixed(3)} note="Multilingual E5, dense" />}
        {miniTe && <StatTile label="Telugu → English MRR (English-only)" value={miniTe.mrr.toFixed(3)} note="MiniLM baseline, dense" />}
      </div>

      {models.length > 0 && (
        <GroupedBarChart
          title="Embedding models: MRR by question language"
          subtitle="Dense retrieval, recursive chunking. Higher is better."
          yLabel="MRR"
          {...pivot(models, 'model', 'language', 'mrr', MODEL_LABELS, LANGUAGE_LABELS)}
        />
      )}
      {modes.length > 0 && (
        <GroupedBarChart
          title="Retrieval configuration: MRR"
          subtitle="Multilingual E5. Telugu uses the English translation for BM25 and the reranker; 'no translation' does not."
          yLabel="MRR"
          {...pivot(modes, 'config', 'language', 'mrr', {}, LANGUAGE_LABELS)}
        />
      )}
      {chunking.length > 0 && (
        <GroupedBarChart
          title="Chunking: MRR by chunk size"
          subtitle="Hybrid search, English questions. Chunk size in embedding-model tokens."
          yLabel="MRR"
          {...pivot(
            chunking.map((r) => ({ ...r, size: `${r.chunk_size ?? 300} tokens` })),
            'size',
            'strategy',
            'mrr',
          )}
        />
      )}
      {gate && (
        <LineChart
          title="Relevance gate trade-off"
          subtitle="Refuse to answer when the best reranker probability is below the threshold."
          xLabel="Threshold"
          x={gate.map((r) => r.threshold)}
          series={[
            { label: 'Answerable questions answered', values: gate.map((r) => r.answerable_answered) },
            { label: 'Unanswerable questions refused', values: gate.map((r) => r.unanswerable_refused) },
          ]}
        />
      )}
      <details className="rounded-2xl border border-slate-200 bg-white p-5 text-sm dark:border-slate-800 dark:bg-slate-900">
        <summary className="cursor-pointer font-medium">All retrieval configurations</summary>
        <div className="mt-3">
          <DataTable
            columns={['Model', 'Chunking', 'Size', 'Chunks', 'Mode', 'Rerank', 'Language', 'MRR', 'P@3', 'R@5', 'Latency ms']}
            rows={Object.values(experiments).flatMap((e) =>
              e.rows.map((r) => [
                MODEL_LABELS[r.model] ?? r.model,
                r.strategy,
                r.chunk_size ?? 300,
                r.chunks,
                r.mode,
                r.rerank ? 'yes' : 'no',
                r.language,
                r.mrr,
                r['precision@3'],
                r['recall@5'],
                r.latency_ms_mean.toFixed(0),
              ]),
            )}
          />
        </div>
      </details>
    </section>
  )
}

function VerifierSection({ run }) {
  const m = run.binary
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">Hallucination detector</h2>
      <p className="text-sm text-slate-600 dark:text-slate-400">
        {run.total} labelled claims checked with the NLI verifier. Positive = hallucination (unsupported or contradicted).
      </p>
      <div className="grid gap-4 sm:grid-cols-4">
        <StatTile label="Precision" value={m.precision.toFixed(2)} note="Flags that were real hallucinations" />
        <StatTile label="Recall" value={m.recall.toFixed(2)} note="Hallucinations that were caught" />
        <StatTile label="F1" value={m.f1.toFixed(2)} />
        <StatTile label="Exact verdict accuracy" value={run.three_class_accuracy.toFixed(2)} note="supported / unsupported / contradicted" />
      </div>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <h3 className="mb-2 font-semibold">Confusion matrix (rows = true label)</h3>
        <DataTable
          columns={['True label', 'supported', 'partly', 'unsupported', 'contradicted']}
          rows={Object.entries(run.confusion).map(([label, c]) => [label, c.supported, c.partially_supported, c.unsupported, c.contradicted])}
        />
        {run.errors.length > 0 && (
          <>
            <h3 className="mb-2 mt-5 font-semibold">Mistakes</h3>
            <DataTable columns={['Claim', 'True', 'Predicted']} rows={run.errors.map((e) => [e.claim, e.gold, e.predicted])} />
          </>
        )}
      </div>
    </section>
  )
}

function GenerationSection({ run }) {
  return (
    <section className="space-y-4">
      <h2 className="text-xl font-semibold">End-to-end answers ({run.model})</h2>
      <div className="rounded-2xl border border-slate-200 bg-white p-5 dark:border-slate-800 dark:bg-slate-900">
        <DataTable
          columns={['Language', 'Faithfulness', 'Hallucination rate', 'Answer relevance', 'Context recall', 'Abstention', 'Latency s']}
          rows={run.summary.map((s) => [
            s.language,
            s.faithfulness ?? '—',
            s.hallucination_rate ?? '—',
            s.answer_relevance ?? '—',
            s.context_recall ?? '—',
            s.abstention_unanswerable ?? '—',
            s.latency_s_mean ?? '—',
          ])}
        />
      </div>
    </section>
  )
}

export default function EvaluationPage() {
  const [runs, setRuns] = useState(null)
  const [loaded, setLoaded] = useState({})
  const [error, setError] = useState('')

  useEffect(() => {
    let active = true
    apiClient
      .get('/evaluation/runs')
      .then(async ({ data }) => {
        const latest = {}
        for (const run of data) latest[run.kind] ??= run.name // newest first
        const entries = await Promise.all(
          Object.entries(latest).map(async ([kind, name]) => [kind, (await apiClient.get(`/evaluation/runs/${name}`)).data]),
        )
        if (!active) return
        setRuns(data)
        setLoaded(Object.fromEntries(entries))
      })
      .catch((err) => active && setError(getErrorMessage(err)))
    return () => {
      active = false
    }
  }, [])

  if (error) return <Alert>{error}</Alert>
  if (!runs) {
    return (
      <div className="flex justify-center py-10">
        <Spinner />
      </div>
    )
  }

  return (
    <div className="space-y-10">
      <div>
        <h1 className="text-2xl font-semibold">Research evaluation</h1>
        <p className="mt-1 max-w-3xl text-slate-600 dark:text-slate-400">
          Measured results from the reproducible benchmark in <code>evaluation/</code>. Small synthetic corpus — use these to
          compare configurations, not as absolute quality claims.
        </p>
      </div>
      {runs.length === 0 && (
        <Alert type="info">
          No results yet. From the project folder run <code>backend\.venv\Scripts\python evaluation\run_retrieval_eval.py</code> and{' '}
          <code>evaluation\run_verifier_eval.py</code>, then reload.
        </Alert>
      )}
      {loaded.retrieval && <RetrievalSection run={loaded.retrieval} />}
      {loaded.verifier && <VerifierSection run={loaded.verifier} />}
      {loaded.generation ? (
        <GenerationSection run={loaded.generation} />
      ) : (
        runs.length > 0 && (
          <Alert type="info">
            End-to-end answer metrics need a Gemini key: run <code>evaluation\run_generation_eval.py --limit 20</code>.
          </Alert>
        )
      )}
    </div>
  )
}
