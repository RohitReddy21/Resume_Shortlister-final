"use client";

import Link from 'next/link';
import type { ReactNode } from 'react';

interface AuthFormProps {
  title: string;
  description: string;
  children: ReactNode;
  footer?: ReactNode;
}

export function AuthForm({ title, description, children, footer }: AuthFormProps) {
  return (
    <div className="mt-8 space-y-4">
      <div>
        <h2 className="text-2xl font-semibold text-white">{title}</h2>
        <p className="mt-2 text-sm text-slate-400">{description}</p>
      </div>
      {children}
      {footer ? <div className="pt-2">{footer}</div> : null}
    </div>
  );
}
