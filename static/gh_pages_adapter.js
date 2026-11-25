/**
 * GitHub Pages Static Adapter for Ihyaa-Lands (Naama Platform)
 * Intercepts /api/* fetch calls when hosted statically (github.io or file://)
 * and serves pre-rendered JSON + localStorage state so interactive flows work without a Python backend.
 */
(function () {
    const isStaticHost =
        window.location.hostname.endsWith('github.io') ||
        window.location.protocol === 'file:' ||
        window.IHYAA_STATIC_MODE === true;

    if (!isStaticHost) return;

    // Determine relative base prefix based on current script src
    const scripts = document.getElementsByTagName('script');
    let basePrefix = '';
    for (let i = 0; i < scripts.length; i++) {
        const src = scripts[i].getAttribute('src') || '';
        if (src.includes('gh_pages_adapter.js')) {
            basePrefix = src.replace(/static\/gh_pages_adapter\.js.*$/, '');
            break;
        }
    }

    const STORAGE_KEY = 'ihyaa_static_state_v1';
    function loadState() {
        try {
            return JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}');
        } catch (e) {
            return {};
        }
    }
    function saveState(st) {
        try {
            localStorage.setItem(STORAGE_KEY, JSON.stringify(st));
        } catch (e) {}
    }

    let cachedReviews = null;
    async function getReviewsMap() {
        if (cachedReviews) return cachedReviews;
        try {
            const res = await originalFetch(basePrefix + 'static/data/farms_review.json');
            cachedReviews = await res.json();
        } catch (e) {
            cachedReviews = {};
        }
        return cachedReviews;
    }

    const originalFetch = window.fetch.bind(window);

    function jsonResponse(obj, status = 200) {
        return new Response(JSON.stringify(obj), {
            status,
            headers: { 'Content-Type': 'application/json; charset=utf-8' }
        });
    }

    window.fetch = async function (input, init) {
        const url = typeof input === 'string' ? input : (input && input.url) || '';

        // 1. GeoJSON for GIS Map
        if (url.includes('/api/farms/geojson')) {
            return originalFetch(basePrefix + 'static/data/geojson.json');
        }

        // 2. Farm review modal data
        const reviewMatch = url.match(/\/api\/admin\/farms\/(\d+)\/review/);
        if (reviewMatch) {
            const farmId = reviewMatch[1];
            const reviews = await getReviewsMap();
            const state = loadState();
            const override = (state.farmOverrides || {})[farmId];
            let entry = reviews[farmId];
            if (!entry && (state.registeredFarms || {})[farmId]) {
                entry = { success: true, farm: state.registeredFarms[farmId], visits: [] };
            }
            if (!entry) {
                return jsonResponse({ success: false, message: 'الطلب غير موجود في النسخة التجريبية' }, 404);
            }
            const mergedFarm = Object.assign({}, entry.farm, override || {});
            return jsonResponse({ success: true, farm: mergedFarm, visits: entry.visits || [] });
        }

        // 3. Admin Inbox Actions (3 Roles)
        if (url.includes('/api/admin/inbox/action')) {
            const fd = init && init.body instanceof FormData ? init.body : new FormData();
            const farmId = fd.get('farm_id');
            const role = fd.get('role') || 'auditor';
            const action = fd.get('action') || '';
            const notes = fd.get('notes') || '';
            const supportPath = fd.get('support_path') || '';

            const state = loadState();
            state.farmOverrides = state.farmOverrides || {};
            const cur = state.farmOverrides[farmId] || {};

            let newStatus = cur.status || 'مسجل';
            let msg = 'تم تنفيذ الإجراء وحفظه بنجاح.';
            if (role === 'auditor') {
                if (action === 'approve_audit') {
                    newStatus = 'محال للمعاينة الميدانية';
                    msg = 'تم اعتماد التدقيق المكتبي وإحالة الطلب إلى فني الزيارة الميدانية.';
                } else if (action === 'request_info') {
                    newStatus = 'نواقص وثائق';
                    msg = 'تم إشعار المستفيد بالنواقص المطلوبة.';
                } else if (action === 'reject') {
                    newStatus = 'مرفوض من الفرع';
                    msg = 'تم رفض الطلب وحفظ السبب في سجل المزرعة.';
                }
            } else if (role === 'inspector') {
                if (action === 'schedule_visit') {
                    msg = 'تمت جدولة موعد الزيارة الميدانية بنجاح.';
                } else if (action === 'submit_inspection_report') {
                    newStatus = 'تمت الزيارة الميدانية';
                    msg = 'تم رفع التقرير الميداني وإحالة الطلب إلى مدير الفرع للاعتماد.';
                }
            } else if (role === 'manager') {
                if (action === 'approve_plan') {
                    newStatus = 'جاري التأهيل';
                    msg = 'تم إصدار قرار الاعتماد النهائي وتخصيص مسار الدعم بنجاح!';
                } else if (action === 'return_for_reinspection') {
                    newStatus = 'محال للمعاينة الميدانية';
                    msg = 'تمت إعادة الطلب إلى فني الميدان لإعادة المعاينة.';
                }
            }

            state.farmOverrides[farmId] = Object.assign({}, cur, {
                status: newStatus,
                assigned_partner_name: supportPath || cur.assigned_partner_name
            });
            saveState(state);
            return jsonResponse({ success: true, message: msg, farm_id: farmId, new_status: newStatus });
        }

        // 4. Register Farm
        if (url.includes('/api/farms/register')) {
            const code = 'FRM-' + Math.floor(2000 + Math.random() * 7000);
            return jsonResponse({
                success: true,
                code,
                message: 'تم تسجيل طلبكم بنجاح برقم ' + code + ' (وضع العرض الثابت)'
            });
        }

        // 5. Nafath Login simulation
        if (url.includes('/api/nafath/initiate')) {
            return jsonResponse({ success: true, random_number: Math.floor(10 + Math.random() * 89) });
        }
        if (url.includes('/api/nafath/confirm')) {
            return jsonResponse({ success: true, redirect_url: basePrefix + 'my-requests.html' });
        }

        // 6. Generic admin/advisory/partner POSTs
        if (url.includes('/api/')) {
            return jsonResponse({ success: true, message: 'تم الحفظ بنجاح (وضع العرض الثابت على GitHub Pages)' });
        }

        return originalFetch(input, init);
    };
})();
