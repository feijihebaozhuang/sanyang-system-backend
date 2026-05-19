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

    window.sanitizeSkuAttrs = function (text) {
        if (!text) return '';
        return String(text)
            .replace(
                /(?:规格|尺寸|材质硬度等级|颜色分类|材质|颜色|硬度等级|硬度)[:：]\s*/gi,
                ''
            )
            .replace(/[;；]+\s*/g, ' ')
            .replace(/\s{2,}/g, ' ')
            .trim();
    };

    window.prodDisplayAttrs = function (item) {
        if (!item) return '—';
        var plain = (item.production_spec || '').trim();
        if (plain) return plain;
        var raw = (item.display || item.platform_attrs || item.spec || '').trim();
        return window.sanitizeSkuAttrs(raw) || raw || '—';
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
            renderProdDashboard([]);
            var stEl = document.getElementById('prodStats');
            if (stEl) stEl.textContent = '—';
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

    window.renderProdDashboard = function (orders) {
        orders = orders || [];
        var tbl = document.getElementById('prodTable');
        if (!tbl) return;
        if (!orders.length) {
            tbl.innerHTML =
                '<tr><td colspan="11" style="text-align:center;padding:30px;color:#999;">暂无匹配的订单</td></tr>';
            prodRenderMobileCards([]);
            if (typeof updateBatchPrintBtn === 'function') updateBatchPrintBtn();
            return;
        }
        var esc = function (s) {
            return String(s || '')
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;');
        };
        try {
            var html = orders
                .map(function (o) {
                    var printBadge = o.printed
                        ? '<span style="color:#52c41a;font-weight:bold;">✅ 已打印</span>'
                        : '<span style="color:#e94560;font-weight:bold;">⭕ 未打印</span>';
                    var itemsHtml = '';
                    var specs = o.full_items || [];
                    if (!specs.length) {
                        itemsHtml = '<span style="color:#999;font-size:11px;">—</span>';
                    } else {
                        var lines = [];
                        specs.forEach(function (item, idx) {
                            var attrs = window.prodDisplayAttrs(item);
                            var prodLine =
                                typeof renderProductionSpecHtml === 'function'
                                    ? renderProductionSpecHtml(item, true)
                                    : '';
                            var mcHtml =
                                typeof renderMaterialCalcHtml === 'function'
                                    ? renderMaterialCalcHtml(item)
                                    : '';
                            var calcBtn =
                                '<button type="button" onclick="calcMaterialLine(\'' +
                                o.so_id +
                                '\',' +
                                idx +
                                ',event)" style="margin-left:4px;padding:1px 6px;font-size:10px;background:#722ed1;color:#fff;border:none;border-radius:3px;cursor:pointer;">算料</button>';
                            lines.push(
                                '<div style="font-size:11px;line-height:1.5;padding:2px 0;border-bottom:' +
                                    (idx < specs.length - 1 ? '1px dashed #eee' : 'none') +
                                    ';white-space:normal;word-break:break-word;">' +
                                    '<span style="color:#333;">' +
                                    esc(attrs) +
                                    '</span> ' +
                                    '<strong style="color:#e94560;">×' +
                                    (item.qty || 0) +
                                    '</strong> ' +
                                    '<span style="font-size:10px;' +
                                    (item.has_stock ? 'color:#52c41a;' : 'color:#e94560;') +
                                    'font-weight:500;">' +
                                    (item.has_stock ? '✅现货' : '📦需生产') +
                                    '</span>' +
                                    calcBtn +
                                    prodLine +
                                    mcHtml +
                                    '</div>'
                            );
                        });
                        itemsHtml = lines.join('');
                    }
                    var typeClass = 'tag-default';
                    if (o.product_type === '纸箱') typeClass = 'tag-warning';
                    else if (o.product_type === '扣底盒') typeClass = 'tag-info';
                    else if (o.product_type === '现货') typeClass = 'tag-success';
                    var currentStep = '—';
                    var pct = o.progress || 0;
                    if (o.steps && o.steps.length) {
                        var activeStep = o.steps.find(function (s) {
                            return s.active;
                        });
                        var doneAll = o.steps.every(function (s) {
                            return s.done;
                        });
                        currentStep = doneAll
                            ? '✅ 已完成'
                            : activeStep
                              ? activeStep.name
                              : '—';
                    }
                    var barColor = pct >= 100 ? '#52c41a' : '#1677ff';
                    var progressHtml =
                        '<div style="display:flex;align-items:center;gap:4px;min-width:80px;">' +
                        '<div style="flex:1;height:5px;background:#f0f0f0;border-radius:3px;overflow:hidden;">' +
                        '<div style="height:100%;width:' +
                        pct +
                        '%;background:' +
                        barColor +
                        ';border-radius:3px;"></div>' +
                        '</div><span style="font-size:10px;color:#888;white-space:nowrap;">' +
                        pct +
                        '%</span></div>';
                    return (
                        '<tr onclick="showProdDetailBySoId(\'' +
                        o.so_id +
                        '\')" style="cursor:pointer;">' +
                        '<td style="width:36px;" onclick="event.stopPropagation()">' +
                        '<input type="checkbox" class="prod-checkbox" value="' +
                        o.so_id +
                        '" onchange="updateBatchPrintBtn()">' +
                        '</td>' +
                        '<td style="font-size:11px;">' +
                        printBadge +
                        '</td>' +
                        '<td style="font-family:monospace;font-size:12px;color:#1677ff;font-weight:600;">' +
                        esc(o.so_id || '') +
                        '</td>' +
                        '<td style="font-size:12px;">' +
                        esc(o.shop || '') +
                        '</td>' +
                        '<td><span class="tag ' +
                        typeClass +
                        '">' +
                        esc(o.product_type || '') +
                        '</span></td>' +
                        '<td style="font-size:12px;max-width:200px;overflow-wrap:break-word;word-break:break-word;">' +
                        itemsHtml +
                        '</td>' +
                        '<td><strong>' +
                        (o.qty || 0) +
                        '</strong></td>' +
                        '<td style="font-size:11px;color:#1677ff;">' +
                        currentStep +
                        '</td>' +
                        '<td style="min-width:80px;">' +
                        progressHtml +
                        '</td>' +
                        '<td style="font-size:11px;color:#666;">' +
                        esc(o.created || '') +
                        '</td>' +
                        '<td style="font-size:11px;">' +
                        '<button onclick="event.stopPropagation();printSingleProd(\'' +
                        o.so_id +
                        '\')" style="padding:2px 8px;background:#52c41a;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:11px;">🖨️</button> ' +
                        '<button onclick="event.stopPropagation();initSingleFlow(\'' +
                        o.so_id +
                        '\')" style="padding:2px 8px;background:#1677ff;color:#fff;border:none;border-radius:3px;cursor:pointer;font-size:11px;">📋</button>' +
                        '</td></tr>'
                    );
                })
                .join('');
            tbl.innerHTML = html.replace(/motion\.div/g, 'div');
        } catch (e) {
            tbl.innerHTML =
                '<tr><td colspan="11" style="color:#e94560;">渲染错误: ' +
                esc(e.message) +
                '</td></tr>';
        }
        prodRenderMobileCards(orders);
        if (typeof updateBatchPrintBtn === 'function') updateBatchPrintBtn();
    };

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

    window._prodCurrentAnnId = null;

    window.renderMaterialCalcHtml = function (item) {
        var mc = item.material_calc || {};
        var st = mc.status || item.material_status || 'pending';
        var icon =
            st === 'done'
                ? '✅'
                : st === 'shortage'
                  ? '⚠️缺料'
                  : st === 'error'
                    ? '❌'
                    : '⏳';
        if (st !== 'done' && st !== 'error' && st !== 'shortage') {
            return '<div style="font-size:10px;color:#888;margin-top:2px;">算料 ' + icon + '</div>';
        }
        if (st === 'shortage') {
            return (
                '<div style="font-size:10px;color:#cf1322;font-weight:600;margin-top:2px;">' +
                icon +
                ' ' +
                (mc.error || '缺料，请自行决定') +
                '</div>'
            );
        }
        var paper = mc.paper_display || mc.paper_spec || (mc.paper && mc.paper.paper_spec) || '—';
        var boards = mc.boards_needed != null ? mc.boards_needed : '—';
        var per = mc.sheets_per_board != null ? mc.sheets_per_board : '—';
        var dm =
            mc.dimoldb_label ||
            mc.dimoldb_id ||
            mc.dimoldb_code ||
            (mc.dimoldb && mc.dimoldb.dimoldb_id) ||
            '—';
        return (
            '<div style="font-size:10px;color:#555;margin-top:2px;line-height:1.4;">' +
            icon +
            ' 纸板：' +
            paper +
            '；' +
            boards +
            '张；开' +
            per +
            '个/张；刀模 ' +
            dm +
            '</div>'
        );
    };

    window.batchCalcMaterialOrdersImpl = async function (ids) {
        var statsEl = document.getElementById('prodStats');
        var oldStats = statsEl ? statsEl.textContent : '';
        try {
            if (statsEl) statsEl.textContent = '算料中…';
            var res = await fetch('/api/production/calc-material/batch', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ so_ids: ids }),
            });
            var data = await res.json();
            if (!data.success) throw new Error(data.error || '批量算料失败');
            alert(
                '批量算料完成\n成功行: ' +
                    (data.lines_done || 0) +
                    '\n失败行: ' +
                    (data.lines_failed || 0)
            );
            loadProdDashboard(false);
        } catch (e) {
            alert('批量算料失败：' + e.message);
        } finally {
            if (statsEl && oldStats) statsEl.textContent = oldStats;
        }
    };

    window.calcMaterialLine = async function (soId, lineIdx, ev) {
        if (ev && ev.stopPropagation) ev.stopPropagation();
        try {
            var res = await fetch('/api/production/calc-material', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ so_id: soId, line_index: lineIdx }),
            });
            var data = await res.json();
            if (!data.success) throw new Error(data.error || '算料失败');
            loadProdDashboard(false);
        } catch (e) {
            alert('算料失败：' + e.message);
        }
    };

    window.loadProductionAnnouncements = async function () {
        var bar = document.getElementById('prodAnnouncementBar');
        if (!bar) return;
        try {
            var res = await fetch('/api/production/announcements');
            var data = await res.json();
            if (!data.success || !data.announcements || !data.announcements.length) {
                bar.style.display = 'none';
                return;
            }
            var ann = data.announcements[0];
            window._prodCurrentAnnId = ann.id;
            document.getElementById('prodAnnTitle').textContent = ann.title || '公告';
            document.getElementById('prodAnnContent').textContent = ann.content || '';
            var badge = document.getElementById('prodAnnBadge');
            if (badge) badge.style.display = ann.is_read ? 'none' : 'inline';
            var editBtn = document.getElementById('prodAnnEditBtn');
            if (editBtn) editBtn.style.display = data.can_edit ? 'inline-block' : 'none';
            bar.style.display = 'block';
            if (!ann.is_read && !sessionStorage.getItem('sy_ann_popup_' + ann.id)) {
                sessionStorage.setItem('sy_ann_popup_' + ann.id, '1');
                alert('📢 ' + (ann.title || '公告') + '\n\n' + (ann.content || ''));
            }
        } catch (e) {
            bar.style.display = 'none';
        }
    };

    window.markAnnouncementRead = async function () {
        var id = window._prodCurrentAnnId;
        if (!id) return;
        try {
            await fetch('/api/production/announcements/' + id + '/read', { method: 'POST' });
            var badge = document.getElementById('prodAnnBadge');
            if (badge) badge.style.display = 'none';
        } catch (e) {}
    };

    window.openAnnouncementEditor = async function () {
        var title = prompt('公告标题', document.getElementById('prodAnnTitle').textContent || '');
        if (title === null) return;
        var content = prompt('公告内容（全员可见）', document.getElementById('prodAnnContent').textContent || '');
        if (content === null) return;
        try {
            var res = await fetch('/api/production/announcements', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    id: window._prodCurrentAnnId,
                    title: title,
                    content: content,
                }),
            });
            var data = await res.json();
            if (!data.success) throw new Error(data.error || '保存失败');
            loadProductionAnnouncements();
            alert('公告已发布');
        } catch (e) {
            alert('保存失败：' + e.message);
        }
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
