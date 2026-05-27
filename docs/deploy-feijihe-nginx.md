# guanli.feijihe.top 管理后台登录无反应（SY_AUTH 未定义）

## 根因（已确认）

`guanli` 的 Nginx 在 **`location /`** 上配置了 `allow` / `deny` IP 白名单（如仅允许 `14.120.52.215`）。  
**所有路径**（含 `/static/auth_session.js`）都走该 location，因此：

- 在服务器上 `curl guanli.feijihe.top` → **403**（非白名单 IP）
- 用户侧若 HTML 能打开但出口 IP 与白名单不一致，**JS 被 403** → 浏览器报 `SY_AUTH is not defined` → 点登录无反应

这与 MySQL / `admin888` 无关，是 **静态资源被 Nginx 拦了**。

## 修复（二选一，建议都做）

1. **代码（已做）**：`index_customer_order.html` **内联** `auth_session.js`，首页不再请求 `/static/auth_session.js`。
2. **Nginx（C 在 87 改）**：在 `guanli` 的 `server` 块里、带白名单的 `location /` **之前** include：

   ```nginx
   include /www/feijihe/repo/deploy/nginx-guanli-static.conf.include;
   ```

   或手写 `location /static/ { proxy_pass http://127.0.0.1:3003/static/; }`，**不要**在 `/static/` 里写 `allow/deny`。

## 自检

```bash
# 应 200（勿带白名单外的测试 IP 时期望 403 仅针对 /，/static 应 200）
curl -s -o /dev/null -w "%{http_code}\n" https://guanli.feijihe.top/static/auth_session.js
curl -s -o /dev/null -w "%{http_code}\n" -X POST https://guanli.feijihe.top/api/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"admin888"}'
```

部署：`sudo bash /www/feijihe/repo/deploy.sh`（会覆盖 `index_customer_order.html`）。

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
