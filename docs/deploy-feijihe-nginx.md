# 三端口与 guanli 登录（必读）

## 三个端口各是什么（87 同一台机，不同程序）

| 端口 | 程序 | 域名 | 登录账号表 | 用途 |
|------|------|------|------------|------|
| **3001** | `app_cs.py` | `zean.feijihe.top` | 内存 `USERS` + MySQL `users` | 客服订单看板 |
| **3002** | `app_production.py` | `feijihe.top` | 同上 `USERS` / `users` | 生产扫码、报价、小程序 `/api/mp/*` |
| **3003** | `app_customer_order.py` | `guanli.feijihe.top` | MySQL **`co_admin_user`**（与 3001 不是一张表） | 统一管理后台 |

三套 **Session / 登录互不相通**。在 guanli 登的是 3003 的 `admin`，不是 zean 上的客服账号。

## guanli 仍登不进：为什么内联 JS 还不够

Nginx 若在 **`location /`** 写 `allow 14.120.52.215; deny all;`，则 **所有未单独拆出的路径** 都过白名单，包括：

| 路径 | 后果 |
|------|------|
| `/static/auth_session.js` | 403 → `SY_AUTH` 未定义（**已用 HTML 内联绕过**） |
| **`POST /api/login`** | **403** → 前端显示失败或像没反应（**必须改 Nginx**） |
| `GET /api/me` 等 | 403 → 进不了后台 |

所以：**只改代码、不改 Nginx，`/api/login` 照样 403。**

## Nginx 正确写法（C 在 87 改）

在带白名单的 `location /` **之前** include（顺序不能反）：

```nginx
include /www/feijihe/repo/deploy/nginx-guanli-api-static.conf.include;
```

该文件含 **`location /api/`** 与 **`location /static/`**，均反代 `127.0.0.1:3003`，**不要**写 `allow/deny`。

完整示例见 `deploy/nginx-guanli.example.conf`。

```bash
sudo nginx -t && sudo systemctl reload nginx
bash /www/feijihe/repo/scripts/verify_three_ports.sh
```

期望：`POST https://guanli.feijihe.top/api/login` → **200** 且 body 含 `"success":true`（非 403）。

## 本机验收（在 87 上）

```bash
# 三端口进程
curl -s -o /dev/null -w "3001:%{http_code} 3002:%{http_code} 3003:%{http_code}\n" \
  http://127.0.0.1:3001/ http://127.0.0.1:3002/ http://127.0.0.1:3003/

# 3003 登录（不经过 Nginx）
curl -s -X POST http://127.0.0.1:3003/api/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin888"}'
```

- 本机 3003 成功、域名 POST **403** → **100% 是 guanli 的 Nginx 白名单**，与密码无关。
- 本机 3003 也失败 → 查 `stable/.env`、MySQL、`systemctl status sanyang-customer-order`。

---

# feijihe.top 生产端部署排查（400 / SY_AUTH）

## 常见原因

1. **Nginx `proxy_pass` 端口错误**  
   生产端 Flask 监听 **3002**（`network_mode: host` 时直接绑宿主机）。  
   `feijihe.top` 应反代到 `http://127.0.0.1:3002`，客服 `zean.feijihe.top` 为 **3001**。

2. **静态资源未进容器**  
   `index.html` 依赖 `/static/auth_session.js`、`/static/prod_ui.js`。  
   Docker 需 `COPY static/` 或 compose 挂载 `./static:/app/static:ro`。  
   缺失时浏览器报 **`SY_AUTH is not defined`**，页面白屏或异常。

3. **Host / SSL**  
   Nginx `server_name` 须含 `feijihe.top`；证书与 `listen 443` 配置一致。  
   错误 `server_name` 或 `return 400` 规则会导致整站 400。

## 快速自检（服务器）

```bash
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002/
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:3002/static/auth_session.js
curl -s -o /dev/null -w "%{http_code}" -H "Host: feijihe.top" https://127.0.0.1/   # 若本机有 nginx
docker compose -f /www/feijihe/stable/docker-compose.yml ps
```

期望：根路径与 `auth_session.js` 均为 **200**。

## 登录报「网络错误: SY_AUTH is not defined」

1. 浏览器 F12 → Network，看 `/static/auth_session.js` 是否为 **200**（404/502 即未加载）。
2. 服务器：
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:3002/static/auth_session.js
   ls -la /www/feijihe/stable/static/auth_session.js
   ```
3. **stable 的 `index.html` 很旧**（没有 `<script src="/static/auth_session.js">`）时，从 repo 覆盖并重启 prod：
   ```bash
   cp /www/feijihe/repo/index.html /www/feijihe/stable/index.html
   docker compose -f /www/feijihe/stable/docker-compose.yml restart prod
   ```
4. Nginx 若单独 `location /static/` 用 `alias`，路径必须指向 **`/www/feijihe/stable/static/`**；否则删掉该 location，全部反代到 3002。

## 部署后同步前端

`deploy-docker.sh` 默认**不覆盖** stable 上的 `index.html`。  
后端更新后若改了刀模表单/列表，需手动：

```bash
cp /www/feijihe/repo/index.html /www/feijihe/stable/index.html
docker compose -f /www/feijihe/stable/docker-compose.yml restart prod
```
