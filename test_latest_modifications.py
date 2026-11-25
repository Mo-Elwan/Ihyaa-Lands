import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

from starlette.testclient import TestClient
from backend.app import app, DB_PATH

client = TestClient(app)

print("--- 0. Logging in via Nafath ---")
client.post("/api/nafath/initiate", data={"national_id": "1087452190"})
client.post("/api/nafath/confirm", data={"national_id": "1087452190", "farmer_name": "سعد بن محمد القحطاني"})

print("--- 1. Testing /register HTML for City, Cloud Link, and Mandatory Fields ---")
res = client.get("/register")
assert res.status_code == 200
html = res.text

# 1. City replaced Center and Village
assert 'name="city" id="city" readonly' in html
assert 'المدينة <span class="text-red-500">*</span>' in html
assert 'data-city="' in html
print("[OK] City field replaced center and village in the location section and is read-only.")

# 2. Cloud Video Link is Deleted
assert 'رابط صور أو فيديو إضافي سحابي' not in html
assert 'Google Drive / OneDrive / YouTube' not in html
print("[OK] Cloud link (Google Drive / OneDrive / YouTube) is completely removed.")

# 3. Previous Crops and Priority Needs Text are Mandatory (HTML required) with Red Star only (no '(إلزامي)')
assert '<textarea name="previous_crops" id="previous_crops" rows="3" required' in html
assert '<textarea name="priority_needs_text" id="priority_needs_text" rows="3" required' in html
assert '(إلزامي)' not in html
assert '(الزامي)' not in html
print("[OK] (إلزامي) removed completely; replaced by red star (*) only, with inputs marked required.")

print("--- 2. Testing Server-Side Mandatory Validation for previous_crops ---")
base_payload = {
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
    "center": "مركز بني كبير",
    "village": "قرية الحدب",
    "area_m2": 12000,
    "land_status": "غير محياة",
    "water_source": "بئر",
    "electricity_source": "لا يوجد",
    "previous_crops": "",
    "priority_needs_text": "حفر بئر وتوفير شتلات",
    "media_descriptions": ["صورة البئر"],
    "road_type": "معبد",
    "social_security": "نعم"
}

# Sending empty previous_crops must fail with 400
res_crops_empty = client.post("/api/farms/register", data=base_payload)
assert res_crops_empty.status_code == 400
assert "المزروعات السابقة أو الحالية إلزامي" in res_crops_empty.json()["message"]
print("[OK] Empty previous_crops correctly rejected with HTTP 400.")

print("--- 3. Testing Server-Side Mandatory Validation for priority_needs_text ---")
payload_no_needs = dict(base_payload)
payload_no_needs["previous_crops"] = "رمان ولوز"
payload_no_needs["priority_needs_text"] = "   "

res_needs_empty = client.post("/api/farms/register", data=payload_no_needs)
assert res_needs_empty.status_code == 400
assert "أهم احتياجات التأهيل المطلوبة للمزرعة إلزامي" in res_needs_empty.json()["message"]
print("[OK] Empty priority_needs_text correctly rejected with HTTP 400.")

print("--- 4. Testing Valid Registration with City Saved to Database ---")
valid_payload = dict(base_payload)
valid_payload["previous_crops"] = "رمان ولوز وخوخ"
valid_payload["priority_needs_text"] = "تمديد شبكة ري بالتنقيط وحفر بئر"
valid_payload["city"] = "بلجرشي"

res_valid = client.post("/api/farms/register", data=valid_payload)
assert res_valid.status_code == 200
data = res_valid.json()
assert data["success"] is True
code = data["code"]
print(f"[OK] Farm successfully registered: {code}")

# Verify in DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT * FROM farms WHERE code = ?", (code,))
row = c.fetchone()
assert row is not None
assert row["city"] == "بلجرشي"
assert row["previous_crops"] == "رمان ولوز وخوخ"
assert "تمديد شبكة ري بالتنقيط وحفر بئر" in row["notes"]
conn.close()

print(f"[OK] Database verified: farm {code} has city='بلجرشي' and mandatory fields correctly recorded.")

print("--- 5. Testing Registration Without Any Attachments (Optional) ---")
no_attachments_payload = dict(valid_payload)
del no_attachments_payload["media_descriptions"]
res_no_attach = client.post("/api/farms/register", data=no_attachments_payload)
assert res_no_attach.status_code == 200
data_no_attach = res_no_attach.json()
assert data_no_attach["success"] is True
print(f"[OK] Registration without attachments succeeded smoothly: {data_no_attach['code']}")

print("\n>>> ALL TESTS FOR LATEST MODIFICATIONS PASSED 100%! <<<")
