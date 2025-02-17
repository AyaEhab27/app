import cv2
import numpy as np
import tensorflow as tf
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import mediapipe as mp
import os
from gtts import gTTS
from fastapi.middleware.cors import CORSMiddleware

# Start API
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)
# model paths
model_paths = {
    "arabic_letters": "app/models/Aalpha2_sign_language_model.h5",
    "arabic_numbers": "app/models/AN2_sign_language_model.h5",
    "english_letters": "app/models/E_alpha_sign_language_model.h5",
    "english_numbers": "app/models/EN_sign_language_model.h5"
}

#  load models
models = {}
for key, path in model_paths.items():
    models[key] = tf.keras.models.load_model(path)
    models[key].compile(optimizer="adam", loss="categorical_crossentropy", metrics=["accuracy"])

# categories
categories = {
    "arabic_letters": [ "ain", "al", "alef", "beh", "dad", "dal", "feh", "ghain", "hadhf", "hah", "heh", "jeem", "kaf", "khah", "laa", "lam", "masafa", "meem", "noon", "qaf", "reh", "sad", "seen", "sheen", "tah", "teh", "teh_marbuta", "thal", "theh", "waw", "yeh", "zah", "zain"],
    "arabic_numbers": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9","hadhf","masafa"],
    "english_letters": ["A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N", "O", "P", "Q", "R", "S", "T", "U", "V", "W", "X", "Y", "Z","delete","space"],
    "english_numbers": ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9","delete","space"]
}

# mapping
mapping = {
    "arabic_letters": {
        "ain": "ع", "al": "ال", "alef": "أ", "beh": "ب", "dad": "ض", "dal": "د", "feh": "ف", "ghain": "غ", "hadhf": "حذف", "hah": "ح", 
        "heh": "ه", "jeem": "ج", "kaf": "ك", "khah": "خ", "laa": "لا", "lam": "ل", "masafa": "مسافة", "meem": "م", "noon": "ن", "qaf": "ق", 
        "reh": "ر", "sad": "ص", "seen": "س", "sheen": "ش", "tah": "ط", "teh": "ت", "teh_marbuta": "ة", "thal": "ذ", "theh": "ث", "waw": "و", 
        "yeh": "ي", "zah": "ز", "zain": "ز"
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

# make landmarks for hand
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(min_detection_confidence=0.7)
mp_drawing = mp.solutions.drawing_utils

#  the text
text_field = ""

# BaseModel
class LanguageRequest(BaseModel):
    language: str 
    mode: str     

#  1- set language 
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

# convert text to speech
def text_to_speech(text):
    lang = 'ar' if current_language.startswith("arabic") else 'en'
    tts = gTTS(text=text, lang=lang)
    tts.save("output.mp3")
    os.system("start output.mp3")

# 2- predict
@app.post("/predict/")
async def predict(request: dict):
    global text_field
    frame = request['frame'] 

    frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    results = hands.process(frame_rgb)

    if results.multi_hand_landmarks:
        for hand_landmarks in results.multi_hand_landmarks:

            landmarks = np.array([[lm.x, lm.y, lm.z] for lm in hand_landmarks.landmark]).reshape(1, 21, 3)

            prediction = models[current_language].predict(landmarks)
            label = categories[current_language][np.argmax(prediction)]

            # change to labels in mapping
            mapped_label = mapping[current_language].get(label, label)

            if mapped_label == "مسافة":
                text_field += " "
            elif mapped_label == "حذف":
                text_field = text_field[:-1]
            elif mapped_label == "delete":
                text_field = text_field[:-1] 
            elif mapped_label == "space":
                 text_field += " "
            else:
                text_field += mapped_label

    return {"text": text_field}

# 3- text to speech
@app.get("/text_to_speech/")
async def speak_text():
    text_to_speech(text_field)
    return {"message": "Text-to-speech is played", "text": text_field}

