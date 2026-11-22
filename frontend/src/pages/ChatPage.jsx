import { useCallback, useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { askQuestion, createConversation, deleteConversation, getConversation, listConversations } from '../api/chat'
import { getErrorMessage } from '../api/client'
import { listDocuments } from '../api/documents'
import AssistantMessage from '../components/chat/AssistantMessage'
import Composer from '../components/chat/Composer'
import SourcePanel from '../components/chat/SourcePanel'
import Alert from '../components/ui/Alert'
import Spinner from '../components/ui/Spinner'
import useAuth from '../hooks/useAuth'

const EXAMPLES = [
  'Summarise the main contribution of this paper.',
  'What dataset was used for evaluation?',
  'ఈ పత్రంలోని ముఖ్యమైన ఫలితాలు ఏమిటి?',
]

function ThinkingBubble() {
  return (
    <div className="flex max-w-3xl items-center gap-3 rounded-2xl rounded-tl-sm border border-slate-200 bg-white px-4 py-3 text-sm text-slate-500 shadow-sm dark:border-slate-700 dark:bg-slate-900">
      <Spinner className="h-4 w-4" />
      Searching your documents, writing and checking the answer…
    </div>
  )
}

export default function ChatPage() {
  const { conversationId } = useParams()
  const navigate = useNavigate()
  const { user } = useAuth()
  const [conversations, setConversations] = useState([])
  const [conversation, setConversation] = useState(null)
  const [documents, setDocuments] = useState([])
  const [scope, setScope] = useState([])
  const [language, setLanguage] = useState(user.preferred_language === 'te' ? 'te' : 'auto')
  const [pending, setPending] = useState(null) // question being answered
  const [error, setError] = useState('')
  const [selected, setSelected] = useState({ messageId: null, source: null })
  const bottomRef = useRef(null)

  const refreshList = useCallback(() => listConversations().then(setConversations).catch(() => {}), [])

  useEffect(() => {
    refreshList()
    listDocuments()
      .then(setDocuments)
      .catch(() => {})
  }, [refreshList])

  useEffect(() => {
    let active = true
    if (!conversationId) {
      Promise.resolve().then(() => active && setConversation(null))
      return () => {
        active = false
      }
    }
    getConversation(conversationId)
      .then((data) => {
        if (!active) return
        setConversation(data)
        setScope(data.document_ids ?? [])
        const last = [...data.messages].reverse().find((m) => m.role === 'assistant')
        setSelected({ messageId: last?.id ?? null, source: null })
      })
      .catch((err) => active && setError(getErrorMessage(err)))
    return () => {
      active = false
    }
  }, [conversationId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [conversation?.messages.length, pending])

  async function handleSend(question) {
    setError('')
    setPending(question)
    try {
      let target = conversation
      if (!target) {
        target = { ...(await createConversation({ document_ids: scope.length ? scope : null })), messages: [] }
      }
      const { user_message, assistant_message } = await askQuestion(target.id, {
        content: question,
        answerLanguage: language,
        documentIds: scope.length ? scope : null,
      })
      setConversation({
        ...target,
        title: target.messages.length ? target.title : question.slice(0, 80),
        messages: [...target.messages, user_message, assistant_message],
      })
      setSelected({ messageId: assistant_message.id, source: assistant_message.citations[0]?.number ?? null })
      if (!conversationId) navigate(`/chat/${target.id}`, { replace: true })
      refreshList()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setPending(null)
    }
  }

  async function handleDelete(id) {
    if (!window.confirm('Delete this conversation?')) return
    try {
      await deleteConversation(id)
      setConversations((list) => list.filter((c) => c.id !== id))
      if (String(id) === conversationId) navigate('/chat')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const messages = conversation?.messages ?? []
  const selectedMessage = messages.find((m) => m.id === selected.messageId)
  const readyCount = documents.filter((d) => d.status === 'ready').length

  return (
    <div className="grid gap-6 lg:grid-cols-[14rem_minmax(0,1fr)_22rem]">
      {/* Conversation list */}
      <aside className="space-y-2">
        <Link
          to="/chat"
          className="block rounded-lg bg-indigo-600 px-3 py-2 text-center text-sm font-medium text-white hover:bg-indigo-700"
        >
          + New chat
        </Link>
        <nav className="max-h-[60vh] space-y-1 overflow-y-auto lg:max-h-[calc(100vh-12rem)]">
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center rounded-lg text-sm ${
                String(c.id) === conversationId
                  ? 'bg-indigo-50 text-indigo-700 dark:bg-indigo-950/50 dark:text-indigo-300'
                  : 'hover:bg-slate-100 dark:hover:bg-slate-800'
              }`}
            >
              <Link to={`/chat/${c.id}`} className="min-w-0 flex-1 truncate px-3 py-2" title={c.title}>
                {c.title}
              </Link>
              <button
                onClick={() => handleDelete(c.id)}
                className="px-2 text-slate-400 opacity-0 hover:text-red-600 group-hover:opacity-100"
                aria-label={`Delete conversation ${c.title}`}
              >
                ✕
              </button>
            </div>
          ))}
        </nav>
      </aside>

      {/* Messages */}
      <section className="flex min-h-[70vh] flex-col">
        <div className="flex-1 space-y-5 pb-4">
          {messages.length === 0 && !pending && (
            <div className="rounded-2xl border border-dashed border-slate-300 px-6 py-12 text-center dark:border-slate-700">
              <h1 className="text-xl font-semibold">Ask your documents anything</h1>
              <p className="mt-2 text-sm text-slate-500">
                Answers cite their sources and every statement is checked against the evidence.
              </p>
              {readyCount === 0 ? (
                <p className="mt-4 text-sm">
                  <Link to="/documents" className="font-medium text-indigo-600 hover:underline">
                    Upload a document
                  </Link>{' '}
                  first — answers come only from your files.
                </p>
              ) : (
                <div className="mt-5 flex flex-wrap justify-center gap-2">
                  {EXAMPLES.map((example) => (
                    <button
                      key={example}
                      onClick={() => handleSend(example)}
                      className="rounded-full border border-slate-300 px-3 py-1 text-sm hover:bg-slate-100 dark:border-slate-600 dark:hover:bg-slate-800"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {messages.map((message) =>
            message.role === 'user' ? (
              <div key={message.id} className="flex justify-end">
                <p
                  lang={message.language}
                  className="max-w-2xl rounded-2xl rounded-tr-sm bg-indigo-600 px-4 py-2.5 text-sm text-white"
                >
                  {message.content}
                </p>
              </div>
            ) : (
              <AssistantMessage
                key={message.id}
                message={message}
                activeSource={selected.messageId === message.id ? selected.source : null}
                onSelectSource={(source) => setSelected({ messageId: message.id, source })}
              />
            ),
          )}

          {pending && (
            <>
              <div className="flex justify-end">
                <p className="max-w-2xl rounded-2xl rounded-tr-sm bg-indigo-600/80 px-4 py-2.5 text-sm text-white">
                  {pending}
                </p>
              </div>
              <ThinkingBubble />
            </>
          )}
          <div ref={bottomRef} />
        </div>

        <div className="sticky bottom-4 space-y-2">
          {error && <Alert onClose={() => setError('')}>{error}</Alert>}
          <Composer
            onSend={handleSend}
            disabled={Boolean(pending)}
            language={language}
            onLanguageChange={setLanguage}
            documents={documents}
            scope={scope}
            onScopeChange={setScope}
          />
        </div>
      </section>

      {/* Sources */}
      <aside className="lg:sticky lg:top-4 lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-500">Sources</h2>
        <SourcePanel
          message={selectedMessage}
          activeSource={selected.source}
          onSelectSource={(source) => setSelected({ ...selected, source })}
        />
      </aside>
    </div>
  )
}
