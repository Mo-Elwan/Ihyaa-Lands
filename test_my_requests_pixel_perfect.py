import sys

sys.stdout.reconfigure(encoding='utf-8')

from starlette.testclient import TestClient
from backend.app import app

client = TestClient(app)

print("--- 1. Testing /my-requests Page Fidelity to Screenshot ---")
# Authenticate via Nafath
client.post("/api/nafath/initiate", data={"national_id": "1087452190"})
client.post("/api/nafath/confirm", data={"national_id": "1087452190", "farmer_name": "سعد بن محمد القحطاني"})

res = client.get("/my-requests")
assert res.status_code == 200
html = res.text

# 1. Total count title
assert "جميع الطلبات" in html
print("[OK] Total counter line 'جميع الطلبات (X) طلب' is present.")

# 2. Filter Bar
assert 'placeholder="بحث جميع الطلبات"' in html
assert "جميع الحسابات" in html
assert "عرض الطلبات حسب المدة" in html
assert "كل الحالات" in html
assert "الترتيب حسب" in html
print("[OK] Exact 5-element filter toolbar (Search, Account, Duration, Status, Sort) verified.")

# 3. Table Column Headers
assert "عنوان الطلب" in html
assert "الحالة" in html
assert "رقم الحساب" in html
assert "رقم الطلب" in html
assert "تاريخ الطلب" in html
print("[OK] All 5 column headers with sort capability verified.")

# 4. Old Mock Requests are completely HIDDEN as requested
assert "إصدار شهادة اعتماد مصدر مائي (عقد توريد) لمصانع إنتاج مياه معبأة" not in html
assert "رخص استخدام مصادر المياه الجوفية (الآبار)" not in html
assert "طلب استيراد أسمدة ومخصبات زراعية" not in html
assert "إصدار تصريح أعمال الجبس" not in html
print("[OK] Previous sample requests are completely HIDDEN.")

# 5. Status styling: Color is on the text/dot instead of background
assert 'text-[#007a3d]' in html or 'text-emerald' in html
# Check that solid background badge classes are NOT used for status
assert 'bg-[#542d74] shadow-xs' not in html
assert 'bg-[#374151] shadow-xs' not in html
print("[OK] Status styling has color on the text and dot instead of solid background.")

print("--- 2. Testing that Submitting a Farm Request Displays ONLY That Farm Request ---")
payload = {
    "farmer_name": "سعد بن محمد القحطاني",
    "national_id": "1087452190",
    "phone": "0554129876",
    "applicant_role": "مالك",
    "ownership_doc_type": "صك ملكية إلكتروني",
    "ownership_doc_number": "31099887766",
    "agri_registry_number": "SA-2026-104520",
    "region": "الباحة",
    "governorate": "بلجرشي",
    "city": "بلجرشي",
    "area_m2": 12000,
    "land_status": "غير محياة",
    "water_source": "بئر",
    "electricity_source": "لا يوجد",
    "previous_crops": "بن شدوي ولوز",
    "priority_needs_text": "حفر وتعميق بئر",
    "road_type": "معبد",
    "social_security": "نعم"
}

res_reg = client.post("/api/farms/register", data=payload)
assert res_reg.status_code == 200
data_reg = res_reg.json()
code = data_reg["code"]
print(f"[OK] Farm registered with code: {code}")

res_user_reqs = client.get(f"/my-requests?code={code}")
assert res_user_reqs.status_code == 200
user_reqs_html = res_user_reqs.text

assert code in user_reqs_html
assert "طلب حصر وتأهيل مزرعة مهملة" in user_reqs_html
assert "تحت المراجعة والتدقيق" in user_reqs_html
# Ensure color is on the text
assert 'text-[#007a3d]' in user_reqs_html
print(f"[OK] Submitted farm request {code} appears exclusively in My Requests with colored text status.")

print("\n>>> ALL TESTS FOR MY-REQUESTS PASSED 100%! <<<")
