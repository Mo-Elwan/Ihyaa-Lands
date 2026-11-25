import sys
import sqlite3

sys.stdout.reconfigure(encoding='utf-8')

from starlette.testclient import TestClient
from backend.app import app, DB_PATH

client = TestClient(app)

print("--- 1. Testing /admin/inbox Page Load & Role Elements ---")
res = client.get("/admin/inbox")
assert res.status_code == 200
html = res.text

assert "صندوق معالجة الطلبات" in html
assert "1. موظف الفرع" in html
assert "2. فني الزيارة الميدانية" in html
assert "3. مدير الفرع" in html
assert "role-card-auditor" in html
assert "role-card-inspector" in html
assert "role-card-manager" in html
print("[OK] Inbox page loads successfully with all 3 distinct role cards.")

print("--- 2. Registering a Fresh Farm for the Approval Chain ---")
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
    "area_m2": 15000,
    "land_status": "غير محياة",
    "water_source": "بئر",
    "electricity_source": "لا يوجد",
    "previous_crops": "رمان وبن",
    "priority_needs_text": "صيانة بئر وشبكة ري",
    "road_type": "معبد",
    "social_security": "نعم"
}

res_reg = client.post("/api/farms/register", data=payload)
assert res_reg.status_code == 200
data_reg = res_reg.json()
code = data_reg["code"]
print(f"[OK] New Farm created: {code}")

# Get Farm ID from DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT id, status FROM farms WHERE code = ?", (code,))
farm_row = c.fetchone()
farm_id = farm_row["id"]
assert farm_row["status"] == "مسجل"
conn.close()
print(f"[OK] Farm {code} (ID: {farm_id}) is in Initial State: 'مسجل' (Auditor Inbox).")

print("--- 3. Testing Role 1 (موظف الفرع): Approve Audit & Transfer to Inspector ---")
action_payload_1 = {
    "farm_id": farm_id,
    "role": "auditor",
    "action": "approve_audit",
    "notes": "تم التحقق من صك الملكية وسريان السجل الزراعي"
}
res_act1 = client.post("/api/admin/inbox/action", data=action_payload_1)
assert res_act1.status_code == 200
act1_data = res_act1.json()
assert act1_data["success"] is True
assert act1_data["new_status"] == "محال للمعاينة الميدانية"
print(f"[OK] Auditor approved farm: Status updated to '{act1_data['new_status']}' (Moved to Inspector).")

print("--- 4. Testing Role 2 (فني الزيارة الميدانية): Submit Field Inspection Report ---")
action_payload_2 = {
    "farm_id": farm_id,
    "role": "inspector",
    "action": "submit_inspection_report",
    "inspector_name": "م. فيصل الغامدي",
    "visit_date": "2026-11-20",
    "water_eval": "بئر سطحي صالح يحتاج مضخة موفرة",
    "irrigation_eval": "يحتاج شبكة ري بالتنقيط حديثة",
    "soil_eval": "تربة طينية ممتازة",
    "recommended_seedlings": "400 شتلة بن خولاني و100 شتلة لوز",
    "notes": "المزرعة واعدة وجاهزية التأهيل عالية"
}
res_act2 = client.post("/api/admin/inbox/action", data=action_payload_2)
assert res_act2.status_code == 200
act2_data = res_act2.json()
assert act2_data["success"] is True
assert act2_data["new_status"] == "تمت الزيارة الميدانية"
print(f"[OK] Inspector submitted technical report: Status updated to '{act2_data['new_status']}' (Moved to Manager).")

print("--- 5. Testing Role 3 (مدير الفرع): Approve Rehabilitation Plan & Allocate Support ---")
action_payload_3 = {
    "farm_id": farm_id,
    "role": "manager",
    "action": "approve_plan",
    "support_path": "مسار القرض الحسن والدعم التنموي (بنك التنمية الاجتماعية / شركة أزكى)",
    "notes": "يُعتمد إدراج المزرعة ضمن الدفعة الأولى لصرف القرض الحسن وتوريد الشتلات"
}
res_act3 = client.post("/api/admin/inbox/action", data=action_payload_3)
assert res_act3.status_code == 200
act3_data = res_act3.json()
assert act3_data["success"] is True
assert act3_data["new_status"] == "جاري التأهيل"
print(f"[OK] Manager approved rehabilitation: Status updated to '{act3_data['new_status']}'.")

# Final DB Verification
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()
c.execute("SELECT status, support_status, assigned_partner_name, notes FROM farms WHERE id = ?", (farm_id,))
final_row = c.fetchone()
assert final_row["status"] == "جاري التأهيل"
assert final_row["support_status"] == "مخصص"
assert "القرض الحسن" in final_row["assigned_partner_name"]
assert "التدقيق المكتبي" in final_row["notes"]
assert "فني الميدان" in final_row["notes"]
assert "مدير الفرع" in final_row["notes"]
conn.close()

print(f"[OK] DB Verified: Full 3-role approval lifecycle executed smoothly and logged in farm notes.")
print("\n>>> ALL TESTS FOR UNIFIED INBOX & 3 ROLES WORKFLOW PASSED 100%! <<<")
