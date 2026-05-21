/* 生产端：打单分页/缓存、WPS嵌入、通用导入 */
(function () {
    const PROD_CACHE_KEY = 'sy_prod_dashboard_v3';
    const WPS_KDOCS_URL = 'https://www.kdocs.cn/l/cdIlitRGKpMw';

    window._prodPage = 1;
    window._prodPageSize = 15;
    window._prodTotalPages = 1;
    window._prodDashboardOrders = window._prodDashboardOrders || [];
    window._prodOrderDetail = window._prodOrderDetail || {};
    window._dimoldbNameMap = window._dimoldbNameMap || {};
    window._dimoldbNameMapPromise = null;

    window.ensureDimoldbNameMap = function () {
        if (window._dimoldbNameMapPromise) return window._dimoldbNameMapPromise;
        window._dimoldbNameMapPromise = (async function () {
            try {
                var page = 1;
                var totalPages = 1;
                while (page <= totalPages) {
                    var res = await fetch(
                        '/api/dimoldb?page=' + page + '&page_size=200'
                    );
                    var data = await res.json();
                    if (!data.success) break;
                    (data.data || []).forEach(function (d) {
                        if (d && d.id) {
                            var code = (d.code || '').trim();
                            var name = (d.name || '').trim();
                            var isDimSize =
                                name && /\d+(?:\.\d+)?\s*[*×xX]\s*\d+/.test(name);
                            window._dimoldbNameMap[d.id] =
                                code || (!isDimSize && name) || String(d.id);
                        }
                    });
                    totalPages = data.total_pages || 1;
                    page += 1;
                }
            } catch (e) {
                /* ignore */
            }
        })();
        return window._dimoldbNameMapPromise;
    };

    /** 刀模库展示编码（code / id，不用尺寸串 name） */
    window.prodDimoldbDisplayCode = function (idOrMc) {
        if (!idOrMc) return '';
        if (typeof idOrMc === 'object') {
            var mc = idOrMc;
            var code = (mc.dimoldb_code || '').trim();
            if (code) return code;
            var id =
                mc.dimoldb_id ||
                (mc.dimoldb && mc.dimoldb.dimoldb_id) ||
                '';
            if (id && window._dimoldbNameMap[id]) {
                return window._dimoldbNameMap[id];
            }
            var label = (mc.dimoldb_label || '').trim();
            if (label && label.indexOf('dm_') !== 0) return label;
            return id || '';
        }
        var id = String(idOrMc).trim();
        if (!id) return '';
        return window._dimoldbNameMap[id] || id;
    };
    window.prodDimoldbDisplayName = window.prodDimoldbDisplayCode;

    window.prodCopyText = function (text, ev) {
        if (ev && ev.stopPropagation) ev.stopPropagation();
        var s = String(text || '').trim();
        if (!s) return;
        var done = function () {
            if (typeof showToast === 'function') {
                showToast('已复制');
            }
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(s).then(done).catch(function () {
                window.prompt('复制', s);
            });
        } else {
            window.prompt('复制', s);
        }
    };

    window.prodCopySoId = function (soId, ev) {
        window.prodCopyText(soId, ev);
    };

    window.openWpsKdocsEmbed = function () {
        if (typeof switchTopPage === 'function') {
            var fake = { classList: { add: function () {}, remove: function () {} } };
            document.querySelectorAll('.page-section').forEach(function (p) {
                p.classList.remove('active');
            });
            var pg = document.getElementById('page-wps-kdocs');
            if (pg) {
                pg.classList.add('active');
                var iframe = document.getElementById('wpsKdocsFrame');
                if (iframe) {
                    var ds = iframe.getAttribute('data-src');
                    if (ds && (!iframe.src || iframe.src === 'about:blank')) {
                        iframe.src = ds;
                    }
                }
            }
            window.scrollTo({ top: 0, behavior: 'smooth' });
        }
    };

    window.bindProdPagerEvents = function () {
        if (window._prodPagerDocBound) return;
        window._prodPagerDocBound = true;
        document.addEventListener(
            'click',
            function (ev) {
                var btn = ev.target.closest('[data-prod-page]');
                if (!btn || btn.disabled) return;
                if (!btn.closest('#prodPagination')) return;
                ev.preventDefault();
                ev.stopPropagation();
                window.prodGoPage(btn.getAttribute('data-prod-page'));
            },
            true
        );
        document.addEventListener('change', function (ev) {
            if (ev.target && ev.target.id === 'prodPageSizeSel') {
                window.prodChangePageSize(ev.target.value);
            }
        });
        document.addEventListener('keydown', function (ev) {
            if (
                ev.target &&
                ev.target.id === 'prodPageInput' &&
                ev.key === 'Enter'
            ) {
                ev.preventDefault();
                window.prodGoPageInput();
            }
        });
    };

    window.prodRenderPagination = function () {
        var el = document.getElementById('prodPagination');
        if (!el) return;
        bindProdPagerEvents();
        var p = window._prodPage;
        var tp = window._prodTotalPages;
        var prevP = p - 1;
        var nextP = p + 1;
        el.innerHTML =
            '<div class="prod-pager">' +
            '<button type="button" data-prod-page="' +
            prevP +
            '" ' +
            (p <= 1 ? 'disabled' : '') +
            ' onclick="window.prodGoPage(' +
            prevP +
            ');return false;">上一页</button>' +
            '<span>第 <input type="number" id="prodPageInput" min="1" max="' +
            tp +
            '" value="' +
            p +
            '" style="width:48px;text-align:center;padding:4px;"> / ' +
            tp +
            ' 页</span>' +
            '<button type="button" data-prod-page="' +
            nextP +
            '" ' +
            (p >= tp ? 'disabled' : '') +
            ' onclick="window.prodGoPage(' +
            nextP +
            ');return false;">下一页</button>' +
            '<select id="prodPageSizeSel" style="margin-left:8px;padding:4px;">' +
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
        bindProdPagerEvents();
    };

    window.prodGoPage = function (n) {
        n = parseInt(n, 10);
        if (isNaN(n) || n < 1) n = 1;
        if (n > window._prodTotalPages) n = window._prodTotalPages;
        window._prodPage = n;
        window.loadProdDashboard(false, {
            forceRefresh: true,
            skipCache: true,
            paging: true,
        });
    };

    window.prodGoPageInput = function () {
        var inp = document.getElementById('prodPageInput');
        window.prodGoPage(inp ? inp.value : 1);
    };

    window.prodChangePageSize = function (v) {
        window._prodPageSize = parseInt(v, 10) || 15;
        window._prodPage = 1;
        window.loadProdDashboard(false, {
            forceRefresh: true,
            skipCache: true,
            paging: true,
        });
    };

    window.prodApplyCachedDashboard = function () {
        try {
            var raw = sessionStorage.getItem(PROD_CACHE_KEY);
            if (!raw) return false;
            var data = JSON.parse(raw);
            if (!data.orders || !data.orders.length) return false;
            var cachedPage = parseInt(data.page, 10) || 1;
            if (cachedPage !== window._prodPage) return false;
            window._prodDashboardOrders = data.orders;
            window._prodTotalPages = data.total_pages || 1;
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
        var det = item.production_spec_detail || {};
        var missing = det.dimensions_missing || [];
        if (missing.length) {
            var raw =
                det.platform_spec_raw ||
                det.line1 ||
                item.platform_attrs ||
                item.spec ||
                item.display ||
                '';
            raw = String(raw).trim();
            if (raw) return raw;
        }
        var line =
            item.production_spec ||
            det.line2 ||
            det.formatted ||
            item.display ||
            '';
        line = String(line).trim();
        if (!line) {
            var fallback =
                det.platform_spec_raw ||
                det.line1 ||
                item.spec ||
                item.display ||
                '';
            line = String(fallback).trim();
        }
        return line || '—';
    };

    window.renderProductionSpecHtml = function (item, compact) {
        if (!item) return '';
        var fs = compact ? '12px' : '13px';
        var line = prodDisplayAttrs(item);
        if (!line || line === '—') {
            return (
                '<div style="font-size:' +
                fs +
                ';color:#999;">规格未识别</div>'
            );
        }
        return (
            '<div style="font-size:' +
            fs +
            ';font-weight:600;color:#262626;line-height:1.5;">' +
            prodEscHtml(line) +
            '</div>'
        );
    };

    window.prodEscHtml = function (s) {
        return String(s || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;');
    };

    /** 第三行：刀模编码（刀模库 code/id）+ 成品库存 */
    window.renderDimoldbStockHtml = function (item, compact) {
        if (!item) return '';
        var fs = compact ? '10px' : '11px';
        var mt = compact ? '2px' : '3px';
        var mc = item.material_calc || {};
        var dmCode = '';
        if (mc.dimoldb_code || mc.dimoldb_id) {
            dmCode = prodDimoldbDisplayCode(mc);
        }
        if (!dmCode && item.dimoldb_code) {
            dmCode = String(item.dimoldb_code).trim();
        }
        if (!dmCode && item.dimoldb_id) {
            dmCode = prodDimoldbDisplayCode(item.dimoldb_id);
        }
        var dmLabel;
        if (item.dimoldb_skip) {
            dmLabel = '无需刀模';
        } else if (dmCode) {
            dmLabel = dmCode;
        } else if ((item.production_spec_detail || {}).is_placeholder) {
            dmLabel = '定制/无规格';
        } else {
            dmLabel = '未匹配';
        }
        var stockQty = parseInt(item.stock_qty, 10);
        if (isNaN(stockQty)) stockQty = 0;
        var stockSuffix =
            stockQty > 0 && item.has_stock
                ? stockQty + '（✅现货）'
                : stockQty > 0
                  ? stockQty + '（需生产）'
                  : '0（需生产）';
        return (
            '<div style="font-size:' +
            fs +
            ';margin-top:' +
            mt +
            ';line-height:1.45;color:#595959;">' +
            '<span style="color:#888;">刀模编码：</span>' +
            '<span style="font-weight:600;color:#262626;">' +
            prodEscHtml(dmLabel) +
            '</span>' +
            '&nbsp;&nbsp;&nbsp;' +
            '<span style="color:#888;">库存：</span>' +
            '<span style="font-weight:600;color:' +
            (stockQty > 0 && item.has_stock ? '#52c41a' : '#e94560') +
            ';">' +
            prodEscHtml(stockSuffix) +
            '</span></div>'
        );
    };

    /**
     * 打单规格四层块：原文 → 识别 → 刀模/库存 → 算料
     * @param {object} opts { compact, calcBtnHtml }
     */
    window.renderProdItemSpecBlock = function (item, opts) {
        opts = opts || {};
        var compact = !!opts.compact;
        var line2 =
            typeof renderProductionSpecHtml === 'function'
                ? renderProductionSpecHtml(item, compact)
                : '';
        var line3 =
            typeof renderDimoldbStockHtml === 'function'
                ? renderDimoldbStockHtml(item, compact)
                : '';
        var line4 =
            typeof renderMaterialCalcHtml === 'function'
                ? renderMaterialCalcHtml(item)
                : '';
        var extra = opts.calcBtnHtml || '';
        return (
            '<div style="line-height:1.45;white-space:normal;word-break:break-word;">' +
            line2 +
            line3 +
            line4 +
            (extra ? '<div style="margin-top:3px;">' + extra + '</div>' : '') +
            '</div>'
        );
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

    window.loadProdDashboard = async function (resetPage, options) {
        options = options || {};
        if (resetPage === true) window._prodPage = 1;
        window.ensureDimoldbNameMap();
        var pageWanted = window._prodPage;
        window._prodDashReqSeq = (window._prodDashReqSeq || 0) + 1;
        var reqId = window._prodDashReqSeq;
        var hadCache = false;
        if (!options.skipCache && !options.paging && window._prodPage === 1) {
            hadCache = window.prodApplyCachedDashboard();
        }
        var stEl = document.getElementById('prodStats');
        if (!hadCache && stEl) {
            stEl.textContent =
                '加载第 ' + pageWanted + ' 页…（共 ' + (window._prodTotalPages || '?') + ' 页）';
        }
        try {
            var qs = window.prodBuildDashboardQuery();
            if (options.forceRefresh || options.paging || window._prodPage > 1) {
                qs += (qs ? '&' : '') + 'refresh=1';
            }
            if (options.paging) {
                qs += (qs ? '&' : '') + '_ts=' + Date.now();
            }
            var fetchFn =
                typeof SY_AUTH !== 'undefined' && SY_AUTH.apiFetch
                    ? SY_AUTH.apiFetch
                    : fetch;
            var res = await fetchFn('/api/production/dashboard?' + qs);
            if (reqId !== window._prodDashReqSeq) return;
            var data = await res.json();
            if (!data.success) throw new Error(data.error || '加载失败');
            var respPage = parseInt(data.page, 10);
            if (isNaN(respPage)) respPage = pageWanted;
            if (respPage !== pageWanted) return;
            window._prodMappingData =
                data.material_mapping || data.production_material_mapping || [];
            window._prodDashboardOrders = data.orders || [];
            window._prodTotalPages = data.total_pages || 1;
            window._prodPage = data.page || pageWanted;
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
            window.renderProdDashboard(data.orders);
            window.prodRenderPagination();
            var tbl = document.getElementById('prodTable');
            if (tbl && tbl.closest('.table-wrap')) {
                tbl.closest('.table-wrap').scrollTop = 0;
            }
        } catch (e) {
            if (!hadCache && stEl) {
                stEl.textContent = '加载失败';
            }
            if (!hadCache) {
                var tblErr = document.getElementById('prodTable');
                if (tblErr) {
                    tblErr.innerHTML =
                        '<tr><td colspan="11" style="color:#e94560;text-align:center;padding:30px;">❌ ' +
                        e.message +
                        '</td></tr>';
                }
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
                            var calcBtn =
                                '<button type="button" onclick="calcMaterialLine(\'' +
                                o.so_id +
                                '\',' +
                                idx +
                                ',event)" style="margin-left:4px;padding:1px 6px;font-size:10px;background:#722ed1;color:#fff;border:none;border-radius:3px;cursor:pointer;">算料</button>';
                            var block =
                                typeof renderProdItemSpecBlock === 'function'
                                    ? renderProdItemSpecBlock(item, {
                                          compact: true,
                                          calcBtnHtml: calcBtn,
                                      })
                                    : esc(window.prodDisplayAttrs(item));
                            lines.push(
                                '<div style="font-size:11px;padding:2px 0;border-bottom:' +
                                    (idx < specs.length - 1 ? '1px dashed #eee' : 'none') +
                                    ';">' +
                                    block +
                                    '</div>'
                            );
                        });
                        itemsHtml = lines.join('');
                    }
                    var typeClass = 'tag-default';
                    if (o.has_stock) typeClass = 'tag-success';
                    else if (o.product_type === '纸箱') typeClass = 'tag-warning';
                    else if (o.product_type === '扣底盒') typeClass = 'tag-info';
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
                        '<td style="font-family:monospace;font-size:12px;" onclick="event.stopPropagation()">' +
                        '<span style="color:#1677ff;font-weight:600;cursor:pointer;text-decoration:underline dotted;" ' +
                        'title="点击复制内部单号" onclick="prodCopySoId(\'' +
                        esc(o.so_id || '') +
                        '\',event)">' +
                        esc(o.so_id || '') +
                        '</span></td>' +
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
        var psd = item.production_spec_detail || {};
        if (st === 'pending' || st === 'error') {
            var miss =
                item.dimensions_missing ||
                psd.dimensions_missing ||
                [];
            if (!psd.dimensions_ok && miss.length) {
                return (
                    '<div style="font-size:10px;color:#cf1322;font-weight:600;margin-top:2px;line-height:1.45;">⚠️ 规格缺少' +
                    prodEscHtml(miss.join('、')) +
                    '，无法算料（需长宽高齐全）</div>'
                );
            }
        }
        if (st !== 'done' && st !== 'error' && st !== 'shortage') {
            return '';
        }
        if (st === 'shortage') {
            var err = (mc.shortage_detail || mc.error || '').trim();
            var msg =
                err.indexOf('缺料') === 0
                    ? err
                    : '缺料：' + (err || '未找到合适纸板规格，请员工自行决定');
            var pl = mc.paper_l_inch;
            var pw = mc.paper_w_inch;
            var extra =
                pl && pw
                    ? '（需纸长' +
                      prodEscHtml(String(pl)) +
                      '×纸度' +
                      prodEscHtml(String(pw)) +
                      '英寸）'
                    : '';
            return (
                '<div style="font-size:10px;color:#cf1322;font-weight:600;margin-top:2px;line-height:1.45;">⚠️' +
                prodEscHtml(msg) +
                extra +
                '</div>'
            );
        }
        if (st === 'error') {
            return (
                '<div style="font-size:10px;color:#cf1322;font-weight:600;margin-top:2px;">❌ ' +
                (mc.error || '算料失败') +
                '</div>'
            );
        }
        var paper = mc.paper_display || mc.paper_spec || (mc.paper && mc.paper.paper_spec) || '—';
        var boards = mc.boards_needed != null ? mc.boards_needed : '—';
        var per = mc.sheets_per_board != null ? mc.sheets_per_board : '—';
        return (
            '<div style="font-size:10px;color:#389e0d;font-weight:500;margin-top:2px;line-height:1.45;">✅ 纸板：' +
            prodEscHtml(paper) +
            '；' +
            boards +
            '张；开' +
            per +
            '个/张</div>'
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

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', bindProdPagerEvents);
    } else {
        bindProdPagerEvents();
    }
})();
