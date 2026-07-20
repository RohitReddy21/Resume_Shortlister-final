import { clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function Label({ className, ...props }: React.LabelHTMLAttributes<HTMLLabelElement>) {
  return <label className={twMerge(clsx('mb-2 block text-sm text-slate-300', className))} {...props} />;
}
