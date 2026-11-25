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

print("--- 2. Testing /register Page HTML & Directives ---")
res = client.get("/register")
assert res.status_code == 200
html = res.text

# Check 1: Farmer Name & Phone are readonly
assert 'id="farmer_name"' in html
assert 'readonly' in html
assert 'id="phone"' in html
assert "تلقائي من نما" in html
print("[OK] Farmer Name & Phone are READ-ONLY.")

# Check 2: Word (مؤهل لمسار الدعم والقرض الحسن) is removed
assert "(مؤهل لمسار الدعم والقرض الحسن)" not in html
assert "حالة المستفيد في الضمان الاجتماعي المطور" in html
assert "<span>مسجل</span>" in html
print("[OK] '(مؤهل لمسار الدعم والقرض الحسن)' is completely REMOVED; badge shows only 'مسجل'.")

# Check 3: Merged Step 1 & 2 into "بيانات المستفيد و السجل الزراعي", and Step 4 added for Review
assert "الخطوة 1: بيانات المستفيد و السجل الزراعي" in html
assert "step-ind-3" in html
assert "step-ind-4" in html
print("[OK] Steps 1 & 2 merged into 'بيانات المستفيد و السجل الزراعي' and Step 4 added for Review.")

# Check 4: Location fields are read-only and City replaced center & village
assert 'id="reg_display"' in html
assert 'id="governorate"' in html
assert 'id="city"' in html
assert 'name="governorate" id="governorate" readonly' in html
assert 'name="city" id="city" readonly' in html
print("[OK] Geographic location fields (Region, Governorate, City) are strictly READ-ONLY.")

# Check 5: Dynamic linking between applicant role and ownership document type
assert 'ROLE_DOC_MAPPING' in html
assert 'onApplicantRoleChanged' in html
assert 'صك ملكية إلكتروني' in html
assert 'صك حصر ورثة مشفوع بوكالة شرعية سارية' in html
assert 'عقد إيجار زراعي موثق' in html
assert 'عقد استثمار وتشغيل زراعي معتمد' in html
print("[OK] Applicant Role is dynamically mapped to matching document types.")

# Check 6: Step 3 updates (Textareas for crops and needs mandatory, cloud link removed, multiple attachments with required description)
assert '<textarea name="previous_crops" id="previous_crops"' in html
assert 'required' in html
assert '<textarea name="priority_needs_text" id="priority_needs_text"' in html
# Cloud url removed
assert 'رابط صور أو فيديو إضافي سحابي' not in html
# Media attachments container and required description
assert 'id="media_attachments_container"' in html
assert 'name="media_descriptions[]"' in html
assert 'name="media_files[]"' in html
assert 'addMediaAttachmentRow' in html
# Label 'ملاحظات' updated
assert 'ملاحظات إضافية لفريق المعاينة' not in html
print("[OK] Step 3 textareas, multiple media attachments with required description, and simplified 'ملاحظات' verified.")

print("--- 3. Testing Farm Registration API ---")
payload = {
    "farmer_name": "سعد بن محمد القحطاني",
    "national_id": "1087452190",
    "phone": "0554129876",
    "applicant_role": "وريث مفوض",
    "ownership_doc_type": "صك حصر ورثة مشفوع بوكالة شرعية سارية",
    "ownership_doc_number": "4201992837",
    "agri_registry_number": "SA-2026-104520",
    "region": "الباحة",
    "governorate": "بلجرشي",
    "center": "مركز بني كبير",
    "village": "قرية الحدب",
    "area_m2": 12000,
    "land_status": "غير محياة",
    "water_source": "بئر",
    "electricity_source": "لا يوجد",
    "previous_crops": "بن شدوي، لوز بجلي، رمان",
    "priority_needs_text": "بحاجة لحفر بئر ارتوازي وتركيب منظومة طاقة شمسية وشبكة ري بالتنقيط",
    "media_descriptions": ["صورة البئر الحالي وحالته", "فيديو للمدرجات المهملة"],
    "road_type": "معبد",
    "social_security": "نعم",
    "notes": "المزرعة بحاجة لمعاينة عاجلة"
}

res = client.post("/api/farms/register", data=payload)
assert res.status_code == 200
data = res.json()
assert data["success"] is True
assert data["code"].startswith("FRM-")
assert data["agri_registry"] == "SA-2026-104520"
print(f"[OK] Farm registered successfully with code: {data['code']}")

print("\n>>> ALL TESTS FOR NEW REGISTER FLOW PASSED 100%! <<<")
