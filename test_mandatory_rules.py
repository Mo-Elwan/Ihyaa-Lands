from starlette.testclient import TestClient
from backend.app import app

client = TestClient(app)

print("--- 1. Testing Failure without Agricultural Registry ---")
bad_data_1 = {
    "farmer_name": "عبدالله الزهراني",
    "national_id": "1023456789",
    "phone": "0501234567",
    "applicant_role": "مالك",
    "ownership_doc_type": "صك ملكية إلكتروني",
    "ownership_doc_number": "310987654321",
    "agri_registry_number": "",  # Empty!
    "region": "الباحة",
    "governorate": "المخواة",
    "area_m2": 10000
}
res = client.post("/api/farms/register", data=bad_data_1)
assert res.status_code in [400, 422]
print("[OK] Correctly rejected missing agricultural registry.")

print("--- 2. Testing Failure without Ownership Document ---")
bad_data_2 = {
    "farmer_name": "عبدالله الزهراني",
    "national_id": "1023456789",
    "phone": "0501234567",
    "applicant_role": "مالك",
    "ownership_doc_type": "صك ملكية إلكتروني",
    "ownership_doc_number": "",  # Empty!
    "agri_registry_number": "SA-2026-998877",
    "region": "الباحة",
    "governorate": "المخواة",
    "area_m2": 10000
}
res = client.post("/api/farms/register", data=bad_data_2)
assert res.status_code in [400, 422]
print("[OK] Correctly rejected missing ownership document.")

print("--- 3. Testing Success with Both Mandatory Conditions Satisfied ---")
good_data = {
    "farmer_name": "عبدالله بن سعيد الزهراني",
    "national_id": "1023456789",
    "phone": "0501234567",
    "applicant_role": "مالك",
    "ownership_doc_type": "صك ملكية إلكتروني",
    "ownership_doc_number": "310987654321",
    "agri_registry_number": "SA-2026-998877",
    "region": "الباحة",
    "governorate": "المخواة",
    "center": "شدا",
    "village": "قرية المروة",
    "land_status": "غير محياة",
    "area_m2": 12000,
    "electricity_source": "لا يوجد",
    "water_source": "بئر",
    "road_type": "غير معبد - ممهد",
    "social_security": "نعم"
}
res = client.post("/api/farms/register", data=good_data)
assert res.status_code == 200
data = res.json()
assert data["success"] is True
assert data["agri_registry"] == "SA-2026-998877"
assert "صك ملكية إلكتروني" in data["ownership_doc"]
print(f"[OK] Successfully registered farm with code: {data['code']}")

print("--- 4. Verify in Service Details Terms Page ---")
res = client.get("/services/farm-rehab")
assert res.status_code == 200
assert "إثبات الملكية أو الحيازة النظامية" in res.text
assert "توفر وإدخال رقم السجل الزراعي المطور" in res.text
# Verify that words "شرط إلزامي" or "إلزامي" are completely removed from conditions as requested
assert "شرط إلزامي" not in res.text
assert "إلزامي" not in res.text
print("[OK] Terms and Conditions unified styling verified (no 'إلزامي' badges).")

print("\n>>> ALL MANDATORY CONDITIONS TESTS PASSED! <<<")
