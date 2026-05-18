/**
 * 登录会话（Cookie）+ 刷新后恢复当前页
 * 客服端 / 生产端共用
 */
(function (global) {
    const ROUTE_KEY = 'sanyang_ui_route';

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
        return fetch(url, opts);
    }

    // 同源 /api/* 自动带 Cookie（生产端 index.html 里大量裸 fetch 会漏 credentials）
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
    };
})(window);
