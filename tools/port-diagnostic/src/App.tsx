import { useCallback, useState } from 'react';
import { HashRouter, Route, Routes } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  CheckCircle,
  Copy,
  Globe,
  Loader2,
  Server,
  Shield,
  Terminal,
  XCircle,
} from 'lucide-react';
import DiagnosticCard from './components/DiagnosticCard';
import StepGuide from './components/StepGuide';
import {
  DEFAULT_INSTANCE,
  DIAGNOSTIC_STEPS,
  FAQ_ITEMS,
  SANYANG_PORTS,
  type InstanceInfo,
  type PortTestResult,
  type SecurityGroupRule,
} from './config';

function copyText(text: string) {
  void navigator.clipboard.writeText(text);
}

function HomePage() {
  const [instance, setInstance] = useState<InstanceInfo>(DEFAULT_INSTANCE);
  const [targetHost, setTargetHost] = useState('feijihe.top');
  const [targetPort, setTargetPort] = useState('3003');
  const [testMode, setTestMode] = useState<'domain' | 'raw'>('domain');
  const [portResult, setPortResult] = useState<PortTestResult>('idle');
  const [portMessage, setPortMessage] = useState('');
  const [activeStep, setActiveStep] = useState(1);

  const sgRules: SecurityGroupRule[] = [
    { port: 22, protocol: 'TCP', cidr: '0.0.0.0/0', status: 'ok', note: 'SSH' },
    { port: 80, protocol: 'TCP', cidr: '0.0.0.0/0', status: 'ok', note: 'HTTP' },
    { port: 443, protocol: 'TCP', cidr: '0.0.0.0/0', status: 'ok', note: 'HTTPS' },
    {
      port: 3003,
      protocol: 'TCP',
      cidr: '0.0.0.0/0',
      status: 'warn',
      note: '三羊生产通常不需要公网放行，Nginx 本机反代即可',
    },
  ];

  const runPortTest = useCallback(async () => {
    setPortResult('testing');
    setPortMessage('检测中…');

    const port = targetPort.trim() || '3003';

    try {
      if (testMode === 'domain') {
        const host = targetHost.trim() || 'feijihe.top';
        const urls =
          port === '3003'
            ? [
                `https://${host}/api/co/health`,
                `https://${host}/guanli/login`,
              ]
            : [`https://${host}/api/health`];

        let lastErr = '';
        for (const url of urls) {
          try {
            const ctrl = new AbortController();
            const timer = setTimeout(() => ctrl.abort(), 12000);
            const res = await fetch(url, { signal: ctrl.signal, mode: 'cors' });
            clearTimeout(timer);
            const text = await res.text();
            if (res.ok && (text.includes('"ok"') || text.includes('login') || text.includes('html'))) {
              setPortResult('success');
              setPortMessage(`可达：${url} → HTTP ${res.status}`);
              return;
            }
            lastErr = `${url} → HTTP ${res.status}`;
          } catch (e) {
            lastErr = e instanceof Error ? e.message : String(e);
          }
        }
        setPortResult('failed');
        setPortMessage(`域名探测失败：${lastErr}。请在服务器本机 curl 127.0.0.1:${port}`);
        return;
      }

      // 浏览器无法做真实 TCP 探测公网 IP:端口
      await new Promise((r) => setTimeout(r, 1500));
      setPortResult('timeout');
      setPortMessage(
        `浏览器无法直连 TCP ${targetHost}:${port}。请 SSH 登录后执行：curl -s http://127.0.0.1:${port}/api/health`,
      );
    } catch (e) {
      setPortResult('failed');
      setPortMessage(e instanceof Error ? e.message : '检测失败');
    }
  }, [targetHost, targetPort, testMode]);

  const sshCmd = `ssh root@${instance.publicIp}`;
  const statusIcon =
    portResult === 'success' ? (
      <CheckCircle className="h-5 w-5 text-emerald-500" />
    ) : portResult === 'testing' ? (
      <Loader2 className="h-5 w-5 animate-spin text-brand-600" />
    ) : portResult === 'idle' ? (
      <Activity className="h-5 w-5 text-slate-400" />
    ) : (
      <XCircle className="h-5 w-5 text-red-500" />
    );

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-100 to-slate-50">
      <header className="border-b border-slate-200 bg-white/80 backdrop-blur">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
          <div>
            <h1 className="text-xl font-bold text-brand-900">3003 端口连通性诊断</h1>
            <p className="text-sm text-slate-500">三羊系统 · ECS / Nginx / 管理后台</p>
          </div>
          <span className="inline-flex items-center gap-1 rounded-full bg-emerald-50 px-3 py-1 text-xs font-medium text-emerald-700">
            <span className="h-2 w-2 rounded-full bg-emerald-500" />
            诊断工具 v1.0
          </span>
        </div>
      </header>

      <main className="mx-auto max-w-5xl space-y-6 px-4 py-8">
        <DiagnosticCard title="实例信息" icon={Server}>
          <div className="grid gap-4 sm:grid-cols-2">
            {(
              [
                ['实例 ID', 'id'],
                ['名称', 'name'],
                ['公网 IP', 'publicIp'],
                ['内网 IP', 'privateIp'],
                ['安全组', 'securityGroupId'],
                ['地域', 'region'],
              ] as const
            ).map(([label, key]) => (
              <label key={key} className="block text-sm">
                <span className="text-slate-500">{label}</span>
                <input
                  className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm"
                  value={instance[key]}
                  onChange={(e) => setInstance({ ...instance, [key]: e.target.value })}
                />
              </label>
            ))}
          </div>
          <p className="mt-3 text-xs text-amber-700">
            登录入口：<a className="underline" href="https://feijihe.top/guanli/login" target="_blank" rel="noreferrer">https://feijihe.top/guanli/login</a>（admin / admin888）
          </p>
        </DiagnosticCard>

        <div className="grid gap-6 lg:grid-cols-2">
          <DiagnosticCard title="端口 / 域名连通性" icon={Globe}>
            <div className="mb-3 flex gap-2">
              <button
                type="button"
                onClick={() => setTestMode('domain')}
                className={`rounded-lg px-3 py-1.5 text-sm ${testMode === 'domain' ? 'bg-brand-600 text-white' : 'bg-slate-100'}`}
              >
                域名探测（推荐）
              </button>
              <button
                type="button"
                onClick={() => setTestMode('raw')}
                className={`rounded-lg px-3 py-1.5 text-sm ${testMode === 'raw' ? 'bg-brand-600 text-white' : 'bg-slate-100'}`}
              >
                IP:端口
              </button>
            </div>
            <div className="grid gap-3 sm:grid-cols-3">
              <input
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm sm:col-span-2"
                placeholder="域名或 IP"
                value={targetHost}
                onChange={(e) => setTargetHost(e.target.value)}
              />
              <input
                className="rounded-lg border border-slate-200 px-3 py-2 text-sm"
                placeholder="端口"
                value={targetPort}
                onChange={(e) => setTargetPort(e.target.value)}
              />
            </div>
            <button
              type="button"
              onClick={() => void runPortTest()}
              disabled={portResult === 'testing'}
              className="mt-4 w-full rounded-lg bg-brand-600 py-2.5 text-sm font-medium text-white hover:bg-brand-700 disabled:opacity-60"
            >
              开始检测
            </button>
            <div className="mt-4 flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-sm">
              {statusIcon}
              <span className="text-slate-700">{portMessage || '点击「开始检测」'}</span>
            </div>
            <ul className="mt-3 space-y-1 text-xs text-slate-500">
              {SANYANG_PORTS.map((p) => (
                <li key={p.port}>
                  <strong>{p.port}</strong> {p.label} → {p.expose}
                </li>
              ))}
            </ul>
          </DiagnosticCard>

          <DiagnosticCard title="安全组规则检查" icon={Shield}>
            <p className="mb-3 text-sm text-slate-600">
              当前安全组：<code className="rounded bg-slate-100 px-1">{instance.securityGroupId}</code>
            </p>
            <ul className="space-y-2">
              {sgRules.map((r) => (
                <li
                  key={r.port}
                  className="flex items-center justify-between rounded-lg border border-slate-100 px-3 py-2 text-sm"
                >
                  <span>
                    {r.protocol} {r.port} ← {r.cidr}
                    {r.note && <span className="ml-2 text-xs text-slate-400">{r.note}</span>}
                  </span>
                  {r.status === 'ok' && <CheckCircle className="h-4 w-4 text-emerald-500" />}
                  {r.status === 'warn' && <AlertTriangle className="h-4 w-4 text-amber-500" />}
                  {r.status === 'missing' && <XCircle className="h-4 w-4 text-red-500" />}
                </li>
              ))}
            </ul>
            <p className="mt-3 text-xs text-slate-500">
              若仅 3003 不通而 443 正常：在阿里云控制台 → 安全组 → 入站规则添加入方向 TCP 3003（调试完建议关闭公网暴露）。
            </p>
          </DiagnosticCard>
        </div>

        <DiagnosticCard title="SSH 远程诊断" icon={Terminal}>
          <div className="flex items-center gap-2 rounded-lg bg-slate-900 px-4 py-3 text-sm text-emerald-300">
            <code className="flex-1 overflow-x-auto">{sshCmd}</code>
            <button type="button" onClick={() => copyText(sshCmd)} className="text-slate-400 hover:text-white" title="复制">
              <Copy className="h-4 w-4" />
            </button>
          </div>
          <div className="mt-3 grid gap-2 sm:grid-cols-2">
            {[
              'ss -tlnp | grep 3003',
              'curl -s http://127.0.0.1:3003/api/health',
              'bash /www/feijihe/repo/scripts/ops/ensure_guanli_login_87.sh',
              'sudo ufw status',
            ].map((cmd) => (
              <div key={cmd} className="flex items-center gap-2 rounded bg-slate-100 px-2 py-1.5 text-xs">
                <code className="flex-1 truncate">{cmd}</code>
                <button type="button" onClick={() => copyText(cmd)}>
                  <Copy className="h-3.5 w-3.5 text-slate-400" />
                </button>
              </div>
            ))}
          </div>
        </DiagnosticCard>

        <DiagnosticCard title="排查步骤指南" icon={Activity}>
          <StepGuide steps={DIAGNOSTIC_STEPS} activeStep={activeStep} onStepClick={setActiveStep} />
          <div className="mt-4 flex gap-2">
            <button
              type="button"
              disabled={activeStep <= 1}
              onClick={() => setActiveStep((s) => Math.max(1, s - 1))}
              className="rounded-lg border px-4 py-2 text-sm disabled:opacity-40"
            >
              上一步
            </button>
            <button
              type="button"
              disabled={activeStep >= DIAGNOSTIC_STEPS.length}
              onClick={() => setActiveStep((s) => Math.min(DIAGNOSTIC_STEPS.length, s + 1))}
              className="rounded-lg bg-brand-600 px-4 py-2 text-sm text-white disabled:opacity-40"
            >
              下一步
            </button>
          </div>
        </DiagnosticCard>

        <DiagnosticCard title="常见问题" icon={AlertTriangle}>
          <ul className="space-y-4">
            {FAQ_ITEMS.map((item) => (
              <li key={item.title}>
                <h3 className="font-medium text-slate-900">{item.title}</h3>
                <p className="mt-1 text-sm text-slate-600">{item.body}</p>
              </li>
            ))}
          </ul>
        </DiagnosticCard>
      </main>
    </div>
  );
}

export default function App() {
  return (
    <HashRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
      </Routes>
    </HashRouter>
  );
}
