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

    global.SY_AUTH = {
        saveRoute,
        readRoute,
        clearRoute,
        apiFetch,
    };
})(window);
