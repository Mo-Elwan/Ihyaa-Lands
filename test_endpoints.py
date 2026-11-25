from starlette.testclient import TestClient
from backend.app import app

client = TestClient(app)

endpoints = [
    ('/', 200),
    ('/register', 200),
    ('/track', 200),
    ('/track?query=FRM-0001', 200),
    ('/advisory', 200),
    ('/admin', 200),
    ('/admin/farms', 200),
    ('/admin/farms/1', 200),
    ('/admin/map', 200),
    ('/admin/partners', 200),
    ('/admin/visits', 200),
    ('/admin/advisory', 200),
    ('/admin/reports', 200),
    ('/admin/farms/1/print', 200),
    ('/api/farms/geojson?region=الباحة', 200)
]

passed = 0
for url, expected in endpoints:
    res = client.get(url)
    if res.status_code == expected:
        passed += 1
        print(f"[OK] {url} -> {res.status_code}")
    else:
        print(f"[FAIL] {url} -> {res.status_code}")
        print(res.text[:300])

print(f"\nSummary: {passed}/{len(endpoints)} tests passed.")
