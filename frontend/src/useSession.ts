import { useState, useEffect, useRef, useCallback } from 'react'
import { getState, postFeedback, connectWS, SessionState, WsEvent } from './api'

export interface AgentLogEntry {
  agent: string
  msg: string
  ts: number
}

export function useSession(sessionId: string | null) {
  const [state, setState] = useState<SessionState | null>(null)
  const [logs, setLogs] = useState<AgentLogEntry[]>([])
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const refresh = useCallback(async () => {
    if (!sessionId) return
    const s = await getState(sessionId)
    setState(s)
  }, [sessionId])

  const sendFeedback = useCallback(async (choice: string, freeText?: string) => {
    if (!sessionId) return
    await postFeedback(sessionId, choice, freeText)
    await refresh()
  }, [sessionId, refresh])

  useEffect(() => {
    if (!sessionId) return
    refresh()
    pollRef.current = setInterval(refresh, 2000)

    const disconnect = connectWS(sessionId, (e: WsEvent) => {
      if (e.event === 'state_changed') refresh()
      if (e.event === 'agent_log') {
        setLogs(prev => [...prev, {
          agent: e.agent ?? 'system',
          msg: e.msg ?? '',
          ts: Date.now(),
        }])
      }
    })

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      disconnect()
    }
  }, [sessionId, refresh])

  return { state, logs, sendFeedback, refresh }
}
