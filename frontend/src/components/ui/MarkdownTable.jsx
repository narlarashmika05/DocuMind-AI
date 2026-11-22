/** Render the Markdown tables produced by the backend's table extractor. */
function parseRow(line) {
  return line
    .trim()
    .replace(/^\||\|$/g, '')
    .split(/(?<!\\)\|/)
    .map((cell) => cell.trim().replace(/\\\|/g, '|'))
}

export default function MarkdownTable({ markdown }) {
  const lines = markdown.split('\n').filter((line) => line.trim())
  if (lines.length < 2) return <pre className="whitespace-pre-wrap text-sm">{markdown}</pre>
  const [header, , ...rows] = lines.map(parseRow)

  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 dark:border-slate-800">
      <table className="min-w-full divide-y divide-slate-200 dark:divide-slate-800 text-sm">
        <thead className="bg-slate-50 dark:bg-slate-800/50">
          <tr>
            {header.map((cell, i) => (
              <th key={i} className="px-3 py-2 text-left font-semibold text-slate-700 dark:text-slate-300">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
          {rows.map((row, r) => (
            <tr key={r}>
              {row.map((cell, c) => (
                <td key={c} className="px-3 py-2 text-slate-700 dark:text-slate-300">
                  {cell}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
