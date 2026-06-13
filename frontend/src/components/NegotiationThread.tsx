import type { NegotiationMessage } from '../api'
import { useI18n } from '../i18n/I18nProvider'
import { useMessageTranslation } from '../i18n/useMessageTranslation'

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

function MessageBubble({
  msg,
  isBuyer,
  showSender,
  onTheTable,
  lang,
}: {
  msg: NegotiationMessage
  isBuyer: boolean
  showSender: boolean
  onTheTable: boolean
  lang: string
}) {
  const translation = useMessageTranslation(msg.text, lang, !isBuyer && lang !== 'de')

  return (
    <li className={`flex flex-col ${isBuyer ? 'items-end' : 'items-start'}`}>
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
        {translation && (
          <p className="mt-1 text-xs italic text-[var(--color-ink-muted)]">{translation}</p>
        )}
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
}

export default function NegotiationThread({ thread }: { thread: NegotiationMessage[] }) {
  const { lang } = useI18n()
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
          <MessageBubble
            key={i}
            msg={msg}
            isBuyer={isBuyer}
            showSender={showSender}
            onTheTable={onTheTable}
            lang={lang}
          />
        )
      })}
    </ol>
  )
}
