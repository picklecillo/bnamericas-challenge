/** `oil_and_gas` -> `Oil and gas`, `ict` -> `ICT`. */
export function humanize(value: string): string {
  const text = value.replace(/_/g, ' ')
  return text === 'ict' ? 'ICT' : text.charAt(0).toUpperCase() + text.slice(1)
}
