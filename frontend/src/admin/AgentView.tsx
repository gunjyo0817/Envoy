import { useState } from 'react'
import { useSession, type AgentLogEntry } from '../useSession'
import { createSession } from '../api'

const TOOL_BADGE: Record<string, { label: string; color: string }> = {
  search:    { label: 'TAVILY',   color: 'bg-sky-900 text-sky-300' },
  extract:   { label: 'PIONEER',  color: 'bg-purple-900 text-purple-300' },
  analyst:   { label: 'GEMINI',   color: 'bg-emerald-900 text-emerald-300' },
  negotiate: { label: 'GEMINI',   color: 'bg-emerald-900 text-emerald-300' },
  coordinate:{ label: 'GEMINI',   color: 'bg-emerald-900 text-emerald-300' },
  orchestrator: { label: 'SYSTEM', color: 'bg-slate-700 text-slate-400' },
}

export default function AgentView() {
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { state, logs } = useSession(sessionId)

  const start = async () => {
    const id = await createSession({
      query: 'iPhone 14', budget: 200,
      condition: 'good+', location: 'München', max_distance_km: 15,
    })
    setSessionId(id)
  }

  return (
    <div className="min-h-screen bg-slate-900 text-slate-100 font-mono p-6">
      <div className="max-w-3xl mx-auto">
        <div className="flex items-center justify-between mb-6">
          <div>
            <div className="text-indigo-400 font-bold text-xl">buybot / agent view</div>
            <div className="text-slate-500 text-xs mt-0.5">internal · for demo purposes</div>
          </div>
          {!sessionId && (
            <button onClick={start}
              className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-bold">
              Run demo
            </button>
          )}
          {state?.status && (
            <span className="bg-slate-800 text-slate-300 px-3 py-1 rounded-full text-xs">
              status: {state.status}
            </span>
          )}
        </div>

        {state?.degraded && state.degraded.length > 0 && (
          <div className="bg-yellow-900/40 border border-yellow-600 rounded-lg px-4 py-2 mb-4 text-yellow-300 text-xs">
            ⚠ Degraded: {state.degraded.join(' · ')}
          </div>
        )}

        <div className="space-y-2">
          {logs.map((log: AgentLogEntry, i: number) => {
            const badge = TOOL_BADGE[log.agent] ?? TOOL_BADGE.orchestrator
            return (
              <div key={i} className="flex gap-3 items-start bg-slate-800/50 rounded-lg px-3 py-2">
                <span className={`shrink-0 px-2 py-0.5 rounded text-xs font-bold ${badge.color}`}>
                  {badge.label}
                </span>
                <span className="text-slate-300 text-sm flex-1">{log.msg}</span>
                <span className="text-slate-600 text-xs shrink-0">
                  {new Date(log.ts).toLocaleTimeString()}
                </span>
              </div>
            )
          })}
          {logs.length === 0 && (
            <div className="text-slate-600 text-sm py-8 text-center">
              Click "Run demo" to start the agent pipeline
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
