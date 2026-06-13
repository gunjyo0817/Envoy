import { useState, useEffect, useRef } from 'react'
import { useSession, type AgentLogEntry } from '../useSession'
import { createSession } from '../api'

const MONO = '"JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace'

interface Tool {
  label: string
  text: string
  chip: string
}

const TAVILY: Tool = { label: 'TAVILY', text: 'oklch(0.70 0.15 150)', chip: 'oklch(0.54 0.165 150 / 0.16)' }
const PIONEER: Tool = { label: 'PIONEER', text: 'oklch(0.80 0.15 60)', chip: 'oklch(0.75 0.16 60 / 0.16)' }
const GEMINI: Tool = { label: 'GEMINI', text: 'oklch(0.74 0.13 280)', chip: 'oklch(0.62 0.12 280 / 0.16)' }
const SYSTEM: Tool = { label: 'SYSTEM', text: 'var(--color-ink-muted)', chip: 'var(--color-surface-raised)' }

const TOOL_BY_AGENT: Record<string, Tool> = {
  search: TAVILY,
  extract: PIONEER,
  analyst: GEMINI,
  negotiate: GEMINI,
  coordinate: GEMINI,
  orchestrator: SYSTEM,
}

interface AgentDef {
  key: string
  name: string
  tool: Tool
  role: string
}

const PIPELINE: AgentDef[] = [
  { key: 'search', name: 'Search', tool: TAVILY, role: 'live market scan' },
  { key: 'extract', name: 'Extract', tool: PIONEER, role: 'listing → schema' },
  { key: 'analyst', name: 'Analyst', tool: GEMINI, role: 'score & rank' },
  { key: 'negotiate', name: 'Negotiate', tool: GEMINI, role: 'offer strategy' },
  { key: 'coordinate', name: 'Coordinate', tool: GEMINI, role: 'meetup & route' },
]

const STATUS_INDEX: Record<string, number> = {
  searching: 0,
  reviewing: 1,
  negotiating: 3,
  coordinating: 4,
  done: 5,
}
const CHECKPOINT_INDEX: Record<string, number> = {
  confirm_candidate: 2,
  confirm_offer: 3,
  confirm_meetup: 4,
}

function ToolBadge({ tool }: { tool: Tool }) {
  return (
    <span
      className="rounded px-1.5 py-0.5 text-[11px] font-medium tracking-wide"
      style={{ color: tool.text, backgroundColor: tool.chip }}
    >
      {tool.label}
    </span>
  )
}

interface ConsoleProps {
  status?: string
  checkpoint?: string
  logs: AgentLogEntry[]
  degraded: string[]
  sessionId: string | null
  starting: boolean
  onStart: () => void
}

export function AgentConsole({ status, checkpoint, logs, degraded, sessionId, starting, onStart }: ConsoleProps) {
  const feedRef = useRef<HTMLDivElement>(null)

  // Auto-scroll the log feed to the newest entry.
  useEffect(() => {
    feedRef.current?.scrollTo({ top: feedRef.current.scrollHeight })
  }, [logs])

  let activeIndex = status ? STATUS_INDEX[status] ?? -1 : -1
  if (status === 'awaiting_human') {
    activeIndex = checkpoint ? CHECKPOINT_INDEX[checkpoint] ?? 0 : 0
  }
  const failed = status === 'failed'

  return (
    <div className="min-h-dvh bg-[var(--color-bg)] px-5 py-8 text-[var(--color-ink)] sm:px-8" style={{ fontFamily: MONO }}>
      <div className="mx-auto max-w-4xl lg:max-w-5xl">
        {/* Header */}
        <header className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="flex items-center gap-2.5">
              <span className="text-base font-semibold tracking-tight">Envoy</span>
              <span className="rounded bg-[var(--color-surface-raised)] px-1.5 py-0.5 text-[11px] font-medium text-[var(--color-ink-muted)]">
                AGENT VIEW
              </span>
            </div>
            <p className="mt-1 text-xs text-[var(--color-ink-faint)]">Live multi-agent activity · internal</p>
          </div>
          <div className="flex items-center gap-3">
            {status && (
              <span className="flex items-center gap-2 rounded-full bg-[var(--color-surface)] px-3 py-1.5 text-xs">
                <span
                  className={`h-1.5 w-1.5 rounded-full ${
                    failed ? 'bg-[var(--color-danger)]' : status === 'done' ? 'bg-[var(--color-primary)]' : 'animate-pulse bg-[var(--color-primary)]'
                  }`}
                />
                <span className="text-[var(--color-ink-muted)]">{status}</span>
              </span>
            )}
            <button
              type="button"
              onClick={onStart}
              disabled={starting}
              className="cursor-pointer rounded-lg bg-[var(--color-primary)] px-4 py-2 text-sm font-semibold text-[var(--color-primary-text)] transition-[filter,transform] duration-150 hover:brightness-110 active:scale-[0.98] active:brightness-95 disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:brightness-100 disabled:active:scale-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--color-primary)]"
            >
              {starting ? 'Starting…' : sessionId ? 'Restart' : 'Run demo'}
            </button>
          </div>
        </header>

        {/* Agent pipeline roster — the partner-tool story */}
        <section className="mt-7 grid grid-cols-2 gap-2.5 sm:grid-cols-5" aria-label="Agent pipeline">
          {PIPELINE.map((agent, i) => {
            const isActive = i === activeIndex && !failed
            const isDone = i < activeIndex || status === 'done'
            return (
              <div
                key={agent.key}
                className="rounded-xl border bg-[var(--color-surface)] p-3"
                style={{
                  borderColor: isActive ? 'var(--color-primary)' : 'var(--color-border)',
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="text-sm font-semibold text-[var(--color-ink)]">{agent.name}</span>
                  {isActive ? (
                    <span className="relative flex h-2 w-2" aria-label="active">
                      <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-[var(--color-primary)] opacity-75" />
                      <span className="relative inline-flex h-2 w-2 rounded-full bg-[var(--color-primary)]" />
                    </span>
                  ) : isDone ? (
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="var(--color-primary)" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-label="done">
                      <path d="M5 13l4 4L19 7" />
                    </svg>
                  ) : (
                    <span className="h-2 w-2 rounded-full bg-[var(--color-border)]" aria-label="idle" />
                  )}
                </div>
                <p className="mt-1 text-[11px] text-[var(--color-ink-faint)]">{agent.role}</p>
                <div className="mt-2.5">
                  <ToolBadge tool={agent.tool} />
                </div>
              </div>
            )
          })}
        </section>

        {/* Degraded fallbacks — robustness talking point */}
        {degraded.length > 0 && (
          <div
            className="mt-4 flex items-start gap-2.5 rounded-lg border border-[var(--color-accent-dim)] bg-[oklch(0.14_0.025_60)] px-4 py-2.5 text-xs"
            role="status"
          >
            <svg className="mt-0.5 shrink-0 text-[var(--color-accent)]" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
              <path d="M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0Z" />
              <path d="M12 9v4M12 17h.01" />
            </svg>
            <span className="text-[var(--color-ink)]">
              <span className="text-[var(--color-accent)]">Graceful fallback active:</span>{' '}
              {degraded.join(' · ')}
            </span>
          </div>
        )}

        {/* Live log feed */}
        <div
          ref={feedRef}
          className="mt-4 max-h-[58vh] overflow-y-auto rounded-xl border border-[var(--color-border)] bg-[var(--color-surface)] p-3"
        >
          {logs.length === 0 ? (
            <p className="py-12 text-center text-sm text-[var(--color-ink-faint)]">
              {sessionId ? 'Waiting for agent activity…' : 'Press “Run demo” to start the pipeline.'}
            </p>
          ) : (
            <ol className="space-y-1">
              {logs.map((log: AgentLogEntry, i: number) => {
                const tool = TOOL_BY_AGENT[log.agent] ?? SYSTEM
                return (
                  <li key={i} className="flex items-start gap-3 rounded px-2 py-1.5 text-[13px] leading-relaxed hover:bg-[var(--color-surface-raised)]">
                    <span className="shrink-0 tabular-nums text-[var(--color-ink-faint)]">
                      {new Date(log.ts).toLocaleTimeString('en-GB')}
                    </span>
                    <span className="shrink-0">
                      <ToolBadge tool={tool} />
                    </span>
                    <span className="text-[var(--color-ink-muted)]">{log.msg}</span>
                  </li>
                )
              })}
            </ol>
          )}
        </div>
      </div>
    </div>
  )
}

export default function AgentView() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [starting, setStarting] = useState(false)
  const { state, logs } = useSession(sessionId)

  const start = async () => {
    setStarting(true)
    try {
      const id = await createSession({
        query: 'iPhone 14',
        budget_min: 50,
        budget_max: 200,
        condition: 'good+',
        location: 'München',
        max_distance_km: 15,
      })
      setSessionId(id)
    } finally {
      setStarting(false)
    }
  }

  return (
    <AgentConsole
      status={state?.status}
      checkpoint={state?.pending_decision?.checkpoint}
      logs={logs}
      degraded={state?.degraded ?? []}
      sessionId={sessionId}
      starting={starting}
      onStart={start}
    />
  )
}
