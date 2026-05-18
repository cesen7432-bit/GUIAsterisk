export function FormField({ label, error, children, required }) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="label">
          {label}
          {required && <span className="text-red-500 ml-1">*</span>}
        </label>
      )}
      {children}
      {error && <p className="text-xs text-red-600">{error}</p>}
    </div>
  )
}

export function Select({ children, ...props }) {
  return (
    <select className="input" {...props}>
      {children}
    </select>
  )
}

export function Input(props) {
  return <input className="input" {...props} />
}

export function Checkbox({ label, ...props }) {
  return (
    <label className="flex items-center gap-2 cursor-pointer">
      <input type="checkbox" className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500" {...props} />
      <span className="text-sm text-gray-700">{label}</span>
    </label>
  )
}
