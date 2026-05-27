# 端口连通性诊断工具

三羊系统 3001/3002/3003 端口与 Nginx 入口排查用 React 小工具。

## 启动

```bash
cd tools/port-diagnostic
npm install
npm run dev
```

浏览器打开 Vite 提示的地址（默认 `http://localhost:5175`）。

## 功能

- 实例信息（ECS ID、IP、安全组）可编辑
- **域名探测**：对 `feijihe.top/api/co/health`、`/guanli/login` 做 HTTP 检测（推荐）
- **IP:端口**：提示浏览器无法 TCP 探测，给出 SSH curl 命令
- 安全组规则清单与 3003 放行说明
- SSH 命令一键复制
- 4 步排查指南（本机 3003 → 登录 API → Nginx → 防火墙）
- 三羊特有问题（guanli 子域 SSL、登录入口）

## 与三羊架构的关系

| 端口 | 说明 |
|------|------|
| 3001 | 客服 zean.feijihe.top |
| 3002 | 生产 feijihe.top |
| 3003 | 管理后台；**生产应经 Nginx `/api/co` 反代**，不必对公网开放 3003 |

登录请用：**https://feijihe.top/guanli/login**（admin / admin888）

## 构建

```bash
npm run build
```

静态产物在 `dist/`，可挂到任意静态服务器或 `feijihe.top` 某路径。
