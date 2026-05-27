export type PortTestResult = 'idle' | 'testing' | 'success' | 'timeout' | 'failed';

export interface InstanceInfo {
  id: string;
  name: string;
  publicIp: string;
  privateIp: string;
  securityGroupId: string;
  region: string;
  os: string;
}

export interface SecurityGroupRule {
  port: number;
  protocol: string;
  cidr: string;
  status: 'ok' | 'missing' | 'warn';
  note?: string;
}

export interface DiagnosticStep {
  id: number;
  title: string;
  description: string;
  commands: string[];
}

export const DEFAULT_INSTANCE: InstanceInfo = {
  id: 'i-示例',
  name: '三羊应用机 (87)',
  publicIp: '47.xxx.xxx.xxx',
  privateIp: '172.xxx.xxx.xxx',
  securityGroupId: 'sg-7xvc2wye9y2cyqwtlf4l',
  region: '华南',
  os: 'Ubuntu / CentOS',
};

export const SANYANG_PORTS = [
  { port: 3001, label: '客服端 app_cs', expose: 'zean.feijihe.top' },
  { port: 3002, label: '生产端 app_production', expose: 'feijihe.top' },
  { port: 3003, label: '管理后台 app_customer_order', expose: 'feijihe.top/guanli/login（经 Nginx 反代，勿公网直连）' },
];

export const DIAGNOSTIC_STEPS: DiagnosticStep[] = [
  {
    id: 1,
    title: '本机进程与监听',
    description: '在 87 上确认 3003 进程存在且监听 0.0.0.0:3003',
    commands: [
      'systemctl status sanyang-customer-order',
      'curl -s http://127.0.0.1:3003/api/health',
      'ss -tlnp | grep 3003',
    ],
  },
  {
    id: 2,
    title: '登录 API 本机验收',
    description: '绕过 Nginx，直接测 3003 登录（admin/admin888）',
    commands: [
      'curl -s -X POST http://127.0.0.1:3003/api/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"admin888"}\'',
      'python3 /www/feijihe/repo/scripts/reset_co_admin_3003.py',
    ],
  },
  {
    id: 3,
    title: 'Nginx 与域名入口',
    description: '3003 不对公网暴露时，应通过 feijihe 反代 /api/co 与 /guanli/',
    commands: [
      'curl -s -X POST https://feijihe.top/api/co/login -H "Content-Type: application/json" -d \'{"username":"admin","password":"admin888"}\'',
      'curl -s -o /dev/null -w "%{http_code}" https://feijihe.top/guanli/login',
      'sudo bash /www/feijihe/repo/scripts/ops/ensure_guanli_login_87.sh',
    ],
  },
  {
    id: 4,
    title: '安全组与防火墙',
    description: '若需 SSH 外网调试 3003，才需放行；生产推荐仅 80/443 + 22',
    commands: [
      'sudo ufw status',
      'sudo ufw allow 443/tcp',
      'sudo iptables -L -n | head -30',
    ],
  },
];

export const FAQ_ITEMS = [
  {
    title: '安全组未放行 3003',
    body: '浏览器无法直连 ECS:3003 时，先查安全组入站是否允许 TCP 3003。三羊生产环境通常只需 80/443，3003 走 Nginx 127.0.0.1 反代即可。',
  },
  {
    title: '服务未启动',
    body: '执行 systemctl restart sanyang-customer-order 或 deploy.sh 后 sleep 3，再 curl 127.0.0.1:3003/api/health。',
  },
  {
    title: '监听地址错误',
    body: 'gunicorn 须绑定 0.0.0.0:3003（见 deploy/systemd/sanyang-customer-order.service），若仅 127.0.0.1 则外网永远不通。',
  },
  {
    title: '误用 guanli 子域',
    body: 'guanli.feijihe.top SSL 证书异常，请用 https://feijihe.top/guanli/login 登录，不要用 guanli 子域。',
  },
];
