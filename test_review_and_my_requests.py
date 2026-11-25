import sys
import io

sys.stdout.reconfigure(encoding='utf-8')

from starlette.testclient import TestClient
from backend.app import app

client = TestClient(app)

print("--- 1. Testing Nafath Simulation & Login ---")
res = client.post("/api/nafath/initiate", data={"national_id": "1087452190"})
assert res.status_code == 200

res = client.post("/api/nafath/confirm", data={"national_id": "1087452190", "farmer_name": "سعد بن محمد القحطاني"})
assert res.status_code == 200

print("--- 2. Testing /register Review Step & Success Modal Directives ---")
res = client.get("/register")
assert res.status_code == 200
html = res.text

# Check 1: Review step exists with pledge confirmation
assert 'id="step-4"' in html
assert 'الخطوة 4: مراجعة بيانات الطلب والتعهد قبل الإرسال' in html
assert 'id="pledge_confirm"' in html
assert 'populateReviewSummary' in html
print("[OK] Review Step (Step 4) and Pledge confirmation checkbox verified.")

# Check 2: Success modal does NOT contain internal evaluation details
assert 'تصنيف الجاهزية التقديري' not in html
assert 'خطة الحلول الاستصلاحية المقترحة آلياً' not in html
assert 'res_my_requests_btn' in html
assert '/my-requests' in html
print("[OK] Internal evaluation details removed from Beneficiary Success Modal.")

print("--- 3. Testing Registration API and Redirect URL ---")
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
    "center": "مركز بني كبير",
    "village": "قرية الحدب",
    "area_m2": 12000,
    "land_status": "غير محياة",
    "water_source": "بئر",
    "electricity_source": "لا يوجد",
    "previous_crops": "بن شدوي ولوز",
    "priority_needs_text": "حفر بئر وطاقة شمسية",
    "media_descriptions": ["صورة البئر القديم"],
    "road_type": "معبد",
    "social_security": "نعم"
}

res = client.post("/api/farms/register", data=payload)
assert res.status_code == 200
data = res.json()
assert data["success"] is True
assert data["code"].startswith("FRM-")
assert "my-requests" in data["redirect_url"]
print(f"[OK] Farm registered with code: {data['code']} and redirect_url: {data['redirect_url']}")

print("--- 4. Testing /my-requests Page ---")
res = client.get(f"/my-requests?code={data['code']}")
assert res.status_code == 200
my_req_html = res.text
assert "قائمة طلباتي" in my_req_html
assert data["code"] in my_req_html
assert "طلب حصر وتأهيل مزرعة مهملة" in my_req_html
assert "تحت المراجعة والتدقيق" in my_req_html
print("[OK] My Requests page (/my-requests) loaded and displays submitted farm request.")

print("\n>>> ALL TESTS FOR REVIEW PAGE AND MY REQUESTS PASSED 100%! <<<")
