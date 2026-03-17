import type { IOCType, DetectedIOC } from '@/types/ioc'

// Mirrors backend ioc_service.py auto_detect() — keep patterns in sync
const PATTERNS: Array<{ type: IOCType; regex: RegExp }> = [
  { type: 'url',    regex: /https?:\/\/[^\s<>"{}|\\^`\[\]]+/g },
  { type: 'email',  regex: /\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b/g },
  { type: 'hash',   regex: /\b[a-fA-F0-9]{64}\b/g },  // SHA-256
  { type: 'hash',   regex: /\b[a-fA-F0-9]{40}\b/g },  // SHA-1
  { type: 'hash',   regex: /\b[a-fA-F0-9]{32}\b/g },  // MD5
  { type: 'ip',     regex: /\b(?:\d{1,3}\.){3}\d{1,3}\b/g },
  { type: 'domain', regex: /\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}\b/g },
]

export function detectIOCs(text: string): DetectedIOC[] {
  const seen = new Set<string>()
  const results: DetectedIOC[] = []

  // Strip already matched spans to avoid double-matching
  let remaining = text

  for (const { type, regex } of PATTERNS) {
    const matches = [...remaining.matchAll(regex)]
    for (const match of matches) {
      const value = match[0]
      if (!seen.has(value)) {
        seen.add(value)
        results.push({ ioc_type: type, value })
      }
    }
    // Remove matched values from remaining text to avoid re-matching
    remaining = remaining.replace(regex, ' ')
  }

  return results
}
