import { useState } from 'react'
import { createSession } from '../api'

interface Props { onStart: (sessionId: string) => void }

export default function InputScreen({ onStart }: Props) {
  const [query, setQuery] = useState('')
  const [budget, setBudget] = useState(200)
  const [condition, setCondition] = useState('good+')
  const [location, setLocation] = useState('München')
  const [loading, setLoading] = useState(false)

  const handleSubmit = async () => {
    if (!query.trim()) return
    setLoading(true)
    const id = await createSession({ query, budget, condition, location, max_distance_km: 15 })
    onStart(id)
  }

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-2xl shadow-lg p-8 w-full max-w-md">
        <div className="text-2xl font-black text-indigo-600 tracking-tight mb-1">buybot</div>
        <div className="text-slate-500 text-sm mb-6">Tell me what you want to buy</div>

        <div className="space-y-4">
          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">What are you looking for?</label>
            <input
              className="mt-1 w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              placeholder="e.g. iPhone 14, Sony A7III, MacBook Air..."
              value={query} onChange={e => setQuery(e.target.value)}
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">
              Max budget: <span className="text-indigo-600">€{budget}</span>
            </label>
            <input type="range" min={50} max={2000} step={10} value={budget}
              onChange={e => setBudget(Number(e.target.value))}
              className="w-full mt-2 accent-indigo-500"
            />
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Minimum condition</label>
            <select value={condition} onChange={e => setCondition(e.target.value)}
              className="mt-1 w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400">
              <option value="acceptable">Acceptable</option>
              <option value="good">Good</option>
              <option value="good+">Good+</option>
              <option value="very_good">Very Good</option>
              <option value="like_new">Like New</option>
            </select>
          </div>

          <div>
            <label className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Your city</label>
            <input
              className="mt-1 w-full border border-slate-200 rounded-xl px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-400"
              value={location} onChange={e => setLocation(e.target.value)}
            />
          </div>

          <button onClick={handleSubmit} disabled={loading || !query.trim()}
            className="w-full bg-indigo-600 hover:bg-indigo-700 disabled:bg-slate-200 text-white
              font-bold py-4 rounded-xl transition-colors text-sm mt-2">
            {loading ? 'Starting agents...' : '🤖 Find me the best deal →'}
          </button>
        </div>
      </div>
    </div>
  )
}
