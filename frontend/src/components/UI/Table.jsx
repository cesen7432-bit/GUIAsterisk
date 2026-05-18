export function Table({ headers, children, loading }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-gray-200">
      <table className="min-w-full divide-y divide-gray-200">
        <thead className="bg-gray-50">
          <tr>
            {headers.map((h) => (
              <th key={h} className="px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider">
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-100">
          {loading ? (
            <tr>
              <td colSpan={headers.length} className="px-4 py-8 text-center text-gray-400 text-sm">
                Cargando...
              </td>
            </tr>
          ) : children}
        </tbody>
      </table>
    </div>
  )
}

export function Td({ children, className = '' }) {
  return (
    <td className={`px-4 py-3 text-sm text-gray-700 whitespace-nowrap ${className}`}>
      {children}
    </td>
  )
}

export function Tr({ children, onClick }) {
  return (
    <tr
      className={`table-row ${onClick ? 'cursor-pointer' : ''}`}
      onClick={onClick}
    >
      {children}
    </tr>
  )
}
