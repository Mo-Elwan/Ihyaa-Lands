from starlette.testclient import TestClient
from backend.app import app

client = TestClient(app)

print("--- 1. Testing Services Directory ---")
res = client.get("/")
assert res.status_code == 200
assert "دليل الخدمات الإلكترونية" in res.text
assert "طلب حصر وتأهيل مزرعة مهملة" in res.text
print("[OK] Services Directory loaded successfully.")

print("--- 2. Testing Service Details & Terms ---")
res = client.get("/services/farm-rehab")
assert res.status_code == 200
assert "الشروط والضوابط المعتمدة للخدمة" in res.text
assert "طلب الخدمة (عبر النفاذ الوطني)" in res.text
print("[OK] Service Details page loaded successfully.")

print("--- 3. Testing Nafath Login Page ---")
res = client.get("/nafath/login")
assert res.status_code == 200
assert "دخول الأفراد من مواطنين ومقيمين" in res.text
assert "رقم الهوية / الإقامة" in res.text
print("[OK] Nafath Login Page loaded successfully.")

print("--- 4. Testing Nafath Initiation API ---")
res = client.post("/api/nafath/initiate", data={"national_id": "1098765432"})
assert res.status_code == 200
data = res.json()
assert data["success"] is True
assert "code" in data
code = data["code"]
print(f"[OK] Nafath initiated successfully with 2-digit confirmation code: {code}")

print("--- 5. Testing Nafath Confirmation & Session ---")
res = client.post("/api/nafath/confirm", data={"national_id": "1098765432", "farmer_name": "سعيد الزهراني"})
assert res.status_code == 200
data = res.json()
assert data["success"] is True
assert data["redirect_url"] == "/register"
print("[OK] Nafath confirmed and session saved.")

print("--- 6. Testing Authenticated Application Page ---")
res = client.get("/register")
assert res.status_code == 200
assert "مواطن موثق عبر النفاذ الوطني الموحد" in res.text
assert "1098765432" in res.text
print("[OK] Register page verified user identity via Nafath session.")

print("--- 7. Testing Internal Operations Portal ---")
res = client.get("/admin")
assert res.status_code == 200
assert "لوحة المؤشرات والقيادة" in res.text
print("[OK] Internal Application Processing portal loaded.")

print("\n>>> ALL TESTS PASSED SUCCESSFULLY! <<<")
