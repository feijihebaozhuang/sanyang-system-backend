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

## 部署后同步前端

`deploy-docker.sh` 默认**不覆盖** stable 上的 `index.html`。  
后端更新后若改了刀模表单/列表，需手动：

```bash
cp /www/feijihe/repo/index.html /www/feijihe/stable/index.html
docker compose -f /www/feijihe/stable/docker-compose.yml restart prod
```
