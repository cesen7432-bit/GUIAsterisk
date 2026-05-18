import clsx from 'clsx'

const variants = {
  green:  'bg-green-100 text-green-800',
  red:    'bg-red-100 text-red-800',
  yellow: 'bg-yellow-100 text-yellow-800',
  gray:   'bg-gray-100 text-gray-600',
  blue:   'bg-blue-100 text-blue-800',
  purple: 'bg-purple-100 text-purple-800',
}

export function Badge({ children, variant = 'gray', dot = false }) {
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-medium', variants[variant])}>
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full', {
        'bg-green-500': variant === 'green',
        'bg-red-500': variant === 'red',
        'bg-yellow-500': variant === 'yellow',
        'bg-gray-400': variant === 'gray',
        'bg-blue-500': variant === 'blue',
      })} />}
      {children}
    </span>
  )
}
