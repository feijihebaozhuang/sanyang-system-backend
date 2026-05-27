import type { ReactNode } from 'react';
import { LucideIcon } from 'lucide-react';

interface DiagnosticCardProps {
  title: string;
  icon: LucideIcon;
  children: ReactNode;
  className?: string;
}

export default function DiagnosticCard({ title, icon: Icon, children, className = '' }: DiagnosticCardProps) {
  return (
    <section className={`rounded-xl border border-slate-200 bg-white p-5 shadow-sm ${className}`}>
      <div className="mb-4 flex items-center gap-2 border-b border-slate-100 pb-3">
        <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-brand-600/10 text-brand-600">
          <Icon className="h-5 w-5" />
        </div>
        <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
      </div>
      {children}
    </section>
  );
}
