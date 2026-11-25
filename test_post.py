from starlette.testclient import TestClient
from backend.app import app

client = TestClient(app)

# Test new registration
reg_data = {
    'farmer_name': 'سعيد بن مسفر الغامدي',
    'national_id': '1098765432',
    'phone': '0509988776',
    'region': 'الباحة',
    'governorate': 'بلجرشي',
    'center': 'بني كبير',
    'village': 'قرية الغبر',
    'maps_url': 'https://maps.google.com/?q=19.9012,41.5678',
    'latitude': 19.9012,
    'longitude': 41.5678,
    'land_status': 'غير محياة',
    'area_m2': 15000.0,
    'electricity_source': 'لا يوجد',
    'water_source': 'لا يوجد',
    'previous_crops': 'لوز ورمان',
    'road_type': 'غير معبد - ممهد',
    'social_security': 'نعم',
    'has_agri_registry': 'no',
    'agri_registry_number': '',
    'media_urls': 'https://drive.google.com/test',
    'notes': 'مزرعة وراثية مهملة منذ 8 سنوات وبحاجة إلى بئر وطاقة شمسية'
}

res = client.post('/api/farms/register', data=reg_data)
print('Register status:', res.status_code)
json_data = res.json()
print('Register response:', json_data)
assert json_data['success'] is True
new_code = json_data['code']

# Verify tracking
track_res = client.get(f'/track?query={new_code}')
print('Tracking newly registered farm status:', track_res.status_code)
assert track_res.status_code == 200
assert 'سعيد بن مسفر الغامدي' in track_res.text

print('\nEnd-to-End Registration & Tracking Test: SUCCESS!')
