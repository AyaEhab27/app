import os
import firebase_admin
from firebase_admin import credentials

# المسار إلى ملف Firebase config
firebase_config_path = os.path.join(os.path.dirname(__file__), 'config', 'sound-6893c-firebase-adminsdk-fbsvc-8104119578.json')

# تهيئة Firebase
try:
    cred = credentials.Certificate(firebase_config_path)
firebase_admin.initialize_app(cred, {
    'storageBucket': 'sound-6893c.appspot.com'  
})
    print("✅ Firebase initialized successfully!")
except Exception as e:
    print(f"❌ Error initializing Firebase: {e}")
