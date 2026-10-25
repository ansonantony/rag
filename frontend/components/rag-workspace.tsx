'use client'

import { useRef, useState, useEffect } from 'react'
import {
  ArrowUp,
  Check,
  CircleHelp,
  Loader2,
  MessageSquareText,
  PanelLeft,
  Plus,
  Search,
  Sparkles,
  Upload,
  X,
} from 'lucide-react'

import { useAuth } from '@/src/context/AuthContext'

const apiBase =
  process.env.NEXT_PUBLIC_RAG_API_URL || 'http://127.0.0.1:8000'

type DocumentItem = {
  id: string
  name: string
  size: string
  status: 'ready' | 'indexing' | 'error'
}

type Answer = {
  question: string
  answer: string
}

type Session = {
  id: string
  title: string
  preview: string
}

const starterQuestions = [
  'What is this document about?',
  'Summarize the main ideas',
  'What should I remember from this?',
]

export function RagWorkspace() {
  const { user, token, login, register, logout, authFetch } = useAuth()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [documents, setDocuments] = useState<DocumentItem[]>([])
  const [sessions, setSessions] = useState<Session[]>([])
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null)
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<Answer | null>(null)
  const [isAsking, setIsAsking] = useState(false)
  const [isUploading, setIsUploading] = useState(false)
  const [isUploadOpen, setIsUploadOpen] = useState(false)
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false)
  const [error, setError] = useState('')
  const [isAuthModalOpen, setIsAuthModalOpen] = useState(!user)
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login')
  const [authEmail, setAuthEmail] = useState('')
  const [authPassword, setAuthPassword] = useState('')
  const [isAuthLoading, setIsAuthLoading] = useState(false)
  const [selectedDocumentId, setSelectedDocumentId] = useState<string | null>(null)

  // Initialize user data and sessions on load
  async function initializeApp() {
    if (user) {
      await loadUserData()
    }
  }

  // Load user's documents and sessions
  async function loadUserData() {
    try {
      // Load documents
      const docsResponse = await authFetch('/api/v1/documents/')

      if (docsResponse.ok) {
        const docsData = await docsResponse.json()

        setDocuments(
          docsData.map((doc: any) => ({
            id: doc.id,
            name: doc.filename,
            size: `${formatBytes(doc.file_size)} · Ready`,
            status: doc.status.toLowerCase() as
              | 'ready'
              | 'indexing'
              | 'error',
          })),
        )
      }

      // Load sessions
      const sessionsResponse = await authFetch('/api/v1/chat/sessions/')

      if (sessionsResponse.ok) {
        const sessionsData = await sessionsResponse.json()

        setSessions(
          sessionsData.map((session: any) => ({
            id: session.id,
            title: session.title || 'Untitled',
            preview:
              session.messages.length > 0
                ? session.messages[
                    session.messages.length - 1
                  ].content.substring(0, 50) + '...'
                : 'Start a conversation...',
          })),
        )

        // Set active session to the most recent one,
        // or create new if none exist
        if (sessionsData.length > 0) {
          setActiveSessionId(sessionsData[0].id)
        } else {
          await createNewSession()
        }
      }
    } catch (err) {
      console.error('Failed to load user data:', err)
      setError('Failed to load your data. Please try again later.')
    }
  }

  async function uploadFile(file: File) {
    setError('')
    setIsUploading(true)

    setDocuments((current) => [
      ...current,
      {
        id: '',
        name: file.name,
        size: 'Indexing…',
        status: 'indexing',
      },
    ])

    try {
      const formData = new FormData()
      formData.append('file', file)

      const response = await authFetch('/api/v1/documents/', {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        throw new Error('Upload failed')
      }

      // Reload documents to get updated status
      await loadUserData()
    } catch (err: any) {
      setDocuments((current) =>
        current.filter((doc) => doc.name !== file.name),
      )

      setError(
        err.message ||
          'Could not upload this file. Make sure the API is running and exposes POST /api/v1/documents/.',
      )
    } finally {
      setIsUploading(false)
    }
  }

  async function createNewSession() {
    if (!selectedDocumentId) {
      setError('Please select a document to create a chat session')
      return
    }

    try {
      const response = await authFetch('/api/v1/chat/sessions/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          title: 'New conversation',
          document_id: selectedDocumentId
        }),
      })

      if (!response.ok) {
        throw new Error('Failed to create session')
      }

      const sessionData = await response.json()

      const newSession: Session = {
        id: sessionData.id,
        title: sessionData.title,
        preview: 'Start a new question...',
      }

      setSessions((prev) => [
        newSession,
        ...prev.filter((s) => s.id !== newSession.id),
      ])

      setActiveSessionId(newSession.id)
      setQuestion('')
      setAnswer(null)
      setError('')
    } catch (err) {
      setError('Failed to create new session. Please try again.')
    }
  }

  function selectSession(session: Session) {
    setActiveSessionId(session.id)
    setQuestion('')
    setAnswer(null)
    setError('')
  }

  async function askQuestion(value = question) {
    if (!activeSessionId) {
      await createNewSession()
    }

    const trimmed = value.trim()

    if (!trimmed || isAsking) {
      return
    }

    setQuestion(trimmed)

    setSessions((current) =>
      current.map((session) =>
        session.id === activeSessionId
          ? {
              ...session,
              title:
                session.title === 'New conversation' ||
                session.title === 'Getting started'
                  ? trimmed.slice(0, 28)
                  : session.title,
              preview: trimmed,
            }
          : session,
      ),
    )

    setError('')
    setIsAsking(true)

    try {
      const response = await authFetch(
        `/api/v1/chat/sessions/${activeSessionId}/messages`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ message: trimmed }),
        },
      )

      if (!response.ok) {
        throw new Error('Query failed')
      }

      const responseData = await response.json()

      setAnswer({
        question: trimmed,
        answer: responseData.answer,
      })

      // Update session preview after getting response
      setSessions((current) =>
        current.map((session) =>
          session.id === activeSessionId
            ? {
                ...session,
                preview:
                  trimmed.substring(0, 50) +
                  (trimmed.length > 50 ? '...' : ''),
              }
            : session,
        ),
      )
    } catch (err: any) {
      setError(
        err.message ||
          'Could not reach the RAG API. Check that it is running at the configured API URL.',
      )
    } finally {
      setIsAsking(false)
    }
  }

  function handleAuthSubmit(e: React.FormEvent) {
    e.preventDefault()
    setIsAuthLoading(true)
    setError('')

    if (authMode === 'login') {
      login(authEmail, authPassword)
        .catch((err) => {
          setError('Login failed: ' + err.message)
        })
        .finally(() => setIsAuthLoading(false))
    } else {
      register(authEmail, authPassword)
        .catch((err) => {
          setError('Registration failed: ' + err.message)
        })
        .finally(() => setIsAuthLoading(false))
    }
  }

  // Initialize app on mount
  useEffect(() => {
    initializeApp()
  }, [user])

  if (!user && !isAuthModalOpen) {
    setIsAuthModalOpen(true)
  }

  return (
    <main className="rag-dark min-h-screen bg-[#0b1110] text-[#e8efeb]">
      {!user && isAuthModalOpen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-2xl border border-[#29463f] bg-[#111c1a] p-6">
            <div className="mb-6">
              <h2 className="text-lg font-semibold text-[#e8efeb]">
                {authMode === 'login'
                  ? 'Sign in to Context'
                  : 'Create an account'}
              </h2>

              <p className="mt-1 text-sm text-[#8ba69d]">
                {authMode === 'login'
                  ? 'Access your documents and conversations'
                  : 'Join the RAG workspace to get started'}
              </p>
            </div>

            <form onSubmit={handleAuthSubmit} className="space-y-4">
              <div>
                <label
                  htmlFor="authEmail"
                  className="mb-1 block text-sm font-medium text-[#dce9e4]"
                >
                  Email address
                </label>

                <input
                  id="authEmail"
                  type="email"
                  required
                  value={authEmail}
                  onChange={(e) => setAuthEmail(e.target.value)}
                  disabled={isAuthLoading}
                  className="block w-full rounded-xl border border-[#46786c] bg-[#142823] px-4 py-2 text-white placeholder:text-[#8ba69d] focus:border-[#84a79d] focus:ring-2 focus:ring-[#dce9e4] disabled:opacity-60"
                  placeholder="Enter your email"
                />
              </div>

              <div>
                <label
                  htmlFor="authPassword"
                  className="mb-1 block text-sm font-medium text-[#dce9e4]"
                >
                  Password
                </label>

                <input
                  id="authPassword"
                  type="password"
                  required
                  minLength={8}
                  value={authPassword}
                  onChange={(e) => setAuthPassword(e.target.value)}
                  disabled={isAuthLoading}
                  className="block w-full rounded-xl border border-[#46786c] bg-[#142823] px-4 py-2 text-white placeholder:text-[#8ba69d] focus:border-[#84a79d] focus:ring-2 focus:ring-[#dce9e4] disabled:opacity-60"
                  placeholder="Enter your password (8+ characters)"
                />
              </div>

              <button
                type="submit"
                disabled={
                  isAuthLoading ||
                  !(authEmail && authPassword.length >= 8)
                }
                className={`flex w-full items-center justify-center rounded-xl border border-transparent px-4 py-2 text-sm font-semibold transition-colors ${
                  isAuthLoading
                    ? 'cursor-not-allowed bg-[#4a5568]'
                    : 'bg-[#1d4c45] text-white hover:bg-[#286257]'
                }`}
              >
                {isAuthLoading ? (
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                ) : (
                  authMode === 'login' ? 'Sign in' : 'Create account'
                )}
              </button>
            </form>

            <div className="mt-4 text-center">
              <p className="text-xs text-[#8ba69d]">
                {authMode === 'login'
                  ? "Don't have an account? "
                  : 'Already have an account? '}
              </p>

              <button
                onClick={() =>
                  setAuthMode(
                    authMode === 'login' ? 'register' : 'login',
                  )
                }
                className="text-xs font-semibold text-[#84a79d] underline hover:text-[#dce9e4]"
              >
                {authMode === 'login' ? 'Sign up' : 'Sign in'}
              </button>
            </div>

            {error && (
              <div className="mt-4 rounded-xl border border-[#ebc9c2] bg-[#fff8f6] px-4 py-3 text-sm text-[#a34f42]">
                {error}
              </div>
            )}
          </div>
        </div>
      ) : (
        <>
          <div className="mx-auto flex min-h-screen max-w-[1440px]">
            <aside
              className={`hidden shrink-0 border-r border-[#293b38] bg-[#101917] py-5 text-[#dce9e4] transition-[width,padding] duration-200 md:flex md:flex-col ${
                isSidebarCollapsed
                  ? 'w-[76px] px-3'
                  : 'w-[270px] px-4'
              }`}
            >
              <div
                className={`mb-7 flex items-center gap-3 ${
                  isSidebarCollapsed ? 'justify-center' : 'px-2'
                }`}
              >
                <div className="flex size-9 shrink-0 items-center justify-center rounded-xl bg-[#2d8b76] text-white shadow-sm">
                  <Sparkles size={17} strokeWidth={2.3} />
                </div>

                {!isSidebarCollapsed && (
                  <div>
                    <p className="text-[15px] font-semibold tracking-[-0.02em]">
                      Context
                    </p>
                    <p className="text-[11px] text-[#7e9a91]">
                      RAG workspace
                    </p>
                  </div>
                )}
              </div>

              <button
                onClick={() =>
                  setIsSidebarCollapsed((collapsed) => !collapsed)
                }
                aria-label={
                  isSidebarCollapsed
                    ? 'Expand sidebar'
                    : 'Collapse sidebar'
                }
                title={
                  isSidebarCollapsed
                    ? 'Expand sidebar'
                    : 'Collapse sidebar'
                }
                className="mb-3 flex size-9 items-center justify-center self-end rounded-lg text-[#8eaaa0] transition hover:bg-[#1d302b] hover:text-white"
              >
                <PanelLeft size={17} />
              </button>

              <button
                onClick={createNewSession}
                aria-label="New conversation"
                title="New conversation"
                className={`mb-7 flex items-center gap-2 rounded-xl border border-[#31514a] bg-[#172622] px-3.5 py-2.5 text-sm font-medium shadow-sm transition hover:border-[#4d8777] hover:bg-[#1d302b] ${
                  isSidebarCollapsed
                    ? 'mx-auto size-10 justify-center p-0'
                    : ''
                }`}
              >
                <Plus size={16} />
                {!isSidebarCollapsed && 'New conversation'}
              </button>

              <div
                className={`mb-3 flex items-center justify-between ${
                  isSidebarCollapsed ? 'justify-center' : 'px-2'
                }`}
              >
                <p
                  className={
                    isSidebarCollapsed
                      ? 'sr-only'
                      : 'text-[10px] font-bold uppercase tracking-[0.14em] text-[#6f8c83]'
                  }
                >
                  Recent sessions
                </p>

                <MessageSquareText
                  size={14}
                  className="text-[#6f8c83]"
                />
              </div>

              <nav
                aria-label="Conversation sessions"
                className="flex flex-col gap-1 text-sm"
              >
                {sessions.map((session) => (
                  <button
                    key={session.id}
                    onClick={() => selectSession(session)}
                    aria-label={session.title}
                    title={
                      isSidebarCollapsed ? session.title : undefined
                    }
                    className={`flex w-full flex-col items-start rounded-xl px-3 py-2.5 text-left transition ${
                      isSidebarCollapsed ? 'items-center px-0' : ''
                    } ${
                      activeSessionId === session.id
                        ? 'bg-[#203b34] text-[#e4f2ed]'
                        : 'text-[#91aaa1] hover:bg-[#172622] hover:text-[#dce9e4]'
                    }`}
                  >
                    <MessageSquareText
                      size={16}
                      className={isSidebarCollapsed ? '' : 'hidden'}
                    />

                    <span
                      className={
                        isSidebarCollapsed
                          ? 'sr-only'
                          : 'w-full truncate font-medium'
                      }
                    >
                      {session.title}
                    </span>

                    <span
                      className={
                        isSidebarCollapsed
                          ? 'sr-only'
                          : 'mt-0.5 w-full truncate text-[11px] text-[#709088]'
                      }
                    >
                      {session.preview}
                    </span>
                  </button>
                ))}
              </nav>

              {!isSidebarCollapsed && (
                <div className="mt-auto rounded-2xl border border-[#293f3a] bg-[#14231f] p-4">
                  <div className="mb-3 flex items-center justify-between">
                    <span className="text-xs font-semibold">
                      API connection
                    </span>

                    <span className="size-2 rounded-full bg-[#73b597]" />
                  </div>

                  <p className="truncate text-[11px] text-[#7e9a91]">
                    {apiBase}
                  </p>
                </div>
              )}
            </aside>

            <section className="min-w-0 flex-1">
              <header className="flex h-[74px] items-center justify-between border-b border-[#dedfdb] px-5 sm:px-8">
                <div className="flex items-center gap-3">
                  <PanelLeft
                    className="text-[#69706b] md:hidden"
                    size={20}
                  />

                  <div>
                    <p className="bg-gradient-to-r from-[#2998df] via-[#4da8e6] to-[#9bc4d9] bg-clip-text text-sm font-bold text-transparent">
                      Knowledge base
                    </p>

                    <p className="text-xs text-[#858b85]">
                      Ask questions grounded in your files
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  <div className="flex items-center gap-2">
                    {user && (
                      <>
                        <span className="text-xs text-[#8ba69d]">
                          Signed in as:
                        </span>

                        <span className="text-xs font-semibold text-[#dce9e4]">
                          {user.email}
                        </span>
                      </>
                    )}

                    <button
                      onClick={logout}
                      aria-label="Sign out"
                      className="rounded-lg p-2 text-[#808680] hover:bg-white"
                    >
                      <X size={18} />
                    </button>
                  </div>

                  <button
                    aria-label="Help"
                    className="rounded-lg p-2 text-[#808680] hover:bg-white"
                  >
                    <CircleHelp size={18} />
                  </button>

                  <div className="flex size-8 items-center justify-center rounded-full bg-[#e4c9a6] text-xs font-bold text-[#725334]">
                    AA
                  </div>
                </div>
              </header>

              <div className="mx-auto max-w-[980px] px-5 py-9 sm:px-8 sm:py-12">
                <div className="mb-9">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-[0.16em] text-[#9b6d41]">
                    Document intelligence
                  </p>

                  <h1 className="max-w-2xl text-3xl font-semibold tracking-[-0.045em] text-[#2998df] sm:text-[42px] sm:leading-[1.05]">
                    Make sense of your
                    <br className="hidden sm:block" /> knowledge base.
                  </h1>

                  <p className="mt-4 max-w-xl text-[15px] leading-7 text-[#707771]">
                    Upload a document, then ask anything. Answers are
                    generated from the context your files provide.
                  </p>
                </div>

                <div className="grid gap-5 xl:grid-cols-[1fr_290px]">
                  <div className="space-y-5">
                    <div
                      id="ask"
                      className="rounded-2xl border border-[#dedfdb] bg-white p-4 shadow-[0_10px_30px_rgba(37,48,42,0.035)] sm:p-5"
                    >
                      <div className="mb-3 flex items-center justify-between">
                        <div className="flex items-center gap-2 text-sm font-semibold">
                          <Search
                            size={16}
                            className="text-[#9b6d41]"
                          />
                          Ask your documents
                        </div>

                        <div className="flex items-center gap-2">
                          <span className="hidden text-[11px] text-[#9ca39d] sm:inline">
                            Powered by retrieval
                          </span>

                          <button
                            onClick={() => setIsUploadOpen(true)}
                            disabled={isUploading}
                            aria-label="Upload a file"
                            title="Upload a file"
                            className="flex size-8 items-center justify-center rounded-lg bg-[#1d4c45] text-[#b8ded1] transition hover:bg-[#286257] disabled:opacity-60"
                          >
                            <Upload size={16} />
                          </button>
                        </div>
                      </div>

                      <textarea
                        value={question}
                        onChange={(event) =>
                          setQuestion(event.target.value)
                        }
                        onKeyDown={(event) => {
                          if (
                            event.key === 'Enter' &&
                            !event.shiftKey &&
                            !event.nativeEvent.isComposing &&
                            event.keyCode !== 229
                          ) {
                            event.preventDefault()
                            askQuestion()
                          }
                        }}
                        placeholder="What would you like to know?"
                        rows={3}
                        className="w-full resize-none rounded-xl border border-[#e1e4df] bg-[#fafbf9] p-3.5 text-[15px] outline-none placeholder:text-[#a8aea8] focus:border-[#84a79d] focus:ring-2 focus:ring-[#dce9e4]"
                      />

                      <div className="mt-3 flex items-center justify-between gap-3">
                        <p className="hidden text-xs text-[#929992] sm:block">
                          Press Enter to ask · Shift + Enter for a new line
                        </p>

                        <button
                          onClick={() => askQuestion()}
                          disabled={
                            !question.trim() ||
                            isAsking ||
                            !activeSessionId
                          }
                          className="ml-auto inline-flex items-center gap-2 rounded-xl bg-[#1d4c45] px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-[#163c37] disabled:cursor-not-allowed disabled:opacity-45"
                        >
                          {isAsking ? (
                            <Loader2
                              className="animate-spin"
                              size={16}
                            />
                          ) : (
                            <ArrowUp size={16} />
                          )}
                          Ask question
                        </button>
                      </div>
                    </div>

                    {!answer && !isAsking && (
                      <div className="rounded-2xl border border-dashed border-[#d5dad4] bg-[#fbfcfa] p-5">
                        <div className="mb-4 flex items-center gap-2 text-sm font-semibold">
                          <Sparkles
                            size={16}
                            className="text-[#9b6d41]"
                          />
                          Try a starter question
                        </div>

                        <div className="flex flex-wrap gap-2">
                          {starterQuestions.map((item) => (
                            <button
                              key={item}
                              onClick={() => askQuestion(item)}
                              className="rounded-full border border-[#dce1da] bg-white px-3.5 py-2 text-xs text-[#69716b] transition hover:border-[#9bb5ae] hover:text-[#1d4c45]"
                            >
                              {item}
                            </button>
                          ))}
                        </div>
                      </div>
                    )}

                    {(answer || isAsking) && (
                      <div className="rounded-2xl border border-[#dedfdb] bg-white p-5 sm:p-6">
                        <div className="mb-5 flex items-center justify-between">
                          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-[0.12em] text-[#9b6d41]">
                            <MessageSquareText size={15} />
                            Answer
                          </div>

                          {answer && (
                            <button
                              onClick={() => setAnswer(null)}
                              aria-label="Close answer"
                              className="text-[#9aa09a] hover:text-[#303733]"
                            >
                              <X size={17} />
                            </button>
                          )}
                        </div>

                        {isAsking ? (
                          <div className="space-y-3">
                            <div className="h-4 w-4/5 animate-pulse rounded bg-[#edf0ec]" />
                            <div className="h-4 w-full animate-pulse rounded bg-[#edf0ec]" />
                            <div className="h-4 w-2/3 animate-pulse rounded bg-[#edf0ec]" />
                          </div>
                        ) : (
                          <>
                            <p className="mb-4 text-sm italic text-[#838b84]">
                              “{answer?.question}”
                            </p>

                            <p className="whitespace-pre-wrap text-[16px] leading-8 text-[#303733]">
                              {answer?.answer}
                            </p>

                            <div className="mt-6 flex items-center gap-2 border-t border-[#edf0ea] pt-4 text-xs text-[#8c938d]">
                              <Check
                                size={14}
                                className="text-[#5e927d]"
                              />
                              Grounded in your indexed documents
                            </div>
                          </>
                        )}
                      </div>
                    )}

                    {error && (
                      <div
                        role="alert"
                        className="rounded-xl border border-[#ebc9c2] bg-[#fff8f6] px-4 py-3 text-sm text-[#a34f42]"
                      >
                        {error}
                      </div>
                    )}
                  </div>

                  <div className="border-l border-[#dedfdb] pl-6">
                    <div className="mb-5">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#9b6d41]">
                        Your documents
                      </p>

                      {documents.length === 0 ? (
                        <p className="text-sm text-[#8ba69d]">
                          No documents uploaded yet. Upload a file to
                          get started.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {documents.map((doc) => (
                            <div
                              key={doc.id}
                              className={`flex items-center justify-between rounded-xl border border-[#e1e4df] bg-white px-3 py-2 ${
                                selectedDocumentId === doc.id ? 'border-[#4ade80] bg-[#dcfce7]' : ''
                              }`}
                              onClick={() => {
                                if (selectedDocumentId === doc.id) {
                                  setSelectedDocumentId(null);
                                } else {
                                  setSelectedDocumentId(doc.id);
                                }
                              }}
                            >
                              <div className="flex items-center gap-3">
                                <div className="flex size-8 items-center justify-center rounded-full bg-[#dce9e4]/20 text-xs">
                                  {doc.status === 'ready'
                                    ? '✓'
                                    : doc.status === 'indexing'
                                      ? '⟳'
                                      : '✗'}
                                </div>

                                <div>
                                  <p className="text-sm font-medium">
                                    {doc.name}
                                  </p>

                                  <p className="text-xs text-[#8ba69d]">
                                    {doc.size}
                                  </p>
                                </div>
                              </div>

                              <span
                                className={`rounded px-2 py-0.5 text-xs ${
                                  doc.status === 'ready'
                                    ? 'bg-[#16302e] text-[#4ade80]'
                                    : doc.status === 'indexing'
                                      ? 'bg-[#1e293b] text-[#fbbf24]'
                                      : 'bg-[#16302e] text-[#f87171]'
                                }`}
                              >
                                {doc.status}
                              </span>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    <div className="mt-6">
                      <p className="mb-2 text-xs font-semibold uppercase tracking-[0.16em] text-[#9b6d41]">
                        Conversation history
                      </p>

                      {sessions.length === 0 ? (
                        <p className="text-sm text-[#8ba69d]">
                          No conversations yet. Start a new conversation
                          to begin chatting.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {sessions.map((session) => (
                            <button
                              key={session.id}
                              onClick={() => selectSession(session)}
                              className={`flex w-full items-center justify-between rounded-xl border border-transparent px-3 py-2 ${
                                activeSessionId === session.id
                                  ? 'bg-[#203b34] text-[#e4f2ed]'
                                  : 'text-[#91aaa1] hover:bg-[#172622] hover:text-[#dce9e4]'
                              }`}
                            >
                              <div className="min-w-0 flex-1">
                                <p className="line-clamp-1 text-sm font-medium">
                                  {session.title}
                                </p>

                                <p className="line-clamp-1 text-xs text-[#8ba69d]">
                                  {session.preview}
                                </p>
                              </div>

                              <div className="flex size-6 items-center justify-center text-xs">
                                {activeSessionId === session.id ? (
                                  <div className="flex size-5 items-center justify-center rounded-full bg-[#4ade80]/20 text-xs">
                                    ●
                                  </div>
                                ) : (
                                  <CircleHelp
                                    size={10}
                                    className="opacity-50"
                                  />
                                )}
                              </div>
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            </section>
          </div>

          {isUploadOpen && (
            <div
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-5"
              role="dialog"
              aria-modal="true"
              aria-labelledby="upload-title"
              onMouseDown={(event) => {
                if (event.target === event.currentTarget) {
                  setIsUploadOpen(false)
                }
              }}
            >
              <div className="w-full max-w-md rounded-2xl border border-[#29463f] bg-[#111c1a] p-6 shadow-2xl">
                <div className="mb-5 flex items-start justify-between">
                  <div>
                    <h2
                      id="upload-title"
                      className="text-lg font-semibold text-[#e8efeb]"
                    >
                      Add to your knowledge base
                    </h2>

                    <p className="mt-1 text-sm text-[#8ba69d]">
                      Choose a file to index and ask questions about.
                    </p>
                  </div>

                  <button
                    aria-label="Close upload dialog"
                    onClick={() => setIsUploadOpen(false)}
                    className="rounded-lg p-1 text-[#78938a] hover:bg-[#1d302b] hover:text-white"
                  >
                    <X size={18} />
                  </button>
                </div>

                <button
                  onClick={() => fileInputRef.current?.click()}
                  disabled={isUploading}
                  className="flex w-full flex-col items-center justify-center rounded-xl border border-dashed border-[#46786c] bg-[#142823] px-4 py-10 text-center transition hover:bg-[#1b352e] disabled:opacity-60"
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".pdf,.txt,.doc,.docx"
                    className="hidden"
                    onChange={(event) => {
                      const file = event.target.files?.[0]

                      if (file) {
                        uploadFile(file)
                        setIsUploadOpen(false)
                      }

                      event.currentTarget.value = ''
                    }}
                  />

                  {isUploading ? (
                    <Loader2
                      className="mb-3 animate-spin text-[#9ed2c2]"
                      size={24}
                    />
                  ) : (
                    <Upload
                      className="mb-3 text-[#9ed2c2]"
                      size={24}
                    />
                  )}

                  <span className="text-sm font-semibold text-[#c5e6db]">
                    Click to choose a file
                  </span>

                  <span className="mt-1 text-xs text-[#78938a]">
                    PDF, DOCX or TXT
                  </span>
                </button>
              </div>
            </div>
          )}
        </>
      )}
    </main>
  )
}

function formatBytes(bytes: number) {
  if (bytes < 1024 * 1024) {
    return `${Math.max(1, Math.round(bytes / 1024))} KB`
  }

  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}