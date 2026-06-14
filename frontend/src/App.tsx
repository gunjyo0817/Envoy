import { useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import InputScreen from './screens/InputScreen'
import ProcessingScreen from './screens/ProcessingScreen'
import ChooseScreen from './screens/ChooseScreen'
import NegotiateScreen from './screens/NegotiateScreen'
import MeetupScreen from './screens/MeetupScreen'
import DoneScreen from './screens/DoneScreen'
import AgentView from './admin/AgentView'
import AuthScreen from './screens/AuthScreen'
import SettingsScreen from './screens/SettingsScreen'
import HistoryScreen from './screens/HistoryScreen'
import { useSession } from './useSession'
import { useAuth } from './auth/AuthProvider'

function BuyerFlow() {
  const { user } = useAuth()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const { state, sendFeedback } = useSession(sessionId)

  if (!user) return <AuthScreen />
  if (!sessionId) return <InputScreen onStart={setSessionId} />

  const status = state?.status
  if (!status || status === 'searching' || status === 'reviewing') {
    return <ProcessingScreen status={status} />
  }
  if (status === 'awaiting_human') {
    const cp = state?.pending_decision?.checkpoint
    if (cp === 'confirm_candidate') return <ChooseScreen state={state} onFeedback={sendFeedback} />
    if (cp === 'confirm_offer') return <NegotiateScreen state={state} onFeedback={sendFeedback} />
    if (cp === 'confirm_meetup') return <MeetupScreen state={state} onFeedback={sendFeedback} sessionId={sessionId!} />
  }
  if (status === 'awaiting_seller') {
    return <ProcessingScreen status={status} />
  }
  if (status === 'negotiating' || status === 'coordinating') {
    return <ProcessingScreen status={status} />
  }
  if (status === 'done') return <DoneScreen state={state} sessionId={sessionId!} />
  return <ProcessingScreen status={status} />
}

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<BuyerFlow />} />
      <Route path="/settings" element={<SettingsScreen />} />
      <Route path="/history" element={<HistoryScreen />} />
      <Route path="/admin" element={<AgentView />} />
    </Routes>
  )
}
