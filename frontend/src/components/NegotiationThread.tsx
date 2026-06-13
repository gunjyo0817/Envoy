import type { NegotiationMessage } from '../api'

const ACT_LABEL: Record<string, string> = {
  initial_offer: 'Opening offer',
  counter_offer: 'Counter-offer',
  accept: 'Accepted',
  reject: 'Declined',
  question: 'Question',
  stall: 'Holding out',
}

function actTone(act: string): string {
  if (act === 'accept') return 'text-[var(--color-primary)]'
  if (act === 'reject') return 'text-[var(--color-danger)]'
  return ''
}

export default function NegotiationThread({ thread }: { thread: NegotiationMessage[] }) {
  return (
    <ol className="space-y-3">
      {thread.map((msg, i) => {
        const isBuyer = msg.role === 'buyer'
        const prevRole = i > 0 ? thread[i - 1].role : null
        const showSender = msg.role !== prevRole
        const isLatest = i === thread.length - 1
        // The seller's standing counter is the offer the human is deciding on.
        const onTheTable = isLatest && !isBuyer && msg.act === 'counter_offer'

        return (
          <li key={i} className={`flex flex-col ${isBuyer ? 'items-end' : 'items-start'}`}>
            {showSender && (
              <span className="mb-1 px-1 text-xs font-medium text-[var(--color-ink-faint)]">
                {isBuyer ? 'Your agent' : 'Seller'}
              </span>
            )}
            <div
              className={[
                'max-w-[85%] rounded-2xl px-4 py-2.5',
                isBuyer
                  ? 'rounded-br-md bg-[var(--color-primary)] text-[var(--color-primary-text)]'
                  : 'rounded-bl-md bg-[var(--color-surface-raised)] text-[var(--color-ink)]',
                onTheTable ? 'ring-2 ring-[var(--color-accent)]' : '',
              ].join(' ')}
            >
              <p className="text-sm leading-relaxed">{msg.text}</p>
              <p
                className={`mt-1 text-xs font-medium ${
                  isBuyer ? 'text-[oklch(1_0_0_/_0.8)]' : actTone(msg.act) || 'text-[var(--color-ink-muted)]'
                }`}
              >
                {ACT_LABEL[msg.act] ?? msg.act}
                {msg.price != null && (
                  <span className="tabular-nums"> · €{msg.price}</span>
                )}
              </p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}
