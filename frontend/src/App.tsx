import { useState, useEffect } from 'react'
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom'
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
import AppShell from './screens/AppShell'
import OnboardingWizard from './screens/OnboardingWizard'
import { useSession } from './useSession'
import { useAuth } from './auth/AuthProvider'

// BuyerFlow stays exactly as it is today (search → … → done) — used as the Search tab.
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
  if (status === 'awaiting_seller') return <ProcessingScreen status={status} />
  if (status === 'negotiating' || status === 'coordinating') return <ProcessingScreen status={status} />
  if (status === 'done') return <DoneScreen state={state} sessionId={sessionId!} />
  return <ProcessingScreen status={status} />
}

// Redirects authenticated-but-not-onboarded users into the wizard.
function OnboardingGate() {
  const { user } = useAuth()
  const navigate = useNavigate()
  useEffect(() => {
    if (user && user.onboarded === false) navigate('/onboarding', { replace: true })
  }, [user, navigate])
  return null
}

export default function App() {
  const { user } = useAuth()
  if (!user) return <AuthScreen />

  return (
    <>
      <OnboardingGate />
      <Routes>
        <Route path="/onboarding" element={<OnboardingWizard />} />
        <Route element={<AppShell />}>
          <Route path="/search" element={<BuyerFlow />} />
          <Route path="/deals" element={<HistoryScreen />} />
          <Route path="/me" element={<SettingsScreen />} />
        </Route>
        <Route path="/admin" element={<AgentView />} />
        {/* legacy redirects */}
        <Route path="/" element={<Navigate to="/search" replace />} />
        <Route path="/history" element={<Navigate to="/deals" replace />} />
        <Route path="/settings" element={<Navigate to="/me" replace />} />
        <Route path="*" element={<Navigate to="/search" replace />} />
      </Routes>
    </>
  )
}
