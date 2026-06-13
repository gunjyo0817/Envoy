import StepBar from '../components/StepBar'

const STATUS_MSG: Record<string, string> = {
  searching: 'Searching across Kleinanzeigen, Vinted and more...',
  reviewing: 'Extracting and structuring listings...',
  negotiating: 'Negotiating with the seller...',
  coordinating: 'Planning your meetup...',
}

export default function ProcessingScreen({ status }: { status?: string }) {
  const msg = STATUS_MSG[status ?? 'searching'] ?? 'Working on it...'
  return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md text-center">
        <div className="text-3xl mb-4 animate-bounce">🤖</div>
        <div className="text-lg font-bold text-slate-800 mb-2">Agents are working</div>
        <div className="text-sm text-slate-500 mb-6">{msg}</div>
        <div className="h-1.5 bg-slate-100 rounded-full overflow-hidden">
          <div className="h-full bg-indigo-500 rounded-full animate-pulse w-3/4" />
        </div>
        <div className="mt-6">
          <StepBar status={status} />
        </div>
      </div>
    </div>
  )
}
