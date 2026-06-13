import type { Candidate } from '../api'

interface Props { candidate: Candidate; rank: number; selected?: boolean; onClick?: () => void }

const CONDITION_LABEL: Record<string, string> = {
  new: 'New', like_new: 'Like New', very_good: 'Very Good',
  good: 'Good', acceptable: 'Acceptable',
}

export default function ListingCard({ candidate, rank, selected, onClick }: Props) {
  return (
    <div onClick={onClick}
      className={`border-2 rounded-xl p-4 cursor-pointer transition-all
        ${selected ? 'border-indigo-500 bg-indigo-50' : 'border-slate-200 hover:border-indigo-300'}`}>
      <div className="flex gap-3">
        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-xs font-black shrink-0
          ${rank === 0 ? 'bg-indigo-600 text-white' : 'bg-slate-200 text-slate-500'}`}>
          {rank + 1}
        </div>
        <div className="text-2xl">📱</div>
        <div className="flex-1 min-w-0">
          <div className="font-semibold text-slate-800 text-sm truncate">{candidate.title}</div>
          <div className="flex items-baseline gap-2 mt-0.5">
            <span className="text-xl font-black text-emerald-600">€{candidate.price_eur}</span>
            {candidate.score >= 85 && (
              <span className="text-xs bg-emerald-100 text-emerald-700 px-2 py-0.5 rounded-full font-semibold">
                Great deal
              </span>
            )}
          </div>
          <div className="flex gap-3 mt-1 text-xs text-slate-400 flex-wrap">
            {candidate.seller_rating && <span>⭐ {candidate.seller_rating}</span>}
            <span>📍 {candidate.location}</span>
            <span className="capitalize">{CONDITION_LABEL[candidate.condition] ?? candidate.condition}</span>
          </div>
          {candidate.insight && (
            <div className="mt-2 text-xs text-indigo-700 bg-indigo-50 px-3 py-1.5 rounded-lg">
              💡 {candidate.insight}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
