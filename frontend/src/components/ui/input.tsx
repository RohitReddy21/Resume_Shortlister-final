import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {}

export function Input({ className, ...props }: InputProps) {
  return <input className={twMerge(clsx('w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-white outline-none ring-0', className))} {...props} />;
}
