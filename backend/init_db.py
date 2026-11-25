import sqlite3
import pandas as pd
import numpy as np
import re
import os
import sys
import io
import random
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

DB_PATH = os.path.join(os.path.dirname(__file__), 'ihyaa_platform.db')
EXCEL_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'إحياء المزارع المهملة  (الردود) (10).xlsx')

# Regional approximate central coordinates (Lat, Lng)
REGION_COORDS = {
    'الباحة': (20.0129, 41.4677),
    'عسير': (18.2164, 42.5053),
    'المدينة المنورة': (24.5247, 39.5692),
    'مكة المكرمة': (21.3891, 39.8579),
    'الرياض': (24.7136, 46.6753),
    'حائل': (27.5236, 41.6966),
    'المنطقة الشرقية': (26.4207, 50.0888),
    'جازان': (16.8892, 42.5511),
    'نجران': (17.4933, 44.1277),
    'تبوك': (28.3835, 36.5662),
    'القصيم': (26.3260, 43.9750),
    'الجوف': (29.8870, 39.3206),
    'الحدود الشمالية': (30.9753, 41.0381)
}

def extract_coords(url_or_text, region):
    if not isinstance(url_or_text, str) or not url_or_text.strip():
        center = REGION_COORDS.get(region, (24.0, 45.0))
        # natural jitter ~ 15-30km
        return center[0] + random.uniform(-0.15, 0.15), center[1] + random.uniform(-0.15, 0.15)
    
    # Try regex search for lat,lng
    m = re.search(r'([-+]?[1-3]\d\.\d+)[,\s]+([-+]?[3-5]\d\.\d+)', url_or_text)
    if m:
        try:
            lat = float(m.group(1))
            lng = float(m.group(2))
            if 15.0 <= lat <= 33.0 and 34.0 <= lng <= 56.0:
                return lat, lng
        except:
            pass

    # Reverse order if any
    m2 = re.search(r'q=([-+]?[1-3]\d\.\d+),([-+]?[3-5]\d\.\d+)', url_or_text)
    if m2:
        try:
            lat = float(m2.group(1))
            lng = float(m2.group(2))
            if 15.0 <= lat <= 33.0 and 34.0 <= lng <= 56.0:
                return lat, lng
        except:
            pass

    center = REGION_COORDS.get(region, (24.0, 45.0))
    return center[0] + random.uniform(-0.18, 0.18), center[1] + random.uniform(-0.18, 0.18)

def determine_smart_solution(region, water, elec, status, area, prev_crop, social_sec):
    solutions = []
    priority = "أولوية 2"
    cost = 35000.0

    has_water = any(w in str(water) for w in ['بئر', 'خزان', 'يوجد', 'نعم'])
    has_elec = any(e in str(elec) for e in ['يوجد', 'نعم', 'طاقة'])
    is_rehabilitated = 'محياه' in str(status) and 'غير' not in str(status)
    is_social = 'نعم' in str(social_sec)

    # Water solutions
    if not has_water:
        if region in ['الباحة', 'عسير']:
            solutions.append("حفر/تعميق بئر سطحي وتركيب خزان تجميع مياه أمطار جبلي")
            cost += 45000
        elif region in ['تبوك', 'الجوف', 'الحدود الشمالية', 'حائل']:
            solutions.append("حفر بئر ارتوازي وتأهيل خزان خرساني أرضي")
            cost += 60000
        else:
            solutions.append("إنشاء خزان مائي وتمديد خط تغذية من أقرب نقطة ري")
            cost += 25000
    else:
        solutions.append("صيانة البئر وتطهيره وتركيب مضخة غاطسة موفرة للطاقة")
        cost += 12000

    # Electricity solutions
    if not has_elec:
        if region in ['جازان', 'نجران', 'تبوك', 'الحدود الشمالية']:
            solutions.append("تركيب منظومة طاقة شمسية مستقلة (10-15 كيلوواط) لتشغيل المضخات والإنارة")
            cost += 38000
        else:
            solutions.append("تركيب منظومة طاقة شمسية زراعية مدعومة من صندوق التنمية الزراعية")
            cost += 32000
    else:
        solutions.append("صيانة اللوحات الكهربائية وربط العداد الزراعي")
        cost += 5000

    # Irrigation & Agriculture solutions
    solutions.append("توريد وتركيب شبكة ري حديثة بالتنقيط (GR) مع فلاتر ذكية")
    cost += max(8000.0, float(area if area and area > 0 else 5000) * 1.5)

    # Crop & Seedlings according to region
    if region in ['الباحة', 'عسير']:
        solutions.append("توريد 400 شتلة بن خولاني/صافي شدوي وشتلات رمان ولوز بلدي")
    elif region in ['المدينة المنورة', 'القصيم', 'الرياض']:
        solutions.append("توريد 150 فسيلة نخيل نسيجية عالية الجودة وأشجار حمضيات وسدر")
    elif region in ['المنطقة الشرقية']:
        solutions.append("إحلال 200 فسيلة نخيل خلاص الأحساء وأشجار كينوقاربوس مصدات رياح")
    elif region in ['جازان']:
        solutions.append("تزويد المزرعة بشتلات مانجو عويس وتومي وبابايا معالجة")
    elif region in ['نجران']:
        solutions.append("توريد شتلات حمضيات نجرانية ونخيل وشتلات مصدات رياح")
    else:
        solutions.append("توريد 250 شتلة زيتون وفواكه صيفية ملائمة للمنطقة")

    # Partnership / Social Funding model
    if is_social:
        solutions.append("إدراج المزرعة ضمن مسار المنح المجتمعية والقرض الحسن (شركة أزكى/بنك التنمية)")
    else:
        solutions.append("مسار الشراكة مع الجمعيات التعاونية أو الاستثمار الأهلي للحيازات")

    # Priority determination
    if has_water and has_elec:
        priority = "أولوية 1 (جاهزية عالية - تأهيل سريع)"
    elif has_water or has_elec:
        priority = "أولوية 2 (جاهزية متوسطة - يحتاج استكمال)"
    else:
        priority = "أولوية 3 (جاهزية منخفضة - استصلاح شامل)"

    return priority, " + ".join(solutions), round(cost, 2)

def init_database():
    print(f"Connecting to DB: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # Drop existing tables
    cursor.execute("DROP TABLE IF EXISTS farms")
    cursor.execute("DROP TABLE IF EXISTS partners")
    cursor.execute("DROP TABLE IF EXISTS support_allocations")
    cursor.execute("DROP TABLE IF EXISTS field_visits")
    cursor.execute("DROP TABLE IF EXISTS advisory_requests")
    cursor.execute("DROP TABLE IF EXISTS system_users")

    # Create tables
    cursor.execute("""
    CREATE TABLE farms (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE,
        created_at TEXT,
        farmer_name TEXT,
        national_id TEXT,
        phone TEXT,
        region TEXT,
        governorate TEXT,
        center TEXT,
        village TEXT,
        maps_url TEXT,
        latitude REAL,
        longitude REAL,
        land_status TEXT,
        area_m2 REAL,
        electricity_source TEXT,
        water_source TEXT,
        previous_crops TEXT,
        media_urls TEXT,
        road_type TEXT,
        social_security TEXT,
        agricultural_registry TEXT,
        status TEXT,
        readiness_priority TEXT,
        suggested_solution TEXT,
        solution_cost_est REAL,
        assigned_partner_name TEXT,
        support_status TEXT,
        notes TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE partners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        category TEXT,
        region TEXT,
        contribution_type TEXT,
        committed_quantity INTEGER,
        delivered_quantity INTEGER,
        unit TEXT,
        phone TEXT,
        email TEXT,
        status TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE support_allocations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER,
        partner_id INTEGER,
        support_type TEXT,
        quantity INTEGER,
        status TEXT,
        allocated_date TEXT,
        notes TEXT,
        FOREIGN KEY(farm_id) REFERENCES farms(id),
        FOREIGN KEY(partner_id) REFERENCES partners(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE field_visits (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER,
        team_name TEXT,
        visit_date TEXT,
        status TEXT,
        soil_quality TEXT,
        water_salinity_tds INTEGER,
        recommendations TEXT,
        inspector_name TEXT,
        FOREIGN KEY(farm_id) REFERENCES farms(id)
    )
    """)

    cursor.execute("""
    CREATE TABLE advisory_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farm_id INTEGER,
        farmer_name TEXT,
        farmer_phone TEXT,
        topic TEXT,
        inquiry TEXT,
        reply TEXT,
        advisor_name TEXT,
        status TEXT,
        created_at TEXT
    )
    """)

    cursor.execute("""
    CREATE TABLE system_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password_hash TEXT,
        full_name TEXT,
        role TEXT,
        role_label TEXT,
        region TEXT
    )
    """)

    # Seed Default Users
    users = [
        ('admin', 'admin123', 'م. فهد الزهراني - رئيس لجنة المبادرة', 'admin', 'مدير النظام ورئيس اللجنة', 'كافة المناطق'),
        ('soliman', 'admin123', 'أ. سليمان الجطيلي - نائب رئيس اللجنة', 'committee_head', 'نائب رئيس اللجنة', 'كافة المناطق'),
        ('makkah_mgr', 'user123', 'م. خالد القرشي - مدير فرع منطقة مكة', 'branch_manager', 'مدير فرع الوزارة', 'مكة المكرمة'),
        ('baha_mgr', 'user123', 'م. سعيد الغامدي - مدير فرع منطقة الباحة', 'branch_manager', 'مدير فرع الوزارة', 'الباحة'),
        ('asir_mgr', 'user123', 'م. عبدالله الشهري - مدير فرع منطقة عسير', 'branch_manager', 'مدير فرع الوزارة', 'عسير'),
        ('madinah_mgr', 'user123', 'م. أحمد الحربي - مدير فرع منطقة المدينة', 'branch_manager', 'مدير فرع الوزارة', 'المدينة المنورة'),
        ('eastern_mgr', 'user123', 'م. محمد الدوسري - مدير فرع المنطقة الشرقية', 'branch_manager', 'مدير فرع الوزارة', 'المنطقة الشرقية'),
        ('field_agent1', 'field123', 'م. عمر العتيبي - مفتش ميداني', 'field_inspector', 'أخصائي حصر ومعاينة ميدانية', 'مكة المكرمة'),
        ('field_agent2', 'field123', 'م. يحيى الزهراني - مفتش ميداني', 'field_inspector', 'أخصائي حصر ومعاينة ميدانية', 'الباحة')
    ]
    cursor.executemany("INSERT INTO system_users (username, password_hash, full_name, role, role_label, region) VALUES (?,?,?,?,?,?)", users)

    # Seed Official Partners from October report
    partners_data = [
        ('جمعية البن الصافي الشدوي', 'جمعيات وأهلية', 'الباحة', 'استثمار أهلي للحيازات وشتلات بن', 23000, 15000, 'شتلة', '0501234567', 'info@shadacoffee.sa', 'نشط'),
        ('جمعية الباحة الخضراء', 'جمعيات وأهلية', 'الباحة', 'شتلات رمان ولوز وأشجار غطاء نباتي', 100000, 42000, 'شتلة', '0502345678', 'contact@greenbaha.sa', 'نشط'),
        ('جمعية البن التعاونية', 'جمعيات وأهلية', 'عسير', 'شتلات بن ومعدات حصاد وري', 50000, 20000, 'شتلة', '0503456789', 'info@coopcoffee.sa', 'نشط'),
        ('شركة أزكى للاستثمار الزراعي', 'شركات ومستثمرين', 'الباحة', 'قرض حسن بدون فوائد مقابل ثلث المحصول', 1000000, 350000, 'ريال', '0504567890', 'support@azka.sa', 'نشط'),
        ('مكتب وزارة البيئة بالأحساء والجمعيات الشريكة', 'مشاتل وجهات أهلية', 'المنطقة الشرقية', 'فسائل نخيل خلاص ومصدات رياح', 50000, 18500, 'فسيلة', '0505678901', 'alahsa@mewa.gov.sa', 'نشط'),
        ('مشاتل نجران الوطنية المعتمدة (50 مشتل)', 'مشاتل', 'نجران', 'شتلات حمضيات وسدر ونخيل', 45000, 12000, 'شتلة', '0506789012', 'info@najran-nurseries.sa', 'نشط'),
        ('المؤسسة العامة للري', 'جهات حكومية وشبه حكومية', 'المنطقة الشرقية', 'تأهيل شبكات ومصادر الري والمياه المعالجة', 2000, 650, 'مزرعة', '0138000000', 'info@eta.gov.sa', 'نشط'),
        ('صندوق التنمية الزراعية', 'تمويل وإقراض', 'كافة المناطق', 'تمويل تقنيات الري والطاقة الشمسية الميسر', 5000000, 1800000, 'ريال', '199080', 'care@adf.gov.sa', 'نشط'),
        ('مركز وقاء (مكافحة الآفات النباتية والحيوانية)', 'جهات حكومية وشبه حكومية', 'كافة المناطق', 'فحص التربة ومكافحة سوسة النخيل والآفات الحرجية', 3000, 920, 'زيارة واستشارة', '933', 'weqaa@weqaa.gov.sa', 'نشط')
    ]
    cursor.executemany("""
    INSERT INTO partners (name, category, region, contribution_type, committed_quantity, delivered_quantity, unit, phone, email, status)
    VALUES (?,?,?,?,?,?,?,?,?,?)
    """, partners_data)

    # Read and parse Excel file
    print(f"Reading Excel: {EXCEL_PATH}")
    df = pd.read_excel(EXCEL_PATH)
    df.columns = df.columns.str.strip()

    maps_col = [c for c in df.columns if 'google' in c.lower() or 'maps' in c.lower()][0]

    farms_rows = []
    statuses = ['مسجل', 'قيد المراجعة', 'تمت الزيارة الميدانية', 'جاري التأهيل', 'مؤهلة ومنتجة']
    status_weights = [0.45, 0.25, 0.15, 0.10, 0.05]

    for index, row in df.iterrows():
        fid = index + 1
        code = f"FRM-{fid:04d}"
        created_at = str(row.get('طابع زمني', datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        farmer_name = str(row.get('اسم المزارع', f'مزارع {fid}')).strip()
        national_id = str(row.get('السجل مدني', '')).replace('.0', '').strip()
        phone = str(row.get('رقم التواصل', '')).replace('.0', '').strip()
        region = str(row.get('المنطقة', 'غير محدد')).strip()
        gov = str(row.get('المحافظة', '')).strip()
        center = str(row.get('المركز', '')).strip()
        village = str(row.get('القرية / الحي', '')).strip()
        maps_raw = str(row.get(maps_col, '')).strip()
        land_status = str(row.get('حالة الارض الزراعية', 'غير محياة')).strip()
        
        try:
            area = float(str(row.get('المساحة (م2)', 0)).replace(',', '').strip())
        except:
            area = 5000.0

        elec = str(row.get('مصدر الكهرباء', 'لا يوجد')).strip()
        water = str(row.get('مصدر المياه', 'لا يوجد')).strip()
        prev_crop = str(row.get('المزروعات السابقة', '')).strip()
        media = str(row.get('ارفاق صور او مقطع فيديو للمزرعة', '')).strip()
        road = str(row.get('الطرق', 'يوجد')).strip()
        social_sec = str(row.get('هل مسجل في الضمان الاجتماعي', 'لا')).strip()

        # Coords
        lat, lng = extract_coords(maps_raw, region)

        # Priority & Smart Solution
        priority, solution, cost = determine_smart_solution(region, water, elec, land_status, area, prev_crop, social_sec)

        # Status distribution - first 30 in Makkah are qualified according to report
        if region == 'مكة المكرمة' and index < 30:
            farm_status = 'مؤهلة ومنتجة'
            support_status = 'متحقَّق منه'
            assigned_partner = 'جمعية البر الزراعية بمكة'
        elif region == 'الباحة' and 'شدا' in (gov + center + village):
            farm_status = 'جاري التأهيل'
            support_status = 'مخصص'
            assigned_partner = 'جمعية البن الصافي الشدوي'
        else:
            farm_status = random.choices(statuses, weights=status_weights)[0]
            if farm_status == 'مؤهلة ومنتجة':
                support_status = 'متحقَّق منه'
                assigned_partner = 'شركة أزكى للاستثمار الزراعي'
            elif farm_status == 'جاري التأهيل':
                support_status = 'مخصص'
                assigned_partner = 'جمعية الباحة الخضراء'
            elif farm_status == 'تمت الزيارة الميدانية':
                support_status = 'متعهد به'
                assigned_partner = 'مشاتل نجران الوطنية المعتمدة (50 مشتل)'
            else:
                support_status = 'متاح'
                assigned_partner = 'قيد الترشيح'

        # Sijill Zira'i status
        if index % 3 == 0:
            agri_reg = f"SA-2026-{100000 + fid}"
        else:
            agri_reg = "طلب إصدار قائم (منظومة نما)"

        farms_rows.append((
            code, created_at, farmer_name, national_id, phone, region, gov, center, village,
            maps_raw if maps_raw and maps_raw != 'nan' else f"https://maps.google.com/?q={lat:.5f},{lng:.5f}",
            lat, lng, land_status, area, elec, water, prev_crop,
            media if media and media != 'nan' else "",
            road, social_sec, agri_reg, farm_status, priority, solution, cost,
            assigned_partner, support_status, "تم الحصر ضمن مبادرة إحياء المزارع المهملة"
        ))

    print(f"Inserting {len(farms_rows)} farms into DB...")
    cursor.executemany("""
    INSERT INTO farms (
        code, created_at, farmer_name, national_id, phone, region, governorate, center, village,
        maps_url, latitude, longitude, land_status, area_m2, electricity_source, water_source,
        previous_crops, media_urls, road_type, social_security, agricultural_registry, status,
        readiness_priority, suggested_solution, solution_cost_est, assigned_partner_name, support_status, notes
    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, farms_rows)

    # Add sample field visits for visited farms
    cursor.execute("SELECT id, region, governorate FROM farms WHERE status IN ('تمت الزيارة الميدانية', 'جاري التأهيل', 'مؤهلة ومنتجة') LIMIT 150")
    visited_farms = cursor.fetchall()
    visits = []
    inspectors = ['م. عمر العتيبي', 'م. يحيى الزهراني', 'م. خالد الشهري', 'م. عادل المطيري', 'م. فهد السبيعي']
    for row in visited_farms:
        fid, reg, gov = row
        visits.append((
            fid,
            f"فريق المعاينة الميدانية - فرع {reg}",
            "2026-10-18",
            "مكتملة",
            "تربة طميية صالحة للزراعة، تحتاج تقليب وإزالة حشائش",
            random.randint(450, 1400),
            "يوصى بتركيب منظومة طاقة شمسية وغاطس 5 حصان وشبكة تنقيط",
            random.choice(inspectors)
        ))
    cursor.executemany("""
    INSERT INTO field_visits (farm_id, team_name, visit_date, status, soil_quality, water_salinity_tds, recommendations, inspector_name)
    VALUES (?,?,?,?,?,?,?,?)
    """, visits)

    # Add sample agricultural advisory requests
    advisory_samples = [
        (1, 'عطيه عبدالله', '0555577880', 'المحاصيل الملائمة للمنطقة', 'ما هي أفضل أصناف الفواكه المناسبة لمنطقة القنفذة مع قلة المياه؟', 'يوصى بزراعة المانجو والبابايا وأشجار السدر، مع استخدام شبكة تنقيط لتوفير 40% من المياه.', 'د. عبدالعزيز الفهيد - مرشد زراعي أول', 'تم الرد', '2026-10-20'),
        (2, 'محمد علي الأسمري', '0501122334', 'تطهير الآبار السطحية', 'البئر لدينا قديم ومردوم جزئياً، كيف يتم تنظيفه وإعادة تشغيله؟', 'سيتم إدراج مزرعتكم ضمن مسار دعم تعميق وتطهير الآبار بالتعاون مع المؤسسة العامة للري وتركيب غاطس حديث.', 'م. إبراهيم القحطاني', 'تم الرد', '2026-10-22'),
        (5, 'سالم بن مريع', '0544332211', 'الطاقة الشمسية للمزارع', 'هل تكلفة الألواح الشمسية مغطاة بالقرض الحسن؟', 'نعم، مسار القرض الحسن بالتنسيق مع شركة أزكى وصندوق التنمية الزراعية يغطي كامل تكاليف الطاقة الشمسية بدون أي فوائد.', 'م. ناصر الغامدي', 'تم الرد', '2026-10-25'),
    ]
    cursor.executemany("""
    INSERT INTO advisory_requests (farm_id, farmer_name, farmer_phone, topic, inquiry, reply, advisor_name, status, created_at)
    VALUES (?,?,?,?,?,?,?,?,?)
    """, advisory_samples)

    conn.commit()
    conn.close()
    print("Database initialization completed successfully!")

if __name__ == '__main__':
    init_database()
