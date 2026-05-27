import { CheckCircle2, Circle } from 'lucide-react';
import type { DiagnosticStep } from '../../config';

interface StepGuideProps {
  steps: DiagnosticStep[];
  activeStep: number;
  onStepClick: (id: number) => void;
}

export default function StepGuide({ steps, activeStep, onStepClick }: StepGuideProps) {
  return (
    <ol className="space-y-4">
      {steps.map((step) => {
        const active = step.id === activeStep;
        const done = step.id < activeStep;
        return (
          <li key={step.id}>
            <button
              type="button"
              onClick={() => onStepClick(step.id)}
              className={`w-full rounded-lg border p-4 text-left transition ${
                active ? 'border-brand-600 bg-brand-50' : 'border-slate-200 hover:border-slate-300'
              }`}
            >
              <div className="flex items-start gap-3">
                {done ? (
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-emerald-500" />
                ) : (
                  <Circle className={`mt-0.5 h-5 w-5 shrink-0 ${active ? 'text-brand-600' : 'text-slate-300'}`} />
                )}
                <div className="min-w-0 flex-1">
                  <div className="font-medium text-slate-900">
                    步骤 {step.id}：{step.title}
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{step.description}</p>
                  {active && (
                    <ul className="mt-3 space-y-2">
                      {step.commands.map((cmd) => (
                        <li key={cmd}>
                          <code className="block overflow-x-auto rounded bg-slate-900 px-3 py-2 text-xs text-emerald-300">
                            {cmd}
                          </code>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              </div>
            </button>
          </li>
        );
      })}
    </ol>
  );
}
