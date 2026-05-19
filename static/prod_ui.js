/* 生产端：打单分页/缓存、WPS嵌入、通用导入 */
(function () {
    const PROD_CACHE_KEY = 'sy_prod_dashboard_v3';
    const WPS_KDOCS_URL = 'https://www.kdocs.cn/l/cdIlitRGKpMw';

    window._prodPage = 1;
    window._prodPageSize = 15;
    window._prodTotalPages = 1;
    window._prodDashboardOrders = window._prodDashboardOrders || [];
    window._prodOrderDetail = window._prodOrderDetail || {};

    window.openWpsKdocsEmbed = function () {
        if (typeof switchTopPage === 'function') {
            var fake = { classList: { add: function () {}, remove: function () {} } };
            document.querySelectorAll('.page-section').forEach(function (p) {
                p.classList.remove('active');
            });
            var pg = document.getElementById('page-wps-kdocs');
            if (pg) pg.classList.add('active');
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    window.prodRenderPagination = function () {
        var el = document.getElementById('prodPagination');
        if (!el) return;
        var p = window._prodPage;
        var tp = window._prodTotalPages;
        el.innerHTML =
            '<div class="prod-pager">' +
            '<button type="button" ' +
            (p <= 1 ? 'disabled' : '') +
            ' onclick="prodGoPage(' +
            (p - 1) +
            ')">上一页</button>' +
            '<span>第 <input type="number" id="prodPageInput" min="1" max="' +
            tp +
            '" value="' +
            p +
            '" style="width:48px;text-align:center;padding:4px;" onkeydown="if(event.key===\'Enter\')prodGoPageInput()"> / ' +
            tp +
            ' 页</span>' +
            '<button type="button" ' +
            (p >= tp ? 'disabled' : '') +
            ' onclick="prodGoPage(' +
            (p + 1) +
            ')">下一页</button>' +
            '<select id="prodPageSizeSel" onchange="prodChangePageSize(this.value)" style="margin-left:8px;padding:4px;">' +
            [10, 15, 20]
                .map(function (n) {
                    return (
                        '<option value="' +
                        n +
                        '"' +
                        (n === window._prodPageSize ? ' selected' : '') +
                        '>' +
                        n +
                        '条/页</option>'
                    );
                })
                .join('') +
            '</select></div>';
        el.innerHTML = el.innerHTML.replace(/motion\.div/g, 'div');
    };

    window.prodGoPage = function (n) {
        n = parseInt(n, 10);
        if (isNaN(n) || n < 1) n = 1;
        if (n > window._prodTotalPages) n = window._prodTotalPages;
        window._prodPage = n;
        loadProdDashboard(false);
    };

    window.prodGoPageInput = function () {
        var inp = document.getElementById('prodPageInput');
        prodGoPage(inp ? inp.value : 1);
    };

    window.prodChangePageSize = function (v) {
        window._prodPageSize = parseInt(v, 10) || 15;
        window._prodPage = 1;
        loadProdDashboard(false);
    };

    window.prodApplyCachedDashboard = function () {
        try {
            var raw = sessionStorage.getItem(PROD_CACHE_KEY);
            if (!raw) return false;
            var data = JSON.parse(raw);
            if (!data.orders || !data.orders.length) return false;
            window._prodDashboardOrders = data.orders;
            window._prodTotalPages = data.total_pages || 1;
            window._prodPage = data.page || 1;
            if (data.filters && data.filters.shops) {
                var shopSel = document.getElementById('prodFilterShop');
                if (shopSel && shopSel.options.length <= 1) {
                    data.filters.shops.forEach(function (s) {
                        var opt = document.createElement('option');
                        opt.value = s;
                        opt.textContent = s;
                        shopSel.appendChild(opt);
                    });
                }
            }
            renderProdDashboard(data.orders);
            prodRenderPagination();
            var st = data.stats || {};
            document.getElementById('prodStats').textContent =
                '共 ' +
                (st.total || 0) +
                ' 单 ｜ 已打印 ' +
                (st.printed || 0) +
                ' ｜ 未打印 ' +
                (st.unprinted || 0) +
                ' 单（缓存，后台更新中…）';
            return true;
        } catch (e) {
            return false;
        }
    };

    window.prodBuildDashboardQuery = function () {
        var q = new URLSearchParams();
        q.set('page', String(window._prodPage));
        q.set('page_size', String(window._prodPageSize));
        var shop = document.getElementById('prodFilterShop').value;
        var type = document.getElementById('prodFilterType').value;
        var printStatus = document.getElementById('prodFilterPrint').value;
        var dateFrom = document.getElementById('prodFilterDateFrom').value;
        var dateTo = document.getElementById('prodFilterDateTo').value;
        var search = document.getElementById('prodFilterSearch').value.trim();
        if (shop) q.set('shop', shop);
        if (type) q.set('type', type);
        if (printStatus) q.set('print', printStatus);
        if (dateFrom) q.set('date_from', dateFrom);
        if (dateTo) q.set('date_to', dateTo);
        if (search) q.set('search', search);
        return q.toString();
    };

    window.loadProdDashboard = async function (resetPage) {
        if (resetPage === true) window._prodPage = 1;
        var hadCache = prodApplyCachedDashboard();
        if (!hadCache) {
            document.getElementById('prodTable').innerHTML =
                '<tr><td colspan="11" style="text-align:center;padding:24px;color:#888;">正在后台加载…</td></tr>';
        }
        try {
            var res = await fetch('/api/production/dashboard?' + prodBuildDashboardQuery());
            var data = await res.json();
            if (!data.success) throw new Error(data.error || '加载失败');
            window._prodMappingData =
                data.material_mapping || data.production_material_mapping || [];
            window._prodDashboardOrders = data.orders || [];
            window._prodTotalPages = data.total_pages || 1;
            window._prodPage = data.page || 1;
            var shopSel = document.getElementById('prodFilterShop');
            if (shopSel && shopSel.options.length <= 1 && data.filters && data.filters.shops) {
                data.filters.shops.forEach(function (s) {
                    var opt = document.createElement('option');
                    opt.value = s;
                    opt.textContent = s;
                    shopSel.appendChild(opt);
                });
            }
            sessionStorage.setItem(
                PROD_CACHE_KEY,
                JSON.stringify({
                    orders: data.orders,
                    page: data.page,
                    total_pages: data.total_pages,
                    stats: data.stats,
                    filters: data.filters,
                    ts: Date.now(),
                })
            );
            var st = data.stats || {};
            document.getElementById('prodStats').textContent =
                '共 ' +
                (st.total || 0) +
                ' 单 ｜ 已打印 ' +
                (st.printed || 0) +
                ' ｜ 未打印 ' +
                (st.unprinted || 0) +
                ' 单';
            renderProdDashboard(data.orders);
            prodRenderPagination();
        } catch (e) {
            if (!hadCache) {
                document.getElementById('prodTable').innerHTML =
                    '<tr><td colspan="11" style="color:#e94560;text-align:center;padding:30px;">❌ ' +
                    e.message +
                    '</td></tr>';
            }
        }
    };

    window.prodRenderMobileCards = function (orders) {
        var box = document.getElementById('prodCardsMobile');
        if (!box) return;
        if (!orders || !orders.length) {
            box.innerHTML = '<div style="text-align:center;padding:20px;color:#999;">暂无订单</div>'.replace(
                /motion\.div/g,
                'div'
            );
            box.innerHTML = box.innerHTML.replace(/motion\.div/g, 'div');
            return;
        }
        var html = '';
        orders.forEach(function (o) {
            var pb = o.printed
                ? '<span style="color:#52c41a;font-weight:600;">已打印</span>'
                : '<span style="color:#e94560;font-weight:600;">未打印</span>';
            html +=
                '<div class="prod-card" onclick="showProdDetailBySoId(\'' +
                o.so_id +
                '\')">' +
                '<div style="display:flex;justify-content:space-between;margin-bottom:6px;"><span style="font-weight:600;color:#1677ff;">' +
                (o.so_id || '') +
                '</span>' +
                pb +
                '</div>' +
                '<div style="font-size:12px;color:#666;">' +
                (o.shop || '') +
                ' · ' +
                (o.product_type || '') +
                ' · ×' +
                (o.qty || 0) +
                '</div></div>';
        });
        box.innerHTML = html.replace(/motion\.div/g, 'div');
    };

    if (typeof window.renderProdDashboard === 'function') {
        var _origRenderProd = window.renderProdDashboard;
        window.renderProdDashboard = function (orders) {
            _origRenderProd(orders);
            prodRenderMobileCards(orders);
        };
    }

    window.openDataImportModal = function (kind) {
        window._importKind = kind || 'inventory';
        var titles = { dimoldb: '刀模库', inventory: '成品库存', raw: '原材料' };
        document.getElementById('dataImportTitle').textContent =
            '📥 导入' + (titles[kind] || '');
        document.getElementById('dataImportFile').value = '';
        document.getElementById('dataImportStatus').textContent = '';
        document.getElementById('dataImportModal').classList.add('show');
    };

    window.closeDataImportModal = function () {
        document.getElementById('dataImportModal').classList.remove('show');
    };

    window.downloadDataTemplate = function (kind) {
        kind = kind || window._importKind || 'inventory';
        var urls = {
            dimoldb: '/api/dimoldb/template',
            inventory: '/api/inventory/template?tab=finished',
            raw: '/api/raw/template',
        };
        var a = document.createElement('a');
        a.href = urls[kind] || urls.inventory;
        a.click();
    };

    window.submitDataImport = async function () {
        var kind = window._importKind || 'inventory';
        var fileInput = document.getElementById('dataImportFile');
        var mode = document.getElementById('dataImportMode').value;
        var statusEl = document.getElementById('dataImportStatus');
        if (!fileInput.files || !fileInput.files[0]) {
            statusEl.textContent = '请选择 Excel 文件';
            return;
        }
        var urls = {
            dimoldb: '/api/dimoldb/import',
            inventory: '/api/inventory/import_excel',
            raw: '/api/raw/import',
        };
        var fd = new FormData();
        fd.append('file', fileInput.files[0]);
        fd.append('import_mode', mode);
        if (kind === 'inventory') fd.append('product_type', 'zhengsquare');
        statusEl.textContent = '上传中…';
        try {
            var res = await fetch(urls[kind], { method: 'POST', body: fd });
            var data = await res.json();
            if (data.success) {
                statusEl.textContent = '✅ ' + (data.message || '完成');
                if (kind === 'dimoldb' && typeof loadDimoldbList === 'function')
                    loadDimoldbList(1, true);
                if (kind === 'inventory' && typeof loadInventory === 'function') loadInventory(1);
                if (kind === 'raw' && typeof loadRaw === 'function') loadRaw();
            } else {
                statusEl.textContent = '❌ ' + (data.error || '失败');
            }
        } catch (e) {
            statusEl.textContent = '❌ ' + e.message;
        }
    };
})();
