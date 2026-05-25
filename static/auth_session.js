/**
 * 登录会话（Cookie）+ Header 令牌 + 刷新后恢复当前页
 * 客服端 / 生产端共用
 */
(function (global) {
    const ROUTE_KEY = 'sanyang_ui_route';
    const AUTH_USER_KEY = 'sanyang_auth_user';
    const AUTH_TOKEN_KEY = 'sanyang_auth_token';

    function storageGet(key) {
        try {
            const v = localStorage.getItem(key);
            if (v) return v;
        } catch (e) { /* ignore */ }
        try {
            return sessionStorage.getItem(key);
        } catch (e) { /* ignore */ }
        return null;
    }

    function storageSet(key, value) {
        try {
            localStorage.setItem(key, value);
        } catch (e) { /* ignore */ }
        try {
            sessionStorage.setItem(key, value);
        } catch (e) { /* ignore */ }
    }

    function storageRemove(key) {
        try {
            localStorage.removeItem(key);
        } catch (e) { /* ignore */ }
        try {
            sessionStorage.removeItem(key);
        } catch (e) { /* ignore */ }
    }

    function readAuthCredentials() {
        const u = storageGet(AUTH_USER_KEY);
        const t = storageGet(AUTH_TOKEN_KEY);
        if (u && t) return { user: u, token: t };
        return null;
    }

    function applyAuthHeaders(headers) {
        const h = Object.assign({}, headers || {});
        const cred = readAuthCredentials();
        if (cred) {
            h['X-Sanyang-User'] = cred.user;
            h['X-Sanyang-Token'] = cred.token;
        }
        return h;
    }

    function saveAuthCredentials(user, token) {
        if (!user) return;
        storageSet(AUTH_USER_KEY, user);
        if (token) storageSet(AUTH_TOKEN_KEY, token);
    }

    function clearAuthCredentials() {
        storageRemove(AUTH_USER_KEY);
        storageRemove(AUTH_TOKEN_KEY);
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

    function isApiPath(path) {
        if (!path) return false;
        if (path.startsWith('/api/')) return true;
        if (global.location && path.startsWith(global.location.origin + '/api/')) return true;
        return false;
    }

    function apiFetch(url, options) {
        const opts = Object.assign({ credentials: 'same-origin' }, options || {});
        opts.headers = applyAuthHeaders(opts.headers);
        if (!opts.headers['Content-Type'] && opts.method && opts.method.toUpperCase() === 'POST') {
            opts.headers['Content-Type'] = 'application/json';
        }
        if (opts.body === undefined && opts.method && opts.method.toUpperCase() === 'POST') {
            opts.body = '{}';
        }
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
            if (isApiPath(path)) {
                opts.credentials = opts.credentials || 'same-origin';
                opts.headers = applyAuthHeaders(opts.headers);
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
        readAuthCredentials,
    };
})(window);
