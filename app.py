# File: app.py
# Backend Flask dengan logika konteks, sapaan dinamis, dan penghitung pengunjung.

import json
import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from fuzzywuzzy import process
from datetime import datetime

app = Flask(__name__)
CORS(app)

# --- LOKASI FILE PENGHITUNG ---
# Menentukan path absolut agar selalu benar di server PythonAnywhere
# __file__ adalah path ke file app.py saat ini, os.path.dirname mendapatkan direktorinya.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COUNTER_FILE = os.path.join(BASE_DIR, "visitor_count.txt")

# --- MEMUAT KNOWLEDGE BASE ---
def load_knowledge_base():
    """Memuat basis data pengetahuan dari file JSON."""
    knowledge_base_path = os.path.join(BASE_DIR, 'knowledge_base.json')
    try:
        with open(knowledge_base_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error memuat knowledge_base.json: {e}")
        return {}

knowledge_base = load_knowledge_base()

# --- MANAJEMEN KONTEKS ---
user_context = {"topic": None}

# --- FUNGSI SAPAAN DINAMIS ---
def get_dynamic_greeting():
    """Membuat sapaan berdasarkan waktu saat ini."""
    current_hour = datetime.now().hour
    if 5 <= current_hour < 12:
        return "Selamat Pagi!"
    elif 12 <= current_hour < 15:
        return "Selamat Siang!"
    elif 15 <= current_hour < 18:
        return "Selamat Sore!"
    else:
        return "Selamat Malam!"

# --- FUNGSI UTAMA LOGIKA BOT ---
def get_bot_response(user_input):
    """Mencari respons terbaik berdasarkan input pengguna."""
    text = user_input.lower().strip()
    
    # Prioritaskan pencarian berdasarkan konteks
    if user_context.get("topic"):
        for key, value in knowledge_base.items():
            if value.get("parent_context") == user_context["topic"]:
                match = process.extractOne(text, value.get('keywords', []))
                if match and match[1] > 85:
                    return value

    # Lakukan pencarian umum jika tidak ada kecocokan kontekstual
    highest_score = 0
    best_match_key = None
    for key, value in knowledge_base.items():
        match = process.extractOne(text, value.get('keywords', []))
        if match and match[1] > highest_score:
            highest_score = match[1]
            best_match_key = key

    # Jika kecocokan terbaik cukup tinggi, berikan jawaban
    if highest_score > 75:
        response_data = knowledge_base[best_match_key].copy()

        # Logika sapaan dinamis
        if best_match_key == 'greetings':
            greeting = get_dynamic_greeting()
            response_data['response'] = f"{greeting} {response_data['response']}"
        
        # Atur atau hapus konteks
        if "context_id" in response_data:
            user_context["topic"] = response_data["context_id"]
        elif "parent_context" not in response_data:
            user_context["topic"] = None
            
        return response_data

    # Jawaban default
    user_context["topic"] = None
    return {
        "response": "Maaf, saya belum mengerti. Coba ketik 'menu' untuk melihat pilihan utama.",
        "suggestions": ["Menu Utama"]
    }

# --- ENDPOINTS (RUTE API) ---

@app.route('/api/chat', methods=['POST'])
def chat():
    """Endpoint untuk percakapan utama."""
    data = request.get_json()
    user_message = data.get('message', '')
    bot_answer = get_bot_response(user_message)
    return jsonify(bot_answer)

@app.route('/api/feedback', methods=['POST'])
def feedback():
    """Endpoint untuk menerima masukan."""
    feedback_data = request.get_json()
    print(f"--- FEEDBACK DITERIMA ---\nData: {feedback_data}\n--------------------------")
    return jsonify({"status": "success"})

@app.route('/api/visit', methods=['POST'])
def track_visit():
    """Mencatat dan mengupdate jumlah pengunjung."""
    count = 0
    try:
        if os.path.exists(COUNTER_FILE):
            with open(COUNTER_FILE, 'r') as f:
                count = int(f.read())
    except (IOError, ValueError):
        count = 0
    
    count += 1
    
    try:
        with open(COUNTER_FILE, 'w') as f:
            f.write(str(count))
    except IOError as e:
        print(f"Gagal menulis ke file counter: {e}")
        return jsonify({"status": "error", "message": "Could not write to counter file."}), 500

    return jsonify({"status": "success", "visits": count})

if __name__ == '__main__':
    # Bagian ini hanya berjalan jika file dieksekusi secara lokal
    if not knowledge_base:
        print("Aplikasi tidak dapat dijalankan karena knowledge_base kosong atau gagal dimuat.")
    else:
        app.run(debug=True)
