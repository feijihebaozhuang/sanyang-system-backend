/**
 * 登录会话（Cookie）+ Header 令牌 + 刷新后恢复当前页
 * 客服端 / 生产端共用
 */
(function (global) {
    const ROUTE_KEY = 'sanyang_ui_route';
    const AUTH_USER_KEY = 'sanyang_auth_user';
    const AUTH_TOKEN_KEY = 'sanyang_auth_token';

    function saveAuthCredentials(user, token) {
        if (!user) return;
        try {
            sessionStorage.setItem(AUTH_USER_KEY, user);
            if (token) sessionStorage.setItem(AUTH_TOKEN_KEY, token);
        } catch (e) { /* ignore */ }
    }

    function clearAuthCredentials() {
        try {
            sessionStorage.removeItem(AUTH_USER_KEY);
            sessionStorage.removeItem(AUTH_TOKEN_KEY);
        } catch (e) { /* ignore */ }
    }

    function saveRoute(top, sub) {
        const route = { top: top || 'main', sub: sub || null };
        try {
            sessionStorage.setItem(ROUTE_KEY, JSON.stringify(route));
        } catch (e) { /* ignore */ }
        const hash = sub ? '#page=' + encodeURIComponent(top) + '&sub=' + encodeURIComponent(sub)
            : '#page=' + encodeURIComponent(top);
        if (location.hash !== hash) {
            history.replaceState(null, '', location.pathname + location.search + hash);
        }
    }

    function readRoute() {
        const raw = (location.hash || '').replace(/^#/, '');
        if (raw) {
            const p = new URLSearchParams(raw);
            const page = p.get('page');
            if (page) {
                return { top: page, sub: p.get('sub') || null };
            }
        }
        try {
            const r = JSON.parse(sessionStorage.getItem(ROUTE_KEY) || '{}');
            if (r.top) {
                return { top: r.top, sub: r.sub || null };
            }
        } catch (e) { /* ignore */ }
        return { top: 'main', sub: null };
    }

    function clearRoute() {
        try {
            sessionStorage.removeItem(ROUTE_KEY);
        } catch (e) { /* ignore */ }
        if (location.hash) {
            history.replaceState(null, '', location.pathname + location.search);
        }
    }

    function apiFetch(url, options) {
        const opts = Object.assign({ credentials: 'same-origin' }, options || {});
        const headers = Object.assign({}, opts.headers || {});
        try {
            const u = sessionStorage.getItem(AUTH_USER_KEY);
            const t = sessionStorage.getItem(AUTH_TOKEN_KEY);
            if (u && t) {
                headers['X-Sanyang-User'] = u;
                headers['X-Sanyang-Token'] = t;
            }
        } catch (e) { /* ignore */ }
        if (!headers['Content-Type'] && opts.method && opts.method.toUpperCase() === 'POST') {
            headers['Content-Type'] = 'application/json';
        }
        if (opts.body === undefined && opts.method && opts.method.toUpperCase() === 'POST') {
            opts.body = '{}';
        }
        opts.headers = headers;
        return fetch(url, opts);
    }

    if (global.fetch && !global.__SY_FETCH_PATCHED) {
        global.__SY_FETCH_PATCHED = true;
        const nativeFetch = global.fetch.bind(global);
        global.fetch = function (url, options) {
            const opts = options ? Object.assign({}, options) : {};
            let path = '';
            if (typeof url === 'string') {
                path = url;
            } else if (url && url.url) {
                path = url.url;
            }
            if (
                path.startsWith('/api/') ||
                (global.location && path.startsWith(global.location.origin + '/api/'))
            ) {
                opts.credentials = opts.credentials || 'same-origin';
            }
            return nativeFetch(url, opts);
        };
    }

    global.SY_AUTH = {
        saveRoute,
        readRoute,
        clearRoute,
        apiFetch,
        saveAuthCredentials,
        clearAuthCredentials,
    };
})(window);
