import type { NegotiationMessage } from '../api'

const ACT_LABEL: Record<string, string> = {
  initial_offer: 'Opening offer', counter_offer: 'Counter', accept: '✅ Accepted',
  reject: '❌ Rejected', question: 'Question', stall: 'Stalling...',
}

export default function NegotiationThread({ thread }: { thread: NegotiationMessage[] }) {
  return (
    <div className="space-y-2 px-4 py-3">
      {thread.map((msg, i) => (
        <div key={i} className={`flex ${msg.role === 'buyer' ? 'justify-end' : 'justify-start'}`}>
          <div className={`max-w-xs rounded-2xl px-4 py-2.5 text-sm
            ${msg.role === 'buyer'
              ? 'bg-indigo-600 text-white rounded-br-sm'
              : 'bg-slate-100 text-slate-800 rounded-bl-sm'}`}>
            <div>{msg.text}</div>
            <div className={`text-xs mt-1 opacity-70`}>
              {ACT_LABEL[msg.act] ?? msg.act}
              {msg.price != null && ` · €${msg.price}`}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
