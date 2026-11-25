import uvicorn
import webbrowser
import time
import threading

def open_browser():
    time.sleep(1.5)
    print("\n[INFO] جاري فتح المنصة في المتصفح تلقائياً: http://127.0.0.1:8000 ...")
    webbrowser.open("http://127.0.0.1:8000")

if __name__ == "__main__":
    print("=" * 60)
    print("منصة «إحياء» الوطنية لحصر وتأهيل المزارع المهملة")
    print("وزارة البيئة والمياه والزراعة - وكالة شؤون الفروع")
    print("=" * 60)
    print("الخادم يعمل الآن على الرابط:")
    print("  - بوابة المستفيد والمزارع : http://127.0.0.1:8000")
    print("  - بوابة مدير النظام واللجنة: http://127.0.0.1:8000/admin")
    print("=" * 60)
    
    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run("backend.app:app", host="127.0.0.1", port=8000, reload=False)
