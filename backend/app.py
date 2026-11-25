import os
import sys
import io
import sqlite3
import json
import random
from datetime import datetime
from typing import Optional, List, Any
from fastapi import FastAPI, Request, Form, HTTPException, Depends
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI(title="منصة إحياء المزارع المهملة - منظومة نما", version="2.5.0")
app.add_middleware(SessionMiddleware, secret_key="ihyaa_nafath_secure_key_2026_mewa")

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BASE_DIR, 'backend', 'ihyaa_platform.db')
TEMPLATES_DIR = os.path.join(BASE_DIR, 'frontend', 'templates')
STATIC_DIR = os.path.join(BASE_DIR, 'frontend', 'static')

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

def render_template(request: Request, name: str, context: dict = None, status_code: int = 200):
    if context is None:
        context = {}
    return templates.TemplateResponse(request=request, name=name, context=context, status_code=status_code)

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

# Helper: compute smart solution for newly registered farms
def generate_solution_for_farm(region, water, elec, status, area, prev_crop, social_sec):
    solutions = []
    has_water = any(w in str(water) for w in ['بئر', 'خزان', 'يوجد', 'نعم'])
    has_elec = any(e in str(elec) for e in ['يوجد', 'نعم', 'طاقة'])
    is_social = 'نعم' in str(social_sec)
    cost = 35000.0

    if not has_water:
        if region in ['الباحة', 'عسير']:
            solutions.append("حفر/تعميق بئر سطحي وتركيب خزان تجميع مياه أمطار جبلي")
            cost += 45000
        elif region in ['تبوك', 'الجوف', 'الحدود الشمالية', 'حائل']:
            solutions.append("حفر بئر ارتوازي وتأهيل خزان خرساني أرضي")
            cost += 60000
        else:
            solutions.append("إنشاء خزان مائي وتمديد خط تغذية ري موفر")
            cost += 25000
    else:
        solutions.append("صيانة البئر وتطهيره وتركيب مضخة غاطسة موفرة للطاقة")
        cost += 12000

    if not has_elec:
        solutions.append("تركيب منظومة طاقة شمسية مستقلة (10-15 كيلوواط) لتشغيل المضخات والإنارة")
        cost += 38000
    else:
        solutions.append("صيانة اللوحات وتفعيل العداد الزراعي المخصص")
        cost += 5000

    solutions.append("توريد وتركيب شبكة ري حديثة بالتنقيط (GR) مع فلاتر ذكية")
    cost += max(8000.0, float(area if area and area > 0 else 5000) * 1.5)

    if region in ['الباحة', 'عسير']:
        solutions.append("تزويد بـ 400 شتلة بن خولاني/صافي شدوي وشتلات رمان ولوز")
    elif region in ['المدينة المنورة', 'القصيم', 'الرياض']:
        solutions.append("تزويد بـ 150 فسيلة نخيل نسيجية عالية الجودة وأشجار حمضيات وسدر")
    elif region in ['المنطقة الشرقية']:
        solutions.append("إحلال 200 فسيلة نخيل خلاص الأحساء وأشجار كينوقاربوس مصدات رياح")
    elif region in ['جازان']:
        solutions.append("تزويد بشتلات مانجو عويس وتومي وبابايا معالجة")
    elif region in ['نجران']:
        solutions.append("توريد شتلات حمضيات نجرانية ونخيل ومصدات رياح")
    else:
        solutions.append("توريد 250 شتلة زيتون وفواكه صيفية ملائمة")

    if is_social:
        solutions.append("إدراج ضمن مسار الدعم التنموي والقرض الحسن (شركة أزكى/بنك التنمية)")
    else:
        solutions.append("مسار الشراكة التعاونية أو الاستثمار الأهلي للحيازات")

    if has_water and has_elec:
        priority = "أولوية 1 (جاهزية عالية - تأهيل سريع)"
    elif has_water or has_elec:
        priority = "أولوية 2 (جاهزية متوسطة - يحتاج استكمال)"
    else:
        priority = "أولوية 3 (جاهزية منخفضة - استصلاح شامل)"

    return priority, " + ".join(solutions), round(cost, 2)

# ==================== PUBLIC BENEFICIARY ROUTES ====================

@app.get("/", response_class=HTMLResponse)
@app.get("/services", response_class=HTMLResponse)
async def services_directory(request: Request, search: Optional[str] = None, category: Optional[str] = None):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT count(*) FROM farms")
    total_farms = c.fetchone()[0]
    c.execute("SELECT count(*) FROM farms WHERE status = 'مؤهلة ومنتجة'")
    rehab_farms = c.fetchone()[0]
    conn.close()

    logged_user = {
        "nid": request.session.get("user_nid"),
        "name": request.session.get("user_name"),
        "is_authenticated": request.session.get("logged_in", False)
    }

    return render_template(request, "services.html", {
        "total_farms": total_farms,
        "rehab_farms": rehab_farms,
        "logged_user": logged_user,
        "search": search or "",
        "category": category or "all"
    })

@app.get("/services/farm-rehab", response_class=HTMLResponse)
async def service_details(request: Request):
    logged_user = {
        "nid": request.session.get("user_nid"),
        "name": request.session.get("user_name"),
        "is_authenticated": request.session.get("logged_in", False)
    }
    return render_template(request, "service_details.html", {
        "logged_user": logged_user
    })

@app.get("/nafath/login", response_class=HTMLResponse)
async def nafath_login_page(request: Request, return_to: Optional[str] = None):
    # If already logged in, redirect to return_to or register
    if request.session.get("logged_in"):
        return RedirectResponse(url=return_to or "/register")
    return render_template(request, "nafath_login.html", {
        "return_to": return_to or "/register"
    })

@app.post("/api/nafath/initiate")
async def nafath_initiate(national_id: str = Form(...)):
    nid = national_id.strip()
    if not (nid.isdigit() and len(nid) == 10 and nid[0] in ['1', '2']):
        return JSONResponse({
            "success": False,
            "message": "يرجى إدخال رقم هوية وطنية أو إقامة صحيح مكون من 10 أرقام تبدأ بـ 1 أو 2"
        }, status_code=400)

    # Generate random 2-digit confirmation code
    code = random.randint(11, 99)
    return JSONResponse({
        "success": True,
        "code": code,
        "national_id": nid,
        "message": "تم إرسال طلب التحقق إلى تطبيق نفاذ"
    })

@app.post("/api/nafath/confirm")
async def nafath_confirm(
    request: Request,
    national_id: str = Form(...),
    farmer_name: Optional[str] = Form(None)
):
    nid = national_id.strip()
    # Mock user names based on id or default
    default_name = farmer_name or "عبدالله بن فهد الغامدي"
    if nid == "1234567890":
        default_name = "عطيه عبدالله"

    request.session["user_nid"] = nid
    request.session["user_name"] = default_name
    request.session["user_phone"] = "0554129876"
    request.session["user_social_security"] = "مسجل"
    request.session["logged_in"] = True

    return JSONResponse({
        "success": True,
        "redirect_url": "/register",
        "message": "تم التحقق بنجاح عبر منصة النفاذ الوطني الموحد"
    })

@app.get("/nafath/logout")
async def nafath_logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/")

DEFAULT_REGISTRIES = [
    {
        "registry_number": "SA-2026-104520",
        "region": "الباحة",
        "governorate": "بلجرشي",
        "city": "بلجرشي",
        "center": "مركز بني كبير",
        "village": "قرية الحدب",
        "farm_name": "مزرعة وادي الجنابين للتين والرمان",
        "area_m2": 12000,
        "expiry_date": "2027-11-15",
        "status": "سارٍ ومعتمد",
        "previous_crops": "بن شدوي، لوز بجلي، رمان، مشمش",
        "water_source": "بئر",
        "electricity_source": "لا يوجد",
        "road_type": "معبد",
        "latitude": 19.8542,
        "longitude": 41.5621,
        "maps_url": "https://maps.google.com/?q=19.8542,41.5621"
    },
    {
        "registry_number": "SA-2026-108934",
        "region": "مكة المكرمة",
        "governorate": "الطائف",
        "city": "الطائف",
        "center": "مركز الشفا",
        "village": "وادي عرضة",
        "farm_name": "مزرعة الشفا العطرية",
        "area_m2": 18500,
        "expiry_date": "2028-04-20",
        "status": "سارٍ ومعتمد",
        "previous_crops": "ورد طائفي، مشمش، تين، رمان",
        "water_source": "بئر",
        "electricity_source": "طاقة شمسية",
        "road_type": "معبد",
        "latitude": 21.1873,
        "longitude": 40.3214,
        "maps_url": "https://maps.google.com/?q=21.1873,40.3214"
    },
    {
        "registry_number": "SA-2026-112341",
        "region": "عسير",
        "governorate": "النماص",
        "city": "النماص",
        "center": "مركز بني بكر",
        "village": "قرية الحصن",
        "farm_name": "مزرعة مدرجات السروات",
        "area_m2": 9400,
        "expiry_date": "2027-08-10",
        "status": "سارٍ ومعتمد",
        "previous_crops": "قمح بلدي، لوز، تفاح بلدي",
        "water_source": "الأمطار",
        "electricity_source": "يوجد",
        "road_type": "غير معبد - ممهد",
        "latitude": 19.1234,
        "longitude": 42.1456,
        "maps_url": "https://maps.google.com/?q=19.1234,42.1456"
    },
    {
        "registry_number": "SA-2026-115782",
        "region": "الرياض",
        "governorate": "الدرعية",
        "city": "الدرعية",
        "center": "مركز العمارية",
        "village": "شعيب الحيسية",
        "farm_name": "مزرعة نجد التراثية",
        "area_m2": 25000,
        "expiry_date": "2028-01-30",
        "status": "سارٍ ومعتمد",
        "previous_crops": "نخيل خلاص، سدر، حمضيات، أعلاف",
        "water_source": "بئر",
        "electricity_source": "يوجد",
        "road_type": "معبد",
        "latitude": 24.8123,
        "longitude": 46.4215,
        "maps_url": "https://maps.google.com/?q=24.8123,46.4215"
    },
    {
        "registry_number": "SA-2026-119854",
        "region": "المدينة المنورة",
        "governorate": "العلا",
        "city": "العلا",
        "center": "مركز مغيراء",
        "village": "وادي القرى",
        "farm_name": "مزرعة واحة العلا القديمة",
        "area_m2": 32000,
        "expiry_date": "2027-06-18",
        "status": "سارٍ ومعتمد",
        "previous_crops": "نخيل برني، حمضيات، نعناع مديني",
        "water_source": "بئر",
        "electricity_source": "لا يوجد",
        "road_type": "معبد",
        "latitude": 26.6125,
        "longitude": 37.9234,
        "maps_url": "https://maps.google.com/?q=26.6125,37.9234"
    }
]

@app.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    logged_user = {
        "nid": request.session.get("user_nid", "1087452190"),
        "name": request.session.get("user_name", "عبدالله بن فهد الغامدي"),
        "phone": request.session.get("user_phone", "0554129876"),
        "social_security": request.session.get("user_social_security", "مسجل"),
        "is_authenticated": request.session.get("logged_in", False)
    }
    # If not authenticated via Nafath, redirect to Nafath login first
    if not logged_user["is_authenticated"]:
        return RedirectResponse(url="/nafath/login?return_to=/register")

    return render_template(request, "register.html", {
        "logged_user": logged_user,
        "registries": DEFAULT_REGISTRIES
    })

@app.get("/operations", response_class=HTMLResponse)
async def operations_portal_redirect():
    return RedirectResponse(url="/admin")

@app.post("/api/farms/register")
async def register_farm(
    farmer_name: str = Form(...),
    national_id: str = Form(...),
    phone: str = Form(...),
    applicant_role: str = Form("مالك"),
    ownership_doc_type: str = Form("صك ملكية إلكتروني"),
    ownership_doc_number: str = Form(...),
    agri_registry_number: str = Form(...),
    region: str = Form(...),
    governorate: str = Form(...),
    city: str = Form(""),
    center: str = Form(""),
    village: str = Form(""),
    maps_url: str = Form(""),
    latitude: Optional[float] = Form(None),
    longitude: Optional[float] = Form(None),
    land_status: str = Form("غير محياة"),
    area_m2: float = Form(5000.0),
    electricity_source: str = Form("لا يوجد"),
    water_source: str = Form("لا يوجد"),
    previous_crops: str = Form(""),
    priority_needs_text: str = Form(""),
    road_type: str = Form("معبد"),
    social_security: str = Form("لا"),
    priority_needs: Optional[Any] = Form(None),
    media_descriptions: Optional[List[str]] = Form(None),
    media_urls: str = Form(""),
    notes: str = Form("")
):
    # Mandatory validations
    if not agri_registry_number or not agri_registry_number.strip():
        return JSONResponse({
            "success": False,
            "message": "رقم السجل الزراعي المطور شرط إلزامي ولا يمكن إتمام التقديم بدونه."
        }, status_code=400)

    if not ownership_doc_number or not ownership_doc_number.strip():
        return JSONResponse({
            "success": False,
            "message": "رقم وثيقة إثبات الملكية أو الحيازة شرط إلزامي للتقديم."
        }, status_code=400)

    if not previous_crops or not previous_crops.strip():
        return JSONResponse({
            "success": False,
            "message": "حقل المزروعات السابقة أو الحالية إلزامي."
        }, status_code=400)

    if not priority_needs_text or not priority_needs_text.strip():
        return JSONResponse({
            "success": False,
            "message": "حقل أهم احتياجات التأهيل المطلوبة للمزرعة إلزامي."
        }, status_code=400)

    conn = get_db_connection()
    c = conn.cursor()

    # Generate new code
    c.execute("SELECT max(id) FROM farms")
    max_id = c.fetchone()[0] or 0
    new_id = max_id + 1
    code = f"FRM-{new_id:04d}"
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    agri_reg = agri_registry_number.strip()
    doc_type = ownership_doc_type.strip()
    doc_num = ownership_doc_number.strip()
    farm_city = (city or governorate).strip()

    # Coords fallback if missing
    if not latitude or not longitude:
        from backend.init_db import REGION_COORDS
        center_c = REGION_COORDS.get(region, (24.0, 45.0))
        latitude = center_c[0] + random.uniform(-0.1, 0.1)
        longitude = center_c[1] + random.uniform(-0.1, 0.1)

    if not maps_url:
        maps_url = f"https://maps.google.com/?q={latitude:.5f},{longitude:.5f}"

    priority, solution, cost = generate_solution_for_farm(
        region, water_source, electricity_source, land_status, area_m2, previous_crops, social_security
    )

    needs_summary = (priority_needs_text or "").strip()
    if not needs_summary and priority_needs:
        if isinstance(priority_needs, list):
            needs_summary = ", ".join(priority_needs)
        else:
            needs_summary = str(priority_needs)

    combined_notes = f"صفة مقدم الطلب: {applicant_role} | وثيقة الملكية: {doc_type} رقم ({doc_num})"
    if needs_summary:
        combined_notes += f" | احتياجات التأهيل المطلوبة: {needs_summary}"
    if notes:
        combined_notes += f" | ملاحظات: {notes}"

    # Compile media descriptions
    media_summary = media_urls or ""
    if media_descriptions:
        valid_descs = [d.strip() for d in media_descriptions if d and d.strip()]
        if valid_descs:
            media_summary = " | ".join(valid_descs) + (f" | {media_urls}" if media_urls else "")

    c.execute("""
    INSERT INTO farms (
        code, created_at, farmer_name, national_id, phone, region, governorate, city, center, village,
        maps_url, latitude, longitude, land_status, area_m2, electricity_source, water_source,
        previous_crops, media_urls, road_type, social_security, agricultural_registry, status,
        readiness_priority, suggested_solution, solution_cost_est, assigned_partner_name, support_status, notes,
        ownership_doc_type, ownership_doc_number, applicant_role
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        code, created_at, farmer_name, national_id, phone, region, governorate, farm_city, farm_city, farm_city,
        maps_url, latitude, longitude, land_status, area_m2, electricity_source, water_source,
        previous_crops, media_summary, road_type, social_security, agri_reg, "مسجل",
        priority, solution, cost, "قيد الترشيح", "متاح", combined_notes,
        doc_type, doc_num, applicant_role
    ))
    conn.commit()
    conn.close()

    return JSONResponse({
        "success": True,
        "message": f"تم إنشاء طلب رقم ({code}) بنجاح",
        "code": code,
        "farmer_name": farmer_name,
        "agri_registry": agri_reg,
        "ownership_doc": f"{doc_type} ({doc_num})",
        "redirect_url": f"/my-requests?code={code}"
    })

NAAMA_SAMPLE_REQUESTS = [
    {
        "id": "naama-1",
        "title": "إصدار شهادة اعتماد مصدر مائي (عقد توريد) لمصانع إنتاج مياه معبأة",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "48051599266",
        "req_date": "2026/11/10",
        "action_type": "استكمال",
        "is_farm": False
    },
    {
        "id": "naama-2",
        "title": "رخص استخدام مصادر المياه الجوفية (الآبار)",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "48021598397",
        "req_date": "2026/08/11",
        "action_type": "استكمال",
        "is_farm": False
    },
    {
        "id": "naama-3",
        "title": "طلب استيراد أسمدة ومخصبات زراعية",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "48021598330",
        "req_date": "2026/08/05",
        "action_type": "استكمال",
        "is_farm": False
    },
    {
        "id": "naama-4",
        "title": "طلب استيراد أسمدة ومخصبات زراعية",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "48021598332",
        "req_date": "2026/08/05",
        "action_type": "استكمال",
        "is_farm": False
    },
    {
        "id": "naama-5",
        "title": "إصدار شهادة اعتماد مصدر مائي (عقد توريد) لمصانع إنتاج مياه معبأة",
        "status": "الطلب ملغي",
        "status_color": "gray",
        "account_num": "7001477913",
        "req_num": "48021598297",
        "req_date": "2026/08/03",
        "action_type": "التفاصيل",
        "is_farm": False
    },
    {
        "id": "naama-6",
        "title": "إصدار شهادة اعتماد مصدر مائي (عقد توريد) لمصانع إنتاج مياه معبأة",
        "status": "الطلب مكتمل",
        "status_color": "green",
        "account_num": "7001477913",
        "req_num": "48021598298",
        "req_date": "2026/08/03",
        "action_type": "التفاصيل",
        "is_farm": False
    },
    {
        "id": "naama-7",
        "title": "إصدار تصريح أعمال الجبس",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "48011585909",
        "req_date": "2026/06/17",
        "action_type": "استكمال",
        "is_farm": False
    },
    {
        "id": "naama-8",
        "title": "استيراد/بذور تجارب",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "20260187215834",
        "req_date": "2026/04/21",
        "action_type": "استكمال",
        "is_farm": False
    },
    {
        "id": "naama-9",
        "title": "تحديث بيانات الشركة/تحديث بيانات الشركة",
        "status": "مسودة",
        "status_color": "purple",
        "account_num": "7001477913",
        "req_num": "20264182215829",
        "req_date": "2026/04/20",
        "action_type": "استكمال",
        "is_farm": False
    }
]

@app.get("/my-requests", response_class=HTMLResponse)
@app.get("/requests", response_class=HTMLResponse)
async def my_requests_page(request: Request, code: Optional[str] = None):
    user_nid = request.session.get("user_nid", "1087452190")
    user_name = request.session.get("user_name", "عبدالله بن فهد الغامدي")
    is_auth = request.session.get("logged_in", False)

    conn = get_db_connection()
    c = conn.cursor()
    
    # Fetch requests exclusively submitted by this citizen or specified by code
    if code:
        if user_nid:
            c.execute("SELECT * FROM farms WHERE code = ? OR national_id = ? ORDER BY id DESC", (code, user_nid))
        else:
            c.execute("SELECT * FROM farms WHERE code = ? ORDER BY id DESC", (code,))
    elif user_nid:
        c.execute("SELECT * FROM farms WHERE national_id = ? ORDER BY id DESC", (user_nid,))
    else:
        c.execute("SELECT * FROM farms WHERE national_id = '1087452190' ORDER BY id DESC")
    
    requests_list = [dict(r) for r in c.fetchall()]
    conn.close()

    logged_user = {
        "nid": user_nid,
        "name": user_name,
        "is_authenticated": is_auth
    }

    # Transform farm requests into the standard Naama table format
    farm_table_items = []
    for f in requests_list:
        raw_date = f.get("created_at") or "2026-11-17"
        req_date = raw_date[:10].replace("-", "/")
        st = f.get("status", "مسجل")
        if st in ["مسجل", "غير محياة"]:
            status_text = "تحت المراجعة والتدقيق"
            status_color = "emerald"
        elif st in ["مؤهلة ومنتجة", "معتمد"]:
            status_text = "الطلب مكتمل"
            status_color = "green"
        elif st in ["مسودة"]:
            status_text = "مسودة"
            status_color = "purple"
        elif st in ["ملغي", "الطلب ملغي"]:
            status_text = "الطلب ملغي"
            status_color = "gray"
        else:
            status_text = st
            status_color = "emerald"

        farm_table_items.append({
            "id": f.get("code"),
            "title": "طلب حصر وتأهيل مزرعة مهملة",
            "status": status_text,
            "status_color": status_color,
            "account_num": "7001477913",
            "req_num": f.get("code"),
            "req_date": req_date,
            "action_type": "التفاصيل",
            "is_farm": True,
            "farm": f
        })

    # Only show the beneficiary's actual submitted requests (no mock sample requests)
    all_table_requests = farm_table_items

    return render_template(request, "my_requests.html", {
        "requests_list": requests_list,
        "all_table_requests": all_table_requests,
        "active_code": code,
        "logged_user": logged_user
    })

@app.get("/track", response_class=HTMLResponse)
async def track_page(request: Request, query: Optional[str] = None):
    farm = None
    visits = []
    error = None

    if query:
        q = query.strip()
        conn = get_db_connection()
        c = conn.cursor()
        c.execute("SELECT * FROM farms WHERE code = ? OR national_id = ? OR phone = ? LIMIT 1", (q, q, q))
        row = c.fetchone()
        if row:
            farm = dict(row)
            c.execute("SELECT * FROM field_visits WHERE farm_id = ? ORDER BY id DESC", (farm['id'],))
            visits = [dict(v) for v in c.fetchall()]
        else:
            error = f"لم يتم العثور على أي مزرعة مسجلة بالرقم: {q}"
        conn.close()

    return render_template(request, "track.html", {
        "farm": farm,
        "visits": visits,
        "query": query,
        "error": error
    })

@app.get("/advisory", response_class=HTMLResponse)
async def advisory_page(request: Request):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM advisory_requests ORDER BY id DESC LIMIT 20")
    advisories = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template(request, "advisory.html", {"advisories": advisories})

@app.post("/api/advisory")
async def create_advisory(
    farmer_name: str = Form(...),
    farmer_phone: str = Form(...),
    topic: str = Form(...),
    inquiry: str = Form(...)
):
    conn = get_db_connection()
    c = conn.cursor()
    created_at = datetime.now().strftime("%Y-%m-%d")
    c.execute("""
    INSERT INTO advisory_requests (farm_id, farmer_name, farmer_phone, topic, inquiry, reply, advisor_name, status, created_at)
    VALUES (?,?,?,?,?,?,?,?,?)
    """, (None, farmer_name, farmer_phone, topic, inquiry, "طلبك قيد الدراسة من قبل المرشد الزراعي المختص بفرع الوزارة.", "الإدارة العامة للإرشاد الزراعي", "قيد الانتظار", created_at))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "message": "تم إرسال استشارتك بنجاح وسيتواصل معك المرشد الزراعي."})

# ==================== ADMIN & COMMITTEE PORTAL ROUTES ====================

@app.get("/admin", response_class=HTMLResponse)
async def admin_dashboard(request: Request):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT count(*) FROM farms")
    total_farms = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE status = 'مؤهلة ومنتجة'")
    rehab_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE status = 'جاري التأهيل'")
    active_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE readiness_priority LIKE '%أولوية 1%'")
    p1_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE readiness_priority LIKE '%أولوية 2%'")
    p2_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE readiness_priority LIKE '%أولوية 3%'")
    p3_count = c.fetchone()[0]

    c.execute("SELECT sum(area_m2) FROM farms")
    total_area_m2 = c.fetchone()[0] or 0
    total_hectares = round(total_area_m2 / 10000.0, 1)

    c.execute("SELECT count(*) FROM farms WHERE water_source LIKE '%بئر%' OR water_source LIKE '%خزان%'")
    has_water_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE electricity_source LIKE '%يوجد%'")
    has_elec_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE social_security LIKE '%نعم%'")
    social_sec_count = c.fetchone()[0]

    # Regions breakdown
    c.execute("SELECT region, count(*) as cnt FROM farms GROUP BY region ORDER BY cnt DESC")
    regions_data = [dict(r) for r in c.fetchall()]

    # Partners summary
    c.execute("SELECT sum(committed_quantity), sum(delivered_quantity) FROM partners")
    partner_stats = c.fetchone()
    committed_seedlings = partner_stats[0] or 408140
    delivered_seedlings = partner_stats[1] or 112000

    # Recent farms
    c.execute("SELECT * FROM farms ORDER BY id DESC LIMIT 8")
    recent_farms = [dict(r) for r in c.fetchall()]

    conn.close()

    return render_template(request, "admin/dashboard.html", {
        "total_farms": total_farms,
        "rehab_count": rehab_count,
        "active_count": active_count,
        "p1_count": p1_count,
        "p2_count": p2_count,
        "p3_count": p3_count,
        "total_hectares": f"{total_hectares:,}",
        "has_water_count": has_water_count,
        "has_elec_count": has_elec_count,
        "social_sec_count": social_sec_count,
        "regions_data": regions_data,
        "committed_seedlings": f"{committed_seedlings:,}",
        "delivered_seedlings": f"{delivered_seedlings:,}",
        "recent_farms": recent_farms
    })

@app.get("/admin/inbox", response_class=HTMLResponse)
async def admin_inbox_page(request: Request, role: Optional[str] = "auditor"):
    conn = get_db_connection()
    c = conn.cursor()

    # 1. Auditor farms (New registrations awaiting office audit)
    c.execute("""
        SELECT * FROM farms 
        WHERE status IN ('مسجل', 'جديد') 
        ORDER BY id DESC LIMIT 50
    """)
    auditor_farms = [dict(r) for r in c.fetchall()]

    # 2. Inspector farms (Approved by auditor, awaiting field inspection)
    c.execute("""
        SELECT * FROM farms 
        WHERE status IN ('قيد المراجعة', 'محال للمعاينة الميدانية', 'بانتظار الزيارة الميدانية') 
        ORDER BY id DESC LIMIT 50
    """)
    inspector_farms = [dict(r) for r in c.fetchall()]

    # 3. Manager farms (Inspected, awaiting final committee approval)
    c.execute("""
        SELECT * FROM farms 
        WHERE status IN ('تمت الزيارة الميدانية', 'بانتظار الاعتماد') 
        ORDER BY id DESC LIMIT 50
    """)
    manager_farms = [dict(r) for r in c.fetchall()]

    # Counts
    c.execute("SELECT count(*) FROM farms WHERE status IN ('مسجل', 'جديد')")
    auditor_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE status IN ('قيد المراجعة', 'محال للمعاينة الميدانية', 'بانتظار الزيارة الميدانية')")
    inspector_count = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE status IN ('تمت الزيارة الميدانية', 'بانتظار الاعتماد')")
    manager_count = c.fetchone()[0]

    c.execute("SELECT id, name, category, region, contribution_type, unit FROM partners ORDER BY id")
    partners = [dict(r) for r in c.fetchall()]

    conn.close()

    return render_template(request, "admin/inbox.html", {
        "active_role": role or "auditor",
        "auditor_farms": auditor_farms,
        "inspector_farms": inspector_farms,
        "manager_farms": manager_farms,
        "auditor_count": auditor_count,
        "inspector_count": inspector_count,
        "manager_count": manager_count,
        "partners": partners
    })

@app.get("/api/admin/farms/{farm_id}/review")
async def get_farm_review_data(farm_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        return JSONResponse({"success": False, "message": "الطلب غير موجود"}, status_code=404)
    farm = dict(row)
    c.execute("SELECT * FROM field_visits WHERE farm_id = ? ORDER BY id ASC", (farm_id,))
    visits = [dict(v) for v in c.fetchall()]
    conn.close()

    # Extract needs from notes if present
    notes_str = farm.get("notes") or ""
    needs_text = ""
    if "احتياجات التأهيل المطلوبة:" in notes_str:
        part = notes_str.split("احتياجات التأهيل المطلوبة:")[1]
        needs_text = part.split("\n")[0].split("|")[0].strip()

    farm["priority_needs_display"] = needs_text or "تأهيل منظومة الري وحفر/صيانة البئر وتوريد الشتلات"

    return JSONResponse({
        "success": True,
        "farm": farm,
        "visits": visits
    })

@app.post("/api/admin/inbox/action")
async def admin_inbox_action(
    farm_id: int = Form(...),
    action: str = Form(...),
    role: str = Form("auditor"),
    notes: Optional[str] = Form(""),
    visit_date: Optional[str] = Form(None),
    inspector_name: Optional[str] = Form("م. فيصل الغامدي"),
    support_path: Optional[str] = Form("مسار القرض الحسن (بنك التنمية / أزكى)"),
    water_eval: Optional[str] = Form(None),
    irrigation_eval: Optional[str] = Form(None),
    soil_eval: Optional[str] = Form(None),
    recommended_seedlings: Optional[str] = Form(None),
    partner_id: Optional[int] = Form(None),
    allocated_quantity: Optional[int] = Form(0)
):
    conn = get_db_connection()
    c = conn.cursor()

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    c.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
    farm_row = c.fetchone()
    if not farm_row:
        conn.close()
        return JSONResponse({"success": False, "message": "المزرعة غير موجودة"}, status_code=404)

    farm = dict(farm_row)
    cur_notes = farm.get("notes") or ""

    if role == "auditor":
        if action == "approve_audit":
            new_status = "محال للمعاينة الميدانية"
            audit_log = f"\n[التدقيق المكتبي - {now_str}]: تم قبول الطلب مبدئياً واستيفاء الوثائق وإحالته للمعاينة الميدانية."
            if notes:
                audit_log += f" ملاحظات: {notes}"
            c.execute("UPDATE farms SET status = ?, notes = ? WHERE id = ?", (new_status, cur_notes + audit_log, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تم اعتماد التدقيق المكتبي للطلب {farm['code']} وإحالته بنجاح إلى فني الزيارة الميدانية.",
                "farm_id": farm_id,
                "new_status": new_status,
                "next_role": "inspector"
            })
        elif action == "request_info":
            new_status = "نواقص وثائق"
            audit_log = f"\n[التدقيق المكتبي - {now_str}]: تم طلب استكمال نواقص من المستفيد: {notes or 'يرجى تدقيق وثيقة الملكية والسجل الزراعي'}."
            c.execute("UPDATE farms SET status = ?, notes = ? WHERE id = ?", (new_status, cur_notes + audit_log, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تم إشعار المستفيد بالنواقص المطلوبة للطلب {farm['code']}.",
                "farm_id": farm_id,
                "new_status": new_status
            })
        elif action == "reject":
            new_status = "مرفوض من الفرع"
            audit_log = f"\n[التدقيق المكتبي - {now_str}]: تم رفض الطلب نظامياً لعدم انطباق الشروط: {notes or 'غير مستوفٍ للضوابط'}."
            c.execute("UPDATE farms SET status = ?, notes = ? WHERE id = ?", (new_status, cur_notes + audit_log, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تم رفض الطلب {farm['code']} وحفظ السبب في سجل المزرعة.",
                "farm_id": farm_id,
                "new_status": new_status
            })

    elif role == "inspector":
        if action == "schedule_visit":
            v_date = visit_date or datetime.now().strftime("%Y-%m-%d")
            c.execute("""
                INSERT INTO field_visits (farm_id, team_name, inspector_name, visit_date, status, soil_quality, water_salinity_tds, recommendations)
                VALUES (?, ?, ?, ?, 'مجدولة', ?, 0, ?)
            """, (farm_id, "فريق المعاينة الفنية", inspector_name, v_date, "بانتظار المعاينة", notes or "معاينة وفحص التربة ومصادر المياه"))
            log_entry = f"\n[فني الميدان - {now_str}]: تم جدولة المعاينة الميدانية بتاريخ {v_date} بواسطة {inspector_name}."
            c.execute("UPDATE farms SET notes = ? WHERE id = ?", (cur_notes + log_entry, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تمت جدولة موعد الزيارة الميدانية للمزرعة {farm['code']} بنجاح بتاريخ {v_date}.",
                "farm_id": farm_id,
                "visit_date": v_date
            })
        elif action == "submit_inspection_report":
            new_status = "تمت الزيارة الميدانية"
            v_date = visit_date or datetime.now().strftime("%Y-%m-%d")
            findings_text = f"فحص مصادر المياه: {water_eval or 'بئر يحتاج مضخة موفرة'} | شبكة الري: {irrigation_eval or 'تحتاج شبكة تنقيط حديثة'}"
            recs_text = f"الشتلات الموصى بها: {recommended_seedlings or 'بن ولوز وفواكه'} | ملاحظات: {notes or 'المزرعة مؤهلة لتدخل استصلاحي سريع'}"

            c.execute("""
                INSERT INTO field_visits (farm_id, team_name, inspector_name, visit_date, status, soil_quality, water_salinity_tds, recommendations)
                VALUES (?, ?, ?, ?, 'منجزة', ?, 450, ?)
            """, (farm_id, "فريق المعاينة الفنية", inspector_name, v_date, soil_eval or "تربة صالحة ومؤهلة", f"{findings_text} | {recs_text}"))

            log_entry = f"\n[فني الميدان - {now_str}]: تم إنجاز المعاينة الميدانية بواسطة {inspector_name}. التقرير: {findings_text}. التوصية: {recs_text}. ورُفع الطلب للاعتماد."
            c.execute("UPDATE farms SET status = ?, notes = ? WHERE id = ?", (new_status, cur_notes + log_entry, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تم رفع التقرير الميداني للمزرعة {farm['code']} بنجاح وإحالة الطلب إلى مدير الفرع للاعتماد.",
                "farm_id": farm_id,
                "new_status": new_status,
                "next_role": "manager"
            })

    elif role == "manager":
        if action == "approve_plan":
            new_status = "جاري التأهيل"
            partner_name = support_path or "مسار القرض الحسن (بنك التنمية / شركة أزكى)"
            support_type_label = support_path or "دعم تأهيل زراعي"
            qty_val = allocated_quantity if allocated_quantity and allocated_quantity > 0 else 1

            if partner_id:
                c.execute("SELECT id, name, contribution_type FROM partners WHERE id = ?", (partner_id,))
                p_row = c.fetchone()
                if p_row:
                    partner_name = p_row["name"]
                    support_type_label = p_row["contribution_type"]
                    c.execute("""
                        INSERT INTO support_allocations (farm_id, partner_id, support_type, quantity, status, allocated_date, notes)
                        VALUES (?, ?, ?, ?, 'مخصص ومعتمد', ?, ?)
                    """, (farm_id, partner_id, support_type_label, qty_val, now_str[:10], f"{support_path or ''} | {notes or ''}".strip(" |")))

            approval_log = f"\n[مدير الفرع - {now_str}]: تم الاعتماد النهائي لخطة التأهيل وتخصيص مسار الدعم ({support_path}) وإسنادها للشريك: {partner_name}."
            if notes:
                approval_log += f" توجيهات الإدارة: {notes}"

            c.execute("""
                UPDATE farms 
                SET status = ?, support_status = 'مخصص', assigned_partner_name = ?, notes = ? 
                WHERE id = ?
            """, (new_status, partner_name, cur_notes + approval_log, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تم إصدار قرار الاعتماد النهائي للمزرعة {farm['code']} وإسناد الدعم للشريك ({partner_name}) بنجاح!",
                "farm_id": farm_id,
                "new_status": new_status
            })
        elif action == "return_for_reinspection":
            new_status = "محال للمعاينة الميدانية"
            log_entry = f"\n[مدير الفرع - {now_str}]: تم إعادة الملف لفني الميدان لإعادة الفحص والتدقيق: {notes or 'يرجى إعادة فحص منسوب المياه'}."
            c.execute("UPDATE farms SET status = ?, notes = ? WHERE id = ?", (new_status, cur_notes + log_entry, farm_id))
            conn.commit()
            conn.close()
            return JSONResponse({
                "success": True,
                "message": f"تمت إعادة الطلب {farm['code']} إلى فني الميدان لإعادة المعاينة.",
                "farm_id": farm_id,
                "new_status": new_status,
                "next_role": "inspector"
            })

    conn.close()
    return JSONResponse({"success": False, "message": "إجراء غير معروف"}, status_code=400)

@app.get("/admin/farms", response_class=HTMLResponse)
async def admin_farms_list(
    request: Request,
    page: int = 1,
    limit: int = 25,
    region: Optional[str] = None,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    water: Optional[str] = None,
    elec: Optional[str] = None,
    social: Optional[str] = None,
    search: Optional[str] = None
):
    conn = get_db_connection()
    c = conn.cursor()

    query = "SELECT * FROM farms WHERE 1=1"
    params = []

    if region and region != "الكل":
        query += " AND region = ?"
        params.append(region)
    if status and status != "الكل":
        query += " AND status = ?"
        params.append(status)
    if priority and priority != "الكل":
        query += " AND readiness_priority LIKE ?"
        params.append(f"%{priority}%")
    if water and water != "الكل":
        if water == "يوجد":
            query += " AND (water_source LIKE '%بئر%' OR water_source LIKE '%خزان%')"
        else:
            query += " AND (water_source LIKE '%لا%' OR water_source LIKE '%أمطار%')"
    if elec and elec != "الكل":
        query += " AND electricity_source LIKE ?"
        params.append(f"%{elec}%")
    if social and social != "الكل":
        query += " AND social_security LIKE ?"
        params.append(f"%{social}%")
    if search and search.strip():
        s = f"%{search.strip()}%"
        query += " AND (code LIKE ? OR farmer_name LIKE ? OR national_id LIKE ? OR phone LIKE ? OR governorate LIKE ?)"
        params.extend([s, s, s, s, s])

    # Count total matching
    count_query = query.replace("SELECT *", "SELECT count(*)")
    c.execute(count_query, params)
    total_matching = c.fetchone()[0]

    # Paginate
    offset = (page - 1) * limit
    query += " ORDER BY id DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    c.execute(query, params)
    farms = [dict(r) for r in c.fetchall()]

    # Get distinct regions for filter dropdown
    c.execute("SELECT DISTINCT region FROM farms ORDER BY region")
    all_regions = [r[0] for r in c.fetchall()]

    total_pages = (total_matching + limit - 1) // limit

    conn.close()

    return render_template(request, "admin/farms.html", {
        "farms": farms,
        "page": page,
        "limit": limit,
        "total_matching": total_matching,
        "total_pages": total_pages,
        "all_regions": all_regions,
        "selected_region": region or "الكل",
        "selected_status": status or "الكل",
        "selected_priority": priority or "الكل",
        "selected_water": water or "الكل",
        "selected_elec": elec or "الكل",
        "selected_social": social or "الكل",
        "search": search or ""
    })

@app.get("/admin/farms/{farm_id}", response_class=HTMLResponse)
async def admin_farm_detail(request: Request, farm_id: int):
    conn = get_db_connection()
    c = conn.cursor()

    c.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="المزرعة غير موجودة")
    farm = dict(row)

    # Visits
    c.execute("SELECT * FROM field_visits WHERE farm_id = ? ORDER BY id DESC", (farm_id,))
    visits = [dict(v) for v in c.fetchall()]

    # Partners list for assignment
    c.execute("SELECT * FROM partners ORDER BY name")
    partners = [dict(p) for p in c.fetchall()]

    conn.close()
    return render_template(request, "admin/farm_detail.html", {
        "farm": farm,
        "visits": visits,
        "partners": partners
    })

@app.post("/api/admin/farms/{farm_id}/update")
async def update_farm_status(
    farm_id: int,
    status: str = Form(...),
    readiness_priority: str = Form(...),
    assigned_partner_name: str = Form(...),
    support_status: str = Form(...),
    notes: str = Form("")
):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE farms SET
        status = ?,
        readiness_priority = ?,
        assigned_partner_name = ?,
        support_status = ?,
        notes = ?
    WHERE id = ?
    """, (status, readiness_priority, assigned_partner_name, support_status, notes, farm_id))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "message": "تم تحديث بيانات المزرعة بنجاح"})

@app.post("/api/admin/farms/{farm_id}/regenerate-solution")
async def regenerate_solution(farm_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404)
    farm = dict(row)

    priority, solution, cost = generate_solution_for_farm(
        farm['region'], farm['water_source'], farm['electricity_source'],
        farm['land_status'], farm['area_m2'], farm['previous_crops'], farm['social_security']
    )

    c.execute("""
    UPDATE farms SET
        readiness_priority = ?,
        suggested_solution = ?,
        solution_cost_est = ?
    WHERE id = ?
    """, (priority, solution, cost, farm_id))
    conn.commit()
    conn.close()

    return JSONResponse({
        "success": True,
        "priority": priority,
        "suggested_solution": solution,
        "cost": cost
    })

@app.get("/admin/map", response_class=HTMLResponse)
async def admin_map_view(request: Request):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT DISTINCT region FROM farms ORDER BY region")
    all_regions = [r[0] for r in c.fetchall()]
    conn.close()
    return render_template(request, "admin/map.html", {"all_regions": all_regions})

@app.get("/api/farms/geojson")
async def get_farms_geojson(region: Optional[str] = None, priority: Optional[str] = None):
    conn = get_db_connection()
    c = conn.cursor()

    query = "SELECT id, code, farmer_name, region, governorate, area_m2, status, readiness_priority, suggested_solution, solution_cost_est, latitude, longitude, water_source, electricity_source FROM farms WHERE 1=1"
    params = []
    if region and region != "الكل":
        query += " AND region = ?"
        params.append(region)
    if priority and priority != "الكل":
        query += " AND readiness_priority LIKE ?"
        params.append(f"%{priority}%")

    query += " LIMIT 1750"
    c.execute(query, params)
    rows = c.fetchall()
    conn.close()

    features = []
    for r in rows:
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [r["longitude"], r["latitude"]]
            },
            "properties": {
                "id": r["id"],
                "code": r["code"],
                "name": r["farmer_name"],
                "region": r["region"],
                "gov": r["governorate"],
                "area": r["area_m2"],
                "status": r["status"],
                "priority": r["readiness_priority"],
                "solution": r["suggested_solution"],
                "cost": r["solution_cost_est"],
                "water": r["water_source"],
                "elec": r["electricity_source"]
            }
        })

    return JSONResponse({
        "type": "FeatureCollection",
        "features": features
    })

@app.get("/admin/partners", response_class=HTMLResponse)
async def admin_partners_view(request: Request):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM partners ORDER BY id")
    partners = [dict(r) for r in c.fetchall()]

    # Allocations
    c.execute("""
    SELECT sa.*, f.code as farm_code, f.farmer_name, f.region as farm_region, p.name as partner_name
    FROM support_allocations sa
    JOIN farms f ON sa.farm_id = f.id
    JOIN partners p ON sa.partner_id = p.id
    ORDER BY sa.id DESC LIMIT 50
    """)
    allocations = [dict(r) for r in c.fetchall()]
    conn.close()

    return render_template(request, "admin/partners.html", {
        "partners": partners,
        "allocations": allocations
    })

@app.post("/api/admin/partners")
async def add_partner(
    name: str = Form(...),
    category: str = Form(...),
    region: str = Form(...),
    contribution_type: str = Form(...),
    committed_quantity: int = Form(...),
    unit: str = Form(...),
    phone: str = Form(""),
    email: str = Form("")
):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO partners (name, category, region, contribution_type, committed_quantity, delivered_quantity, unit, phone, email, status)
    VALUES (?,?,?,?,?,0,?,?,?,'نشط')
    """, (name, category, region, contribution_type, committed_quantity, unit, phone, email))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "message": "تمت إضافة الشريك ومساهمته بنجاح"})

@app.get("/admin/visits", response_class=HTMLResponse)
async def admin_visits_view(request: Request):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    SELECT v.*, f.code as farm_code, f.farmer_name, f.region, f.governorate, f.phone
    FROM field_visits v
    JOIN farms f ON v.farm_id = f.id
    ORDER BY v.id DESC LIMIT 100
    """)
    visits = [dict(r) for r in c.fetchall()]

    # Farms ready for visit
    c.execute("SELECT id, code, farmer_name, region, governorate FROM farms WHERE status = 'قيد المراجعة' LIMIT 50")
    pending_farms = [dict(r) for r in c.fetchall()]
    conn.close()

    return render_template(request, "admin/visits.html", {
        "visits": visits,
        "pending_farms": pending_farms
    })

@app.post("/api/admin/visits")
async def schedule_visit(
    farm_id: int = Form(...),
    team_name: str = Form(...),
    visit_date: str = Form(...),
    inspector_name: str = Form(...)
):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO field_visits (farm_id, team_name, visit_date, status, soil_quality, water_salinity_tds, recommendations, inspector_name)
    VALUES (?,?,?, 'مجدولة', 'قيد الفحص المخبري', 0, 'معاينة ميدانية مجدولة لتقييم مصادر المياه والتربة', ?)
    """, (farm_id, team_name, visit_date, inspector_name))

    # Update farm status
    c.execute("UPDATE farms SET status = 'تمت الزيارة الميدانية' WHERE id = ?", (farm_id,))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "message": "تمت جدولة الزيارة الميدانية بنجاح وتحديث حالة المزرعة"})

@app.get("/admin/advisory", response_class=HTMLResponse)
async def admin_advisory_view(request: Request):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM advisory_requests ORDER BY id DESC")
    advisories = [dict(r) for r in c.fetchall()]
    conn.close()
    return render_template(request, "admin/advisory.html", {"advisories": advisories})

@app.post("/api/admin/advisory/{req_id}/reply")
async def reply_advisory(req_id: int, reply: str = Form(...), advisor_name: str = Form("مرشد زراعي معتمد")):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("UPDATE advisory_requests SET reply = ?, advisor_name = ?, status = 'تم الرد' WHERE id = ?", (reply, advisor_name, req_id))
    conn.commit()
    conn.close()
    return JSONResponse({"success": True, "message": "تم اعتماد التوصية الإرشادية وإرسالها للمزارع بنجاح"})

@app.get("/admin/reports", response_class=HTMLResponse)
async def admin_reports_view(request: Request):
    conn = get_db_connection()
    c = conn.cursor()

    # Executive figures
    c.execute("SELECT count(*) FROM farms")
    total_farms = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE status = 'مؤهلة ومنتجة'")
    rehab = c.fetchone()[0]

    c.execute("SELECT count(*) FROM farms WHERE status = 'جاري التأهيل'")
    in_progress = c.fetchone()[0]

    c.execute("SELECT sum(area_m2) FROM farms")
    hectares = round((c.fetchone()[0] or 0) / 10000.0, 2)

    c.execute("SELECT region, count(*) as cnt FROM farms GROUP BY region ORDER BY cnt DESC")
    region_stats = [dict(r) for r in c.fetchall()]

    c.execute("SELECT * FROM partners ORDER BY id")
    partners = [dict(r) for r in c.fetchall()]

    conn.close()
    return render_template(request, "admin/reports.html", {
        "total_farms": total_farms,
        "rehab": rehab,
        "in_progress": in_progress,
        "hectares": hectares,
        "region_stats": region_stats,
        "partners": partners,
        "report_date": "نوفمبر 2026م"
    })

@app.get("/admin/farms/{farm_id}/print", response_class=HTMLResponse)
async def print_farm_card(request: Request, farm_id: int):
    conn = get_db_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM farms WHERE id = ?", (farm_id,))
    row = c.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404)
    farm = dict(row)
    c.execute("SELECT * FROM field_visits WHERE farm_id = ? ORDER BY id DESC", (farm_id,))
    visits = [dict(v) for v in c.fetchall()]
    conn.close()

    return render_template(request, "admin/print_card.html", {
        "farm": farm,
        "visits": visits
    })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=True)
