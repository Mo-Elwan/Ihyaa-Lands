import os
import re
import json
import shutil
import sqlite3
from starlette.testclient import TestClient
from backend.app import app, DB_PATH

ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_SRC = os.path.join(ROOT_DIR, "frontend", "static")
STATIC_DST = os.path.join(ROOT_DIR, "static")

PAGES = [
    ("/", "index.html"),
    ("/services", "services.html"),
    ("/services/farm-rehab", "services/farm-rehab.html"),
    ("/register", "register.html"),
    ("/my-requests", "my-requests.html"),
    ("/track", "track.html"),
    ("/advisory", "advisory.html"),
    ("/nafath/login", "nafath/login.html"),
    ("/admin", "admin/index.html"),
    ("/admin/inbox", "admin/inbox.html"),
    ("/admin/farms", "admin/farms.html"),
    ("/admin/map", "admin/map.html"),
    ("/admin/partners", "admin/partners.html"),
    ("/admin/visits", "admin/visits.html"),
    ("/admin/advisory", "admin/advisory.html"),
    ("/admin/reports", "admin/reports.html"),
]

ROUTE_MAP = {
    "/": "index.html",
    "/services": "services.html",
    "/services/farm-rehab": "services/farm-rehab.html",
    "/register": "register.html",
    "/my-requests": "my-requests.html",
    "/requests": "my-requests.html",
    "/track": "track.html",
    "/advisory": "advisory.html",
    "/nafath/login": "nafath/login.html",
    "/nafath/logout": "index.html",
    "/operations": "admin/index.html",
    "/admin": "admin/index.html",
    "/admin/inbox": "admin/inbox.html",
    "/admin/farms": "admin/farms.html",
    "/admin/map": "admin/map.html",
    "/admin/partners": "admin/partners.html",
    "/admin/visits": "admin/visits.html",
    "/admin/advisory": "admin/advisory.html",
    "/admin/reports": "admin/reports.html",
}


def rewrite_links(html: str, out_rel_path: str) -> str:
    depth = out_rel_path.count("/")
    prefix = "../" * depth

    # Replace /static/ references
    html = re.sub(r'(["\'])/static/', rf'\1{prefix}static/', html)

    # Replace exact route attributes: href="/..." or action="/..."
    # Sort longer routes first to avoid partial matches
    sorted_routes = sorted(ROUTE_MAP.keys(), key=len, reverse=True)
    for route in sorted_routes:
        target = prefix + ROUTE_MAP[route]
        # href="/route" or href="/route?..." or href="/route#..."
        pattern = r'((?:href|action)=["\'])' + re.escape(route) + r'([?#][^"\']*)?(["\'])'
        html = re.sub(pattern, lambda m: f"{m.group(1)}{target}{m.group(2) or ''}{m.group(3)}", html)

    # Rewrite JS window.location.href = '/admin/inbox?role=...' or `/admin/inbox?role=${...}`
    html = html.replace("`/admin/inbox?role=", f"`{prefix}admin/inbox.html?role=")
    html = html.replace("'/admin/inbox?role=", f"'{prefix}admin/inbox.html?role=")
    html = html.replace("`/my-requests", f"`{prefix}my-requests.html")
    html = html.replace("'/my-requests", f"'{prefix}my-requests.html")
    html = html.replace('"/my-requests', f'"{prefix}my-requests.html')
    html = html.replace("'/register", f"'{prefix}register.html")
    html = html.replace('"/register', f'"{prefix}register.html')

    # Inject gh_pages_adapter.js before </body>
    adapter_tag = f'<script src="{prefix}static/gh_pages_adapter.js"></script>\n</body>'
    if "</body>" in html:
        html = html.replace("</body>", adapter_tag)
    else:
        html += f'\n<script src="{prefix}static/gh_pages_adapter.js"></script>'

    return html


def main():
    # 1. Copy static assets
    if os.path.exists(STATIC_DST):
        shutil.rmtree(STATIC_DST)
    shutil.copytree(STATIC_SRC, STATIC_DST)
    os.makedirs(os.path.join(STATIC_DST, "data"), exist_ok=True)

    client = TestClient(app)

    # 2. Render all HTML pages
    for route, out_rel in PAGES:
        res = client.get(route)
        if res.status_code != 200:
            raise RuntimeError(f"Failed to render {route}: {res.status_code}")
        out_path = os.path.join(ROOT_DIR, out_rel.replace("/", os.sep))
        os.makedirs(os.path.dirname(out_path), exist_ok=True)
        html = rewrite_links(res.text, out_rel)
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] {route} -> {out_rel}")

    # 3. Export GeoJSON for static map
    geo_res = client.get("/api/farms/geojson")
    with open(os.path.join(STATIC_DST, "data", "geojson.json"), "w", encoding="utf-8") as f:
        f.write(geo_res.text)
    print("[OK] Exported static/data/geojson.json")

    # 4. Export review data for inbox farms (top 150 across all 3 inbox queues)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id FROM farms
        WHERE status IN ('مسجل', 'جديد', 'قيد المراجعة', 'محال للمعاينة الميدانية', 'بانتظار الزيارة الميدانية', 'تمت الزيارة الميدانية', 'بانتظار الاعتماد')
        ORDER BY id DESC LIMIT 150
    """)
    farm_ids = [r[0] for r in c.fetchall()]
    conn.close()

    reviews_map = {}
    for fid in farm_ids:
        r = client.get(f"/api/admin/farms/{fid}/review")
        if r.status_code == 200:
            reviews_map[str(fid)] = r.json()

    with open(os.path.join(STATIC_DST, "data", "farms_review.json"), "w", encoding="utf-8") as f:
        json.dump(reviews_map, f, ensure_ascii=False)
    print(f"[OK] Exported static/data/farms_review.json ({len(reviews_map)} farms)")


if __name__ == "__main__":
    main()
