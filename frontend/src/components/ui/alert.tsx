import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function Alert({ className, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return <div className={twMerge(clsx('rounded-md border border-slate-700 bg-slate-950/80 p-3 text-sm text-slate-300', className))} {...props} />;
}
