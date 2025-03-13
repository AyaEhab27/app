import cv2
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel
import mediapipe as mp
import os
import time
import base64
from gtts import gTTS
from fastapi.middleware.cors import CORSMiddleware
import firebase_admin
from firebase_admin import credentials, storage
import uuid

# Initialize Firebase
cred = credentials.Certificate("path/to/serviceAccountKey.json")  # Replace with your path
firebase_admin.initialize_app(cred, {
    'storageBucket': 'your-storage-bucket-url'  # Replace with your Firebase Storage bucket URL
})

# Function to upload file to Firebase Storage
def upload_to_firebase(file_path, destination_path):
    bucket = storage.bucket()
    blob = bucket.blob(destination_path)
    blob.upload_from_filename(file_path)
    blob.make_public()
    return blob.public_url

# Start API
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

# Model paths
model_paths = {
    "arabic_letters": "app/models/Aalpha2_sign_language_model.h5",
    "arabic_numbers": "app/models/AN2_sign_language_model.h5",
    "english_letters": "app/models/E_alpha_sign_language_model.h5",
    "english_numbers": "app/models/EN_sign_language_model.h5"
}

# Load models
models = {}
for key, path in model_paths.items():
    models[key] = tf.keras.models.load_model(path)
    models[key].compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])

# Categories
categories = {
    "arabic_letters": [ "ain", "al", "alef", "beh", "dad", "dal", "feh", "ghain", "hadhf", "hah", "heh", "jeem", "kaf", "khah", "laa", "lam", "masafa", "meem", "noon", "qaf", "reh", "sad", "seen", "sheen", "tah", "teh", "teh_marbuta", "thal", "theh", "waw", "yeh", "zah", "zain"],
    "arabic_numbers": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9","hadhf","masafa"],
    "english_letters": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z","delete","space"],
    "english_numbers": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9","delete","space"]
}

# Mapping
mapping = {
    "arabic_letters": {
        "ain": "ع", "al": "ال", "alef": "أ", "beh": "ب", "dad": "ض", "dal": "د", "feh": "ف", "ghain": "غ", "hadhf": "حذف", "hah": "ح", 
        "heh": "ه", "jeem": "ج", "kaf": "ك", "khah": "خ", "laa": "لا", "lam": "ل", "masafa": "مسافة", "meem": "م", "noon": "ن", "qaf": "ق", 
        "reh": "ر", "sad": "ص", "seen": "س", "sheen": "ش", "tah": "ط", "teh": "ت", "teh_marbuta": "ة", "thal": "ذ", "theh": "ث", "waw": "و", 
        "yeh": "ي", "zah": "ظ", "zain": "ز"
    },
    "arabic_numbers": {
        "0": "٠", "1": "١", "2": "٢", "3": "٣", "4": "٤", "5": "٥", "6": "٦", "7": "٧", "8": "٨", "9": "٩","hadhf":"حذف","masafa":"مسافة"
    },
    "english_letters": {
        "A": "A", "B": "B", "C": "C", "D": "D", "E": "E", "F": "F", "G": "G", "H": "H", "I": "I", "J": "J", "K": "K", "L": "L", "M": "M", 
        "N": "N", "O": "O", "P": "P", "Q": "Q", "R": "R", "S": "S", "T": "T", "U": "U", "V": "V", "W": "W", "X": "X", "Y": "Y", "Z": "Z","delete":"delete","space":"space"
    },
    "english_numbers": {
        "0": "0", "1": "1", "2": "2", "3": "3", "4": "4", "5": "5", "6": "6", "7": "7", "8": "8", "9": "9","delete":"delete","space":"space"
    }
}

# Make landmarks for hand
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

# The text
text_field = ""

# BaseModels
class LanguageRequest(BaseModel):
    language: str 
    mode: str

class PredictionRequest(BaseModel):    
    frame: str     

# 1- Set language 
@app.post("/set_language/")
async def set_language(request: LanguageRequest):
    global current_language, current_mode
    language = request.language.lower()
    mode = request.mode.lower()

    if language == "arabic":
        if mode == "letters":
            current_language = "arabic_letters"
        elif mode == "numbers":
            current_language = "arabic_numbers"
        else:
            raise HTTPException(status_code=400, detail="Invalid mode for Arabic")
    elif language == "english":
        if mode == "letters":
            current_language = "english_letters"
        elif mode == "numbers":
            current_language = "english_numbers"
        else:
            raise HTTPException(status_code=400, detail="Invalid mode for English")
    else:
        raise HTTPException(status_code=400, detail="Invalid language")

    current_mode = mode
    return {"message": f"Language set to {language} with {mode} mode"}

# Convert text to speech
def text_to_speech(text, lang):
    try:
        timestamp = int(time.time())
        output_file = os.path.join(AUDIO_FOLDER, f"output_{timestamp}.mp3")
        tts = gTTS(text=text, lang=lang)
        tts.save(output_file)
        
        # Upload the file to Firebase Storage
        unique_id = str(uuid.uuid4())
        destination_path = f"audio_files/{unique_id}.mp3"
        public_url = upload_to_firebase(output_file, destination_path)
        
        return public_url  # Return the public URL of the uploaded file
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error in text-to-speech: {str(e)}")

# 2- Text to speech
@app.get("/text_to_speech/")
async def speak_text(text: str = Query(..., description="The text to convert to speech"), 
                     language: str = Query(..., description="The language of the text (ar/en)")):
    if language not in ["ar", "en"]:
        raise HTTPException(status_code=400, detail="Invalid language. Use 'ar' for Arabic or 'en' for English.")
    
    lang = "ar" if language == "ar" else "en"
    
    audio_url = text_to_speech(text, lang)
    
    return {
        "message": "Text-to-speech is played",
        "text": text,
        "audio_url": audio_url  # Return the Firebase Storage URL
    }

# 3- Download audio
@app.get("/download_audio/")
async def download_audio(file_path: str = Query(..., description="Path to the audio file")):
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    return FileResponse(file_path, media_type="audio/mp3", filename=os.path.basename(file_path))

# 4- Predict
@app.post("/predict/")
async def predict(request: PredictionRequest):
    global text_field
    
    # Decode Base64 to numpy array
    frame_data = base64.b64decode(request.frame)
    nparr = np.frombuffer(frame_data, np.uint8)
    frame = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:
            landmarks = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]).reshape(1, 21, 3)
            prediction = models[current_language].predict(landmarks)
            label = categories[current_language][np.argmax(prediction)]
            mapped_label = mapping[current_language].get(label, label)

            if mapped_label == "مسافة" or mapped_label == "space":
                text_field += " "
            elif mapped_label == "حذف" or mapped_label == "delete":
                text_field = text_field[:-1]
            else:
                text_field += mapped_label

    return {"text": text_field}

# 5- Reset the text
@app.post("/reset_text/")
async def reset_text():
    global text_field
    text_field = ""  
    return {"message": "Text field has been reset"}
