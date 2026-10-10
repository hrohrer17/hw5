// Renders agent text with the little markdown they use (**bold**, "- " bullets) without injecting HTML.
import type { ReactNode } from 'react'

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
    part.startsWith('**') && part.endsWith('**') ? <strong key={i}>{part.slice(2, -2)}</strong> : part,
  )
}

export function RichText({ text }: { text: string }) {
  const blocks: ReactNode[] = []
  let bullets: string[] = []
  const flush = () => {
    if (bullets.length) {
      blocks.push(<ul key={`u${blocks.length}`}>{bullets.map((b, i) => <li key={i}>{inline(b)}</li>)}</ul>)
      bullets = []
    }
  }
  for (const raw of text.split('\n')) {
    const line = raw.trimEnd()
    const bullet = line.match(/^\s*(?:[-*•]|\d+\.)\s+(.*)$/)
    if (bullet) {
      bullets.push(bullet[1])
      continue
    }
    flush()
    if (line.trim()) blocks.push(<p key={`p${blocks.length}`}>{inline(line.replace(/^#+\s*/, ''))}</p>)
  }
  flush()
  return <div className="rich">{blocks}</div>
}
