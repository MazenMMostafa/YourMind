from playsound import playsound
from pywebio.session import run_js, hold
import pygame
import random
from datetime import datetime
date = datetime.now()
import google.generativeai as genai
genai.configure(api_key=" AIzaSyAgWEjqvfNcS8ogkkbUMSw0E46LACGZZsE")
from pywebio.input import textarea, input, actions
from pywebio.output import put_markdown, put_button, toast, put_processbar
from pywebio.pin import pin
from datetime import datetime, timedelta
import os
import jwt
import re
import logging
import random
import queue
import threading
import pyrebase
from pywebio import start_server
from pywebio.input import input, input_group, actions, PASSWORD, TEXT, NUMBER, select, radio, checkbox
from pywebio.output import (
    put_text, put_buttons, put_markdown, popup, put_table, 
    put_row, put_column, clear, use_scope, put_html, 
    put_button, clear_scope, toast, put_processbar, 
    put_grid,put_image
)
from pywebio.session import run_js, set_env, local as session_storage, hold
from pywebio.pin import pin, pin_wait_change, put_textarea, put_select, put_input
from contextlib import contextmanager
from functools import wraps
import time
import sys

from questions import beck_questions, all_questions
from firebase_config import FIREBASE_CONFIG  
from pywebio.platform.flask import webio_view
from pywebio import STATIC_PATH
from flask import Flask, send_from_directory
from pywebio.output import *
from pywebio.input import *
from pywebio.session import *
from database_manager import DatabaseConnectionManager, DatabaseManager
import speech_recognition as sr
import sounddevice as sd
import soundfile as sf
import numpy as np


logging.basicConfig(
    filename='app.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


try:
    firebase = pyrebase.initialize_app(FIREBASE_CONFIG)
    db = firebase.database()  
    auth = firebase.auth()  
    logging.info("Firebase initialized successfully")
except Exception as e:
    logging.error(f"Failed to initialize Firebase: {str(e)}")
    print("Error: Failed to connect to Firebase database")
    sys.exit(1)


MAX_RECORD_TIME = 300  
MAX_RECORD_COUNT = 20 
SAVE_PATH = "recordings"  
SESSION_TIMEOUT = 30  
JWT_SECRET = "5f2b6e8c3a9d1e7f8a2c4b6d9e1f3a5b7c6d8e0f4a1b3c5d7e9f2a4c6b8d0e1"



for directory in [SAVE_PATH, "recordings", "logs"]:
    os.makedirs(directory, exist_ok=True)


current_user = None
current_user_role = None
total_score = 0
answers_history = []
page_history = []
q = queue.Queue()
recording = False
record_start_time = None
current_question = None
record_count = 1
audio_data = None

db_connection_manager = DatabaseConnectionManager()
db_manager = DatabaseManager(db)

def logout():
    """تسجيل الخروج."""
    try:
        
        if hasattr(session_storage, 'user'):
            delattr(session_storage, 'user')
        if hasattr(session_storage, 'role'):
            delattr(session_storage, 'role')
            
       
        popup("تم", "تم تسجيل الخروج بنجاح")
        
        
        show_login_screen()
        
    except Exception as e:
        print(f"Logout error: {str(e)}")
        popup("خطأ", "حدث خطأ في تسجيل الخروج")
        show_login_screen()
        
def add_global_style():
    """إضافة التنسيقات العامة للتطبيق."""
    put_html("""
        <style>
            :root {
                --color-1: #4B7A28;    /* الأخضر الداكن */
                --color-2: #7A9B41;    /* الأخضر المتوسط */
                --color-3: #A5C667;    /* الأخضر الفاتح */
                --color-4: #E8F3D6;    /* الأخضر الفاتح جداً */
            }

            body {
                font-family: 'Tajawal', Arial, sans-serif;
                direction: rtl;
                background-color: var(--color-4);
                padding: 20px;
                margin: 0;
            }

            /* الأزرار */
            button, .webio-button {
                background: linear-gradient(145deg, var(--color-2), var(--color-1));
                color: white;
                border: none;
                border-radius: 12px;
                padding: 12px 25px;
                margin: 8px 0;
                cursor: pointer;
                font-size: 16px;
                transition: 0.3s ease;
                width: 100%;
                text-align: center;
                box-shadow: 0 4px 10px rgba(75, 122, 40, 0.15);
            }

            button:hover, .webio-button:hover {
                background: linear-gradient(145deg, var(--color-1), var(--color-2));
                transform: translateY(-3px);
                box-shadow: 0 6px 15px rgba(75, 122, 40, 0.25);
            }

            /* العناوين */
            h1, h2, h3, h4, h5, h6 {
                color: var(--color-1);
                text-align: center;
                margin: 25px 0;
            }

            h1 {
                font-size: 2.5em;
                text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
            }

            /* شريط التقدم */
            .progress {
                background-color: white;
                height: 20px;
                margin: 15px 0;
                border-radius: 10px;
                box-shadow: inset 0 1px 3px rgba(0,0,0,0.1);
            }

            .progress-bar {
                background: linear-gradient(90deg, var(--color-2), var(--color-1));
                border-radius: 10px;
                transition: width 0.4s ease-in-out;
            }

            /* الإطارات */
            .box, .card {
                background: white;
                padding: 20px;
                border-radius: 15px;
                margin: 15px 0;
                box-shadow: 0 6px 20px rgba(75, 122, 40, 0.1);
                border: 1.5px solid var(--color-3);
                transition: transform 0.3s ease;
            }

            .box:hover, .card:hover {
                transform: translateY(-5px);
                box-shadow: 0 10px 25px rgba(75, 122, 40, 0.15);
            }

            /* الجداول */
            table {
                width: 100%;
                border-collapse: collapse;
                margin: 15px 0;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 4px 10px rgba(75, 122, 40, 0.1);
            }

            th, td {
                padding: 12px;
                text-align: center;
            }

            th {
                background: linear-gradient(145deg, var(--color-2), var(--color-1));
                color: white;
            }

            td {
                background-color: white;
                border-bottom: 1px solid var(--color-3);
            }

            tr:last-child td {
                border-bottom: none;
            }

            /* النماذج */
            input, select, textarea {
                width: 100%;
                padding: 10px;
                margin: 8px 0;
                border: 1.5px solid var(--color-3);
                border-radius: 8px;
                transition: 0.3s ease;
                background-color: white;
            }

            input:focus, select:focus, textarea:focus {
                outline: none;
                border-color: var(--color-2);
                box-shadow: 0 0 5px rgba(122, 155, 65, 0.3);
            }

            /* الرسائل */
            .toast {
                background: white;
                color: var(--color-1);
                padding: 15px;
                border-radius: 10px;
                margin: 12px 0;
                text-align: center;
                border-right: 4px solid var(--color-2);
                box-shadow: 0 4px 10px rgba(75, 122, 40, 0.1);
            }

            /* الروابط */
            a {
                color: var(--color-2);
                text-decoration: none;
                transition: 0.3s ease;
                border-bottom: 2px solid transparent;
            }

            a:hover {
                color: var(--color-1);
                border-bottom: 2px solid var(--color-1);
            }

            /* القوائم */
            ul, ol {
                background: white;
                padding: 15px 30px;
                border-radius: 12px;
                box-shadow: 0 4px 10px rgba(75, 122, 40, 0.1);
            }

            li {
                margin: 8px 0;
                color: var(--color-1);
            }

            /* تأثيرات إضافية */
            .highlight {
                background: linear-gradient(120deg, var(--color-4) 0%, var(--color-3) 100%);
                padding: 15px;
                border-radius: 12px;
                margin: 15px 0;
            }
        </style>
    """)
def add_back_emotion():
    add_global_style()
    put_row([
         put_button("العوده لصفحه المشاعر", onclick=show_emotions_menu)

    ])
   

def add_to_history(page_function):
    """Add the current page to history."""
    global page_history
    page_history.append(page_function)


def add_back_button():
    """إضافة زر العودة حسب نوع المستخدم."""
    add_global_style()
    try:
        if not hasattr(session_storage, 'user'):
            return put_button('رجوع', onclick=show_main_screen)
            
        
        user_data = db.child("users").get()
        if user_data:
            for user in user_data.each():
                if user.val().get('username') == session_storage.user:
                    role = user.val().get('role')
                    if role == 'doctor':
                        
                        return put_button('رجوع', onclick=show_doctor_screen)
                    elif role == 'patient':
                        return put_button('رجوع', onclick=show_patient_screen)
                    elif role == 'admin':
                        return put_button('رجوع', onclick=show_admin_screen)
        
       
        return put_button('رجوع', onclick=show_main_screen)
        
    except Exception as e:
        print(f"Error adding back button: {str(e)}")
        return put_button('رجوع', onclick=show_main_screen)

total_score = 0
answers_history = []

def start_beck_assessment():
    """Start Beck Depression Assessment."""
    clear()
    add_global_style()
   
    add_back_button()
    put_markdown("# تقييم بيك للاكتئاب")
    put_markdown(" هذا الإختبار مبني على إختبار بيك للاكتئاب هو أداة معتمدة في تقييم شدة الاكتئاب لدى الأفراد، تم تطويره عام 1961")
    put_markdown("لمزيد من التفاصيل:")
    put_button("اضغط هنا",onclick=lambda: put_markdown("https://academic.oup.com/occmed/article-abstract/66/2/174/2750566?redirectedFrom=fulltext&login=false "))
    if actions("هل تريد البدء في التقييم؟", ["نعم", "العودة"]) == "نعم":
        
        global total_score, answers_history
        total_score = 0
        answers_history = []
        show_beck_question(0, beck_questions)
    else:
        show_patient_screen()

class AssessmentState:
    def __init__(self):
        self.total_score = 0
        self.answers_history = []


assessment_state = AssessmentState()


def play():
    pygame.mixer.init()
    pygame.mixer.music.load("D:/my website your mind/audio.mp3")
    pygame.mixer.music.play()

def stop():
    pygame.mixer.music.stop()

def show_breathing_exercise():
    clear()
    add_global_style()
    add_back_button()
    put_markdown("تمارين تنفس 478 للتهدئة")
    put_markdown("1)اتنفس لمدة 4 ثواني")
    put_markdown("2)اكتم نفسك لمده 7 ثواني")
    put_markdown("3)طلع زفير لمده 8 ثواني")
    
    put_row([
        put_button('استمع لتمارين التنفس', onclick=play),
        put_button('ايقاف التمارين', onclick=stop)  
    ])
def show_beck_question(index, questions):
    """Display Beck assessment questions."""
    add_to_history(lambda: show_beck_question(index, questions))
    
    clear()
    add_global_style()
    add_back_button()
    
    if index < len(questions):
        
        progress = ((index + 1) / len(questions)) * 1
        put_processbar('progress', progress)
        put_text(f"السؤال {index + 1} من {len(questions)}")
        
      
        put_html(f"""
            <div style="background-color: #F0FFF0; padding: 20px; border-radius: 10px; margin: 20px 0;">
                <h3 style="color: #006400;">{questions[index]['question']}</h3>
            </div>
        """)
        add_global_style()
        
        def on_answer_click(score, answer_text):
            add_global_style()
            try:
                username = session_storage.user
                
                
                db.child("medical_history").child(username).child("psychological_assessment").push({
                    "question": questions[index]['question'],
                    "answer": answer_text,
                    "score": score,
                    "timestamp": datetime.now().isoformat()
                })
                
                
                assessment_state.total_score += score
                assessment_state.answers_history.append({
                    'question': questions[index]['question'],
                    'answer': answer_text,
                    'score': score
                })
                
               
                time.sleep(0.5)
                if index + 1 < len(questions):
                    show_beck_question(index + 1, questions)
                else:
                    show_beck_results()
                
            except Exception as e:
                toast(f"حدث خطأ: {str(e)}")
        
       
        put_html("""
            <div style="background-color: white; padding: 15px; border-radius: 10px; margin: 20px 0;">
                <h4 style="color: #006400;">اختر إجابتك:</h4>
            </div>
        """)
        
        
        for answer in questions[index]['answers']:
            put_button(
                label=answer['text'],
                onclick=lambda s=answer['score'], t=answer['text']: on_answer_click(s, t),
                color='success'
            )
        
       
        if index > 0:
            put_button(
                label=' السؤال السابق',
                onclick=lambda: show_beck_question(index - 1, questions),
                color='success'
            )
    else:
        show_beck_results()
def interpret_beck_score(score):
    """تفسير نتيجة اختبار بيك."""
    if score <= 10:
        return {
            'level': 'طبيعي',
            'color': '#4CAF50',
            'message': 'انت كوويس ممكن مودك بس مش احسن حاجة حاول ترفهه عن نفسك'
        }
    elif score <= 16:
        return {
            'level': 'اكتئاب بسيط',
            'color': '#FFC107',
            'message': 'اطمن انت بس ممكن تحتاج تتابع مع دكتور'
        }
    elif score <= 23:
        return {
            'level': 'اكتئاب متوسط',
            'color': '#FF9800',
            'message': 'لازم تراجع مع دكتور'
        }
    else:
        return {
            'level': 'اكتئاب شديد',
            'color': '#F44336',
            'message': 'يجب عليك مراجعة الطبيب فوراً'
        }
def handle_result_action(action):
    """التعامل مع إجراءات نتائج التقييم."""
    if action == 'print':
        
        toast("جاري تحضير النتائج للطباعة...")
        
        
    elif action == 'retry':
       
        clear()
        start_beck_assessment()
        
    elif action == 'home':
       
        clear()
        show_patient_screen()

def show_beck_results():
    """عرض نتائج تقييم بيك."""
    clear()
    add_global_style()
    
    try:
       
        if not hasattr(assessment_state, 'total_score') or not hasattr(session_storage, 'user'):
            toast("بيانات التقييم غير مكتملة")
            return show_patient_screen()

        total_score = assessment_state.total_score
        username = session_storage.user
        timestamp = datetime.now().isoformat()
        
       
        result = interpret_beck_score(total_score)
        
        
        assessment_data = {
            'score': total_score,
            'level': result['level'],
            'message': result['message'],
            'answers': assessment_state.answers_history,
            'date': timestamp
        }
        
        try:
            db.child("assessments").child(username).push(assessment_data)
        except Exception as e:
            print(f"Database error: {str(e)}")

        
        put_html(f"""
            <div class="card" style="text-align: center;">
                <h2>نتيجة تقييم بيك للاكتئاب</h2>
                <div style="display: flex; justify-content: center; gap: 20px; margin: 30px 0;">
                </div>
                <div class="highlight" style="margin: 20px 0;">
                    <h3>التوصية</h3>
                    <p style="font-size: 1.2em;">{result['message']}</p>
                </div>
            </div>
        """)

        
        if assessment_state.answers_history:
            put_html("""
                <div class="card" style="margin-top: 20px;">
                    <h3>تفاصيل التقييم</h3>
                    <div style="overflow-x: auto;">
                        <table style="width: 100%;">
                            <thead>
                                <tr>
                                    <th>السؤال</th>
                                    <th>إجابتك</th>
                                </tr>
                            </thead>
                            <tbody>
            """)

            for answer in assessment_state.answers_history:
                put_html(f"""
                    <tr>
                        <td>{answer.get('question', '')}</td>
                        <td>{answer.get('answer', '')}</td>
                    </tr>
                """)

            put_html("""
                        </tbody>
                    </table>
                </div>
            </div>
            """)

        
        put_buttons([
            {'label': '📋 طباعة النتائج', 'value': 'print', 'color': 'info'},
            {'label': '🔄 إعادة التقييم', 'value': 'retry', 'color': 'warning'},
            {'label': '🏠 الصفحة الرئيسية', 'value': 'home', 'color': 'success'}
        ], onclick=handle_result_action)

       
        put_html("""
            <div class="card" style="margin-top: 20px;">
                <h3>نصائح ومصادر مفيدة</h3>
                <ul>
                    <li>حافظ على نمط حياة صحي ومنتظم</li>
                    <li>مارس الرياضة بانتظام</li>
                    <li>تحدث مع أشخاص تثق بهم عن مشاعرك</li>
                    <li>لا تتردد في طلب المساعدة المهنية عند الحاجة</li>
                </ul>
            </div>
        """)

    except Exception as e:
        print(f"Error showing results: {str(e)}")
        toast("حدث خطأ في عرض النتائج")
        show_patient_screen()
def show_assessment_details():
    """عرض تفاصيل نتائج التقييم."""
    try:
        popup(
            title="تفاصيل التقييم",
            content=[
                put_html("""
                    <div style="background-color: #F0FFF0; padding: 15px; border-radius: 10px;">
                        <table style="width: 100%; border-collapse: collapse;">
                            <tr style="background-color: #90EE90;">
                                <th style="padding: 10px; border: 1px solid #006400;">السؤال</th>
                                <th style="padding: 10px; border: 1px solid #006400;">الإجابة</th>
                            </tr>
                """),
                *[
                    put_html(f"""
                        <tr style="background-color: white;">
                            <td style="padding: 10px; border: 1px solid #006400;">{answer['question']}</td>
                            <td style="padding: 10px; border: 1px solid #006400;">{answer['answer']}</td>
                        </tr>
                    """) 
                    for answer in assessment_state.answers_history
                ],
                put_html("</table></div>")
            ]
        )
    except Exception as e:
        print(f"Error in show_assessment_details: {str(e)}")
        toast("حدث خطأ في عرض التفاصيل")

def save_answer(index, answer, score):
    """Save the answer and score for the current question."""
    global answers_history
    answers_history.append({'question_index': index, 'answer': answer, 'score': score})
app = Flask(__name__)

# 🔹 إعداد مجلد التخزين للتسجيلات الصوتية
UPLOAD_FOLDER = "recordings"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)



def get_response(user_text):
    """🔹 الحصول على رد من Gemini بطريقة محسنة"""
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = f"""
        أجب بإجابة قصيرة نوعًا ما باللغة العامية المصرية، بأسلوب محترم وإيجابي.
        تجنب أي محتوى غير لائق أو عدائي. إذا كان الشخص يعبر عن مشاعر حزينة أو خطرة،
        فقدم ردًا داعمًا واطلب منه اللجوء إلى طبيب إذا لزم الأمر.
        السؤال: {user_text}
        """
        response = model.generate_content([prompt])

        if hasattr(response, 'text') and response.text:
            return response.text.strip()
        else:
            return "أنا هنا لأستمع إليك وأساعدك بطريقة محترمة وداعمة 😊."
    
    except Exception as e:
        logging.error(f"❌ خطأ في الحصول على الرد من Gemini: {e}")
        return "⚠️ حدث خطأ أثناء المعالجة، حاول مرة أخرى لاحقًا."

@app.route("/upload_audio", methods=["POST"])
def upload_audio():
    """🔹 استقبال الملف الصوتي وتحويله إلى نص ثم تحليل الذكاء الاصطناعي"""
    if "audio" not in request.files:
        return jsonify({"error": "لم يتم استقبال أي ملف"}), 400

    audio_file = request.files["audio"]
    file_path = os.path.join(UPLOAD_FOLDER, "uploaded_audio.wav")
    audio_file.save(file_path)

    recognizer = sr.Recognizer()
    with sr.AudioFile(file_path) as source:
        audio_data = recognizer.record(source)
        try:
            text = recognizer.recognize_google(audio_data, language="ar-EG")
            ai_response = get_response(text)
            return jsonify({"text": text, "ai_response": ai_response})
        except sr.UnknownValueError:
            return jsonify({"text": "تعذر فهم الصوت", "ai_response": "❌ لم يتمكن الذكاء الاصطناعي من الرد."})
        except Exception as e:
            return jsonify({"error": str(e), "ai_response": "⚠️ حدث خطأ أثناء تحليل الرد."}), 500

def show_question(index, questions, emotion_type):
    """🔹 عرض الأسئلة، تشغيل الصوت، تسجيل الصوت، وتحليل الذكاء الاصطناعي"""
    clear()

    put_markdown(f"## السؤال {index + 1} من {len(questions)}")
    put_markdown(f"**{questions[index]}**")

    progress = ((index + 1) / len(questions))
    put_processbar('progress', progress)



    # ✅ تضمين JavaScript لتسجيل الصوت وتحليله وعرض الرد
    put_html("""
        <button id="startRecord">🎙️ بدء التسجيل</button>
        <button id="stopRecord" disabled>⏹️ إيقاف التسجيل</button>

        <p id="userText" style="font-weight:bold; color:#008080;"></p>
        <p id="aiResponse" style="font-weight:bold; color:#800080;"></p>

        <script>
            let mediaRecorder;
            let audioChunks = [];

            document.getElementById("startRecord").addEventListener("click", async () => {
                let stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                mediaRecorder = new MediaRecorder(stream);
                audioChunks = [];

                mediaRecorder.ondataavailable = (event) => {
                    audioChunks.push(event.data);
                };

                mediaRecorder.onstop = async () => {
                    let audioBlob = new Blob(audioChunks, { type: "audio/wav" });

                    // حفظ الصوت في متغير ليتم رفعه لاحقًا
                    document.getElementById("uploadAudio").audioBlob = audioBlob;
                    document.getElementById("uploadAudio").disabled = false;
                };

                mediaRecorder.start();
                document.getElementById("startRecord").disabled = true;
                document.getElementById("stopRecord").disabled = false;
            });

            document.getElementById("stopRecord").addEventListener("click", () => {
                mediaRecorder.stop();
                document.getElementById("startRecord").disabled = false;
                document.getElementById("stopRecord").disabled = true;
            });

            document.getElementById("uploadAudio").addEventListener("click", async () => {
                let formData = new FormData();
                formData.append("audio", document.getElementById("uploadAudio").audioBlob, "recording.wav");

                // ✅ تحديث الواجهة أثناء التحليل
                document.getElementById("userText").innerText = "⏳ جارٍ تحليل الصوت...";
                document.getElementById("aiResponse").innerText = "";

                let response = await fetch("/upload_audio", { method: "POST", body: formData });
                let result = await response.json();

                document.getElementById("userText").innerText = "📢 النص المستخرج: " + result.text;
                document.getElementById("aiResponse").innerText = "🤖 رد الذكاء الاصطناعي: " + result.ai_response;
            });
        </script>
    """)

    put_button("➡️ التالي", onclick=lambda: show_question(index + 1, questions, emotion_type))
    if index > 0:
        put_button("السابق", onclick=lambda: show_question(index - 1, questions, emotion_type))

def handle_next_question(question_index, questions):
    """Handle navigation to next question."""
    if question_index + 1 < len(questions):
        show_question(question_index + 1, questions)
    else:
        show_beck_results()

def show_emotions_menu():
    """Show emotions assessment menu."""
    
    clear()
    add_global_style()
    add_back_button()
     
    put_markdown("# تقييم المشاعر")
    put_row([
        put_button("الحزن", onclick=show_sadness_screen),
        put_button("الغضب", onclick=show_anger_screen),
        put_button("التوتر", onclick=show_stress_screen),
    ])
    put_row([
    
    put_button("تحليل الأفكار السلبية", onclick=negative_thoughts),
    put_button("الشعور بالذنب",onclick=show_guilt_screen),
    put_button("انعدام المشاعر", onclick=show_random_video),

    ])
    put_button("تحديات السعادة", onclick=show_happiness_challenges),

import random

def show_random_video():
    clear()
    add_global_style()
    add_back_emotion()
    put_markdown("# فيديو")
    
   
    video_url = [
     "https://www.youtube.com/embed/adf4yi5CECA",
     "https://www.youtube.com/embed/-pZLZyqWeBQ",
     "https://www.youtube.com/embed/XXsGMclkC9U",
     "https://www.youtube.com/embed/zGNXpaj_s9A",
     "https://www.youtube.com/embed/XnONWoasr7k",
     "https://www.youtube.com/embed/TdKMnzJKFi8",


    ]
    
   
    random_video = random.choice(video_url)
    
  
    
    put_html(f"""
    <style>
    .center {{
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
        text-align: center;
    }}
    </style>
    <div class="center">
        <iframe width="560" height="315" src="{random_video}" frameborder="0" 
        allow="accelerometer; autoplay; encrypted-media; gyroscope; picture-in-picture" 
        allowfullscreen></iframe>
    </div>
""")

    put_button("مشاهدة فيديو اخر",onclick=show_random_video)


    questions = ["حاسس بايه بعد الفيديو؟"]
    show_respond(0, questions)

def show_respond(index, questions):
    """عرض الأسئلة وجمع إجابات المريض وتحليلها وتخزينها في السجل الطبي"""
    put_markdown(f"**{questions[index]}**")
    put_textarea("text", rows=5, placeholder="أكتب إجابتك هنا")

    put_button("إرسال", onclick=lambda: say_response(index, questions))

def say_response(index, questions):
    """معالجة استجابة المستخدم وإرسالها إلى Gemini"""
    user_emotion = pin['text']  

    if not user_emotion.strip():
        toast("❌ يرجى كتابة إجابة أولاً!")
        return


    try:
        ai_response = get_response_for_emotionless(user_emotion) 
        put_markdown("### رد النظام:")
        put_markdown(f"💡 {ai_response}")

        username = session_storage.user
        db.child("medical_history").child(username).child("emotionless").push({
            "question": questions[index],
            "answer": user_emotion,
            "system_response": ai_response,
            "timestamp": datetime.now().isoformat(),
        })
        print("✅ تم تسجيل الرد في Firebase بنجاح!")

    except Exception as e:
        print(f"❌ خطأ أثناء حفظ الرد في Firebase: {e}")
        toast("حدث خطأ أثناء تسجيل الإجابة، حاول مرة أخرى.")
   
def get_response_for_emotionless(user_emotion):
   
    """الحصول على رد من Gemini مع تحسين التوجيهات لتجنب الحظر"""
    try:
        model = genai.GenerativeModel("gemini-pro")
        replay = f"""
         جاوب عليه كانك صديق باجابه قصيرة بالعامية عباره عن نصيحة:  {user_emotion}
        """
        respond = model.generate_content(replay)

        if respond and hasattr(respond, 'text') and respond.text:
            print(f"🔹 رد Gemini: {respond.text}")
            return respond.text
        else:
            print("❌ خطأ: لم يتم توليد رد من Gemini!")
            return "أنا هنا لأستمع إليك وأساعدك بطريقة محترمة وداعمة 😊."
    
    except Exception as e:
        print(f"❌ خطأ في الحصول على الرد من Gemini: {e}")
        return "حدث خطأ أثناء المعالجة، حاول مرة أخرى لاحقًا."

    
    
def show_guilt_screen():
    """عرض شاشة تقييم الذنب."""
    clear()
    add_global_style()
    add_back_emotion()
    put_markdown("# تقييم الذنب")
    put_markdown("هناك العديد من الأسباب التي قد تجعلك تشعر بالذنب. يمكنك تحليل هذه الأسباب والتعامل معها بشكل صحيح.")
    put_markdown("### الخطوات:")
    put_markdown("1. **تحديد الأسباب:** قول الأسباب التي بتخليك تحس بالذنب.")
    questions = ["قولي حاسس بالذنب ليه"]
    show_guilt_question(0, questions, "guilt")


def get_response_for_guilt(user_text):
    """الحصول على رد من Gemini مع تحسين التوجيهات لتجنب الحظر"""
    try:
        model = genai.GenerativeModel("gemini-pro")
        prompt = f"""
         اظهر الاجابه بالعامية عن طريق  حلل كلامه وشوف عنده احساس بالذنب طبيعي ولا مرضي وحاول تخفف عنه بنصايح التخلص من الذنب المرضي لو عنده بس متقولش ان ده ذنب مرضي  واظهر الاجابه فقط كانك بتكلمه ومتكتبش اي حاجه من الي انا قولتهالك: {user_text}
        """
        response = model.generate_content(prompt)

        if response and hasattr(response, 'text') and response.text:
            print(f"🔹 رد Gemini: {response.text}")
            return response.text
        else:
            print("❌ خطأ: لم يتم توليد رد من Gemini!")
            return "أنا هنا لأستمع إليك وأساعدك بطريقة محترمة وداعمة 😊."
    
    except Exception as e:
        print(f"❌ خطأ في الحصول على الرد من Gemini: {e}")
        return "حدث خطأ أثناء المعالجة، حاول مرة أخرى لاحقًا."



def show_guilt_question(index,questions, emotion_type):
    """عرض الأسئلة وجمع إجابات المريض بالصوت وتحليلها بالقاموس وتخزينها في السجل الطبي"""
    clear()
    add_global_style()
    
    add_back_emotion()
    put_markdown(f"**{questions[index]}**")

    def start_recording():
        """🔹 بدء التسجيل"""
        global recording, record_start_time, audio_data
        recording = True
        record_start_time = time.time()
        toast("🎤 جاري التسجيل...")
        audio_data = sd.rec(int(10 * 44100), samplerate=44100, channels=1)
        sd.wait()

    def stop_recording():
        """🔹 إيقاف التسجيل وتحليل الصوت وإضافته إلى السجل الطبي"""
        global recording, record_start_time, record_count, audio_data
        if recording:
            recording = False
            duration = time.time() - record_start_time
            if duration > 1:
               
                if not hasattr(session_storage, 'user'):
                    popup('خطأ', 'الرجاء تسجيل الدخول أولاً')
                    return show_main_screen()
                    
                username = session_storage.user  
                
                filename = f"{username}_{emotion_type}_q{index}_{record_count}.wav"
                filepath = os.path.join(SAVE_PATH, filename)
                
                
                sf.write(filepath, audio_data, 44100)
                
                try:
                    r = sr.Recognizer()
                    with sr.AudioFile(filepath) as source:
                        audio = r.record(source)
                        text = r.recognize_google(audio, language='ar-AR')
                        
                    put_markdown("### إجابتك:")
                    put_markdown(f"💬 {text}")

                  
                    ai_response = get_response_for_guilt(text)
                    put_markdown("### رد النظام:")
                    put_markdown(f"💡 {ai_response}")

                    
                    try:
                        db.child("medical_history").child(username).child(emotion_type).push({
                                    "question": questions[index],
                                    "answer": text,
                                    "system_response": ai_response,
                                    "timestamp": datetime.now().isoformat(),
                                    "audio_file": filepath
                           
                        })
                        print("✅ تم تسجيل الرد في Firebase بنجاح!")
                    except Exception as e:
                        print(f"❌ خطأ أثناء حفظ الرد في Firebase: {e}")

                except sr.UnknownValueError:
                    toast("❌ لم نتمكن من فهم التسجيل، حاول مرة أخرى.")
                except Exception as e:
                    toast(f"⚠️ حدث خطأ أثناء المعالجة: {str(e)}")

    put_button("🎙️ بدء التسجيل", onclick=start_recording, color='success')
    put_button("⏹️ إيقاف التسجيل", onclick=stop_recording, color='danger')





    
def get_response_for_negative(user_negative):
   
    """الحصول على رد من Gemini مع تحسين التوجيهات لتجنب الحظر"""
    try:
        model = genai.GenerativeModel("gemini-pro")
        replay = f"""
         اجب على كل فكره لوحدها منفصلة بس جاوب عليهم كلهم كصديق بس باحترام اجب بالعامية المصرية بفكرة ايجابية تناقض الفكره السلبية المرسلة:  {user_negative}
        """
        respond = model.generate_content(replay)

        if respond and hasattr(respond, 'text') and respond.text:
            print(f"🔹 رد Gemini: {respond.text}")
            return respond.text
        else:
            print("❌ خطأ: لم يتم توليد رد من Gemini!")
            return "أنا هنا لأستمع إليك وأساعدك بطريقة محترمة وداعمة 😊."
    
    except Exception as e:
        print(f"❌ خطأ في الحصول على الرد من Gemini: {e}")
        return "حدث خطأ أثناء المعالجة، حاول مرة أخرى لاحقًا."



def negative_thoughts():
    """عرض تحليل الأفكار السلبية."""
   
    clear()
    add_global_style()
    add_back_emotion()
    put_markdown("# تحليل الأفكار السلبية")
    put_markdown("هناك العديد من الأفكار السلبية التي يمكن أن تؤثر على مزاجك وصحتك العقلية. يمكنك تحليل هذه الأفكار وتغييرها بأفكار إيجابية.")
    put_markdown("### الخطوات:")
    put_markdown("1. **تحديد الأفكار السلبية:** اكتب الأفكار السلبية التي تدور في ذهنك.")
    put_markdown("2. **تحليل الأفكار:** قم بتحليل الأفكار السلبية والبحث عن الأدلة التي تؤكد أو تنفي صحتها.")
    put_markdown("3. **تغيير الأفكار:** قم بتغيير الأفكار السلبية إلى أفكار إيجابية ومحفزة.")

    questions = ["ما هي الأفكار السلبية التي تدور في ذهنك؟"]
    show_positive(0, questions)

def show_positive(index, questions):
    """عرض الأسئلة وجمع إجابات المريض وتحليلها وتخزينها في السجل الطبي"""
    progress = (index + 1) / len(questions)
    put_processbar('progress', progress)
    put_markdown(f"## السؤال {index + 1} من {len(questions)}")
    put_markdown(f"**{questions[index]}**")
    put_textarea("text", rows=5, placeholder="أكتب إجابتك هنا")

    put_button("إرسال", onclick=lambda: process_response(index, questions))

def process_response(index, questions):
    """معالجة استجابة المستخدم وإرسالها إلى Gemini"""
    user_negative = pin['text']  

    if not user_negative.strip():
        toast("❌ يرجى كتابة إجابة أولاً!")
        return


    try:
        ai_response = get_response_for_negative(user_negative) 
        put_markdown("### رد النظام:")
        put_markdown(f"💡 {ai_response}")

        username = session_storage.user
        db.child("medical_history").child(username).child("negative_thoughts").push({
            "question": questions[index],
            "answer": user_negative,
            "system_response": ai_response,
            "timestamp": datetime.now().isoformat(),
        })
        print("✅ تم تسجيل الرد في Firebase بنجاح!")

    except Exception as e:
        print(f"❌ خطأ أثناء حفظ الرد في Firebase: {e}")
        toast("حدث خطأ أثناء تسجيل الإجابة، حاول مرة أخرى.")

    
    

def show_sadness_screen():
    add_global_style()
    
    """Show sadness assessment questions with AI-generated responses."""
    questions = [
        "إيه أكتر حاجة موجعاك اليومين دول؟",
        "حسيت إمتى آخر مرة إن الدنيا تقفلت عليك؟ إيه اللي حصل وقتها؟",
        "لما بتكون زعلان، بتحب تحكي لحد ولا تفضل تسكت؟",
        "إيه الحاجة اللي نفسك تغيرها في حياتك دلوقتي؟",
        "إيه أكتر حاجة بتخليك تحس بالراحة لما تكون زعلان؟"
    ]
    show_question(0, questions, "sadness")


def show_anger_screen():
    add_global_style()
    """Show anger assessment questions with AI-generated responses."""
    questions = [
        "ما هو أكثر شيء يثير غضبك؟",
        "كيف تتصرف عندما تغضب؟",
        "هل تندم على تصرفاتك وقت الغضب؟",
        "كم من الوقت تحتاج للتهدئة بعد الغضب؟",
        "هل يؤثر غضبك على علاقاتك مع الآخرين؟"
    ]
    show_question(0, questions, "anger")


def show_stress_screen():
    add_global_style()
    
    """Show stress assessment questions with AI-generated responses."""
    questions = [
        "ما هي مصادر التوتر في حياتك؟",
        "كيف يؤثر التوتر على نومك؟",
        "هل تعاني من أعراض جسدية بسبب التوتر؟",
        "ما هي طريقتك في التخلص من التوتر؟",
        "هل تمارس تمارين الاسترخاء؟"
    ]
    show_question(0, questions, "stress")

def show_articles():
    """Display mental health articles."""
    clear()
    add_global_style()
    add_back_button()
    put_button("مقالات مكتوبة",onclick=show_read_Articles)
    with open(r"D:\my website your mind\IMAGE REA.jpg", "rb") as img_file:
        put_image(img_file.read())
    put_button("مقالات صوتية",onclick=show_audio_articles)
    with open(r"D:\my website your mind\IMAGE LES.jpg", "rb") as img_file:
        put_image(img_file.read())

    

def show_audio_articles():
    clear()
    add_global_style()
    add_back_button()
    audio_files = [
    "D:/my website your mind/audio2.mp3",
    "D:/my website your mind/audio1.mp3",
]

    random_audio = random.choice(audio_files)

    put_button("استمع للمقالة",lambda: play_art(random_audio))
    with open(r"D:\my website your mind\IMAGE LES.jpg", "rb") as img_file:
        put_image(img_file.read())
    
    put_button('وقف المقالة', onclick=stop_art)  
    
    put_button("سماع مقالة اخرى",onclick=show_audio_articles)
    
def play_art(random_audio):
    pygame.mixer.init()
    pygame.mixer.music.load(random_audio)
    pygame.mixer.music.play()

def stop_art():
    pygame.mixer.music.stop()
    

    
def show_read_Articles():   
    clear()
    add_global_style()
    add_back_button()
    articles = [
        {"title":"السعادة في البساطة مش في التعقيد",
         "content": """

في ناس كتير بتفكر إن السعادة في الفلوس، أو العربية الفخمة، أو السفر لدول بعيدة. بس السعادة الحقيقية موجودة في حاجات بسيطة جدًا حوالينا كل يوم.

جرب تبص للسماء وقت الغروب، أو تشم ريحة قهوة الصبح، خليك ممتن للحاجات الصغيرة دي، لأنها بتديك طاقة وراحة نفسية أكتر من أي حاجة تانية.

كمان السعادة مش بس في الحاجات اللي عندك، لكنها في اللي بتقدمه لغيرك. لما ترسم ضحكة على وش حد، بتحس إن قلبك دافي ومبسوط.

ابدأ النهارده واستمتع بكل حاجة بسيطة حواليك، وافتكر: "السعادة اختيار، مش حاجة مستحيلة".

         """
        },
        {"title": "اتعلم تقول لأ من غير ما تحس بالذنب",
         "content": """

كتير مننا عنده مشكلة إنه بيوافق على كل حاجة عشان ما يضايقش الناس، حتى لو ده على حساب نفسه. بس خليني أقولك: مفيش حاجة اسمها إرضاء كل الناس، لأنك ببساطة مش هتقدر ، وفعلا صدق المثل : رضا الناس غايه لا تدرك.

لما حد يطلب منك حاجة، فكر كويس إذا كنت فعلاً قادر تساعده ولا لأ. ولو مش قادر، متتكسفش تقول "لأ". ده مش معناه إنك مش كويس، بالعكس، ده معناه إنك بتحترم وقتك وصحتك النفسية.

تقديرك لحدودك هو أول خطوة عشان تحب نفسك وتعيش مرتاح. متخليش شعور الذنب يمنعك من إنك تاخد قرارات تناسبك
         """
        },
        {"title":"خد شوية وقت لنفسك كل يوم",

         "content": """

الحياة سريعة ومليانة ضغط، وأحيانًا بننسى نهتم بنفسنا. بس الحقيقة، كل واحد فينا محتاج ياخد وقت لنفسه عشان يرتاح ويشحن طاقته.

جرب تعمل حاجة بتحبها كل يوم، حتى لو نص ساعة. اقرأ كتاب، اسمع موسيقى بتحبها، أو حتى اقعد في مكان هادي وتأمل. الحاجات البسيطة دي بتعمل فرق كبير في مزاجك وصحتك النفسية.

خد وقتك عشان تهتم بنفسك، لأنك تستحق تكون مرتاح وسعيد
         """
        },
        {"title":"التغيير بيبدأ بخطوة صغيرة",


         "content": """

كتير بنحس إننا عايزين نغير حياتنا، بس الفكرة دي ساعات بتكون مخيفة. طيب ليه متفكرش في التغيير على إنه خطوات صغيرة بدل ما يكون حاجة ضخمة؟

لو عايز تطور نفسك، جرب تبدأ بحاجة بسيطة، زي إنك تنظم وقتك أكتر، أو تتعلم مهارة جديدة. ومع الوقت، الخطوات الصغيرة دي هتتحول لإنجازات كبيرة.

افتكر إن الطريق الطويل بيبدأ بخطوة واحدة. متستناش اللحظة المثالية عشان تبدأ، لأن كل لحظة هي فرصة جديدة
         """
        },
        {"title":"اتعلم تعيش اللحظة",

         "content": """

إحنا كتير بنقضي وقتنا نفكر في الماضي أو نقلق من المستقبل. بس الحقيقة، اللي معاك دلوقتي هو اللحظة اللي بتعيشها، وهي دي اللي تقدر تتحكم فيها.

حاول تستمتع بكل حاجة بتعملها، حتى لو كانت حاجة بسيطة زي شرب كوبايه شاي ، تأمل ، قرايه كتاب ، ركز على اللحظة وحس بتفاصيلها. هتلاقي إنك بتستمتع أكتر ومشاعرك بقت أهدى.

العيش في اللحظة مش معناه إنك تتجاهل المستقبل، بس معناه إنك تدي كل وقت حقه وتستمتع بيه
         """
        },
        {
            "title":"الراحة النفسية أهم من إرضاء الناس",
            "content": """

كتير مننا بيحاول دايمًا يرضي اللي حواليه، بس ده ساعات بيجي على حساب راحتنا النفسية. الحقيقة، إرضاء كل الناس مستحيل، وأهم حاجة إنك ترضي نفسك الأول.

خليك صادق مع نفسك ومع اللي حواليك. متعملش حاجة بس عشان ترضي حد، اعملها لأنك عايز تعملها. لما تبدأ تحط راحتك النفسية أولوية، هتحس إنك أقوى وسعيد أكتر
"""
        },
        {
            "title": "التعبير عن المشاعر هو مفتاح الراحة",
            "content": """

كتير مننا بيكتم مشاعره عشان خايف يظهر ضعيف. بس الحقيقة، التعبير عن المشاعر هو اللي بيخليك تتخلص من الضغط اللي جواك.

لو مضايق، احكي لحد قريب منك، ولو ملقتش تعالى اتكلم هنا وعبر عن اللي جواك ، الكلام بيريحك وبيخليك تفهم نفسك أكتر.

افتكر إن التعبير عن مشاعرك مش ضعف، ده شجاعة وقوة
"""
        },
        {
            "title": "افهم نفسك أكتر عشان تهون عليك الدنيا",
            "content": """

أوقات كتير بنلاقي نفسنا مضايقين من غير سبب واضح. بنحس إن الحزن ماسك فينا ومش عارفين نهرب منه. بس الحقيقة، الحزن مش عيب ولا نقطة ضعف، ده زي جرس إنذار بيقولك "اهتم بنفسك".

جرب تسأل نفسك: إيه اللي مضايقني؟ ساعات هتكتشف إن السبب بسيط، زي ضغط الشغل، أو حاجة صغيرة حصلت وخدتها على أعصابك. المهم تبدأ تواجه مشاعرك بدل ما تهرب منها.

حاجة كمان مهمة: خلي حواليك ناس بتحبك وبتفهمك. مش شرط يكونوا كتير، المهم يكونوا بيحسسوك بالراحة. ولو حاسس إنك لوحدك، افتح قلبك لشخص تثق فيه. مجرد الكلام عن اللي جواك بيخفف كتير.

وأهم نصيحة: اتعلم تقول لنفسك كلام حلو. كل يوم الصبح، بص لنفسك في المراية وقول: "أنا قوي، أنا أقدر، والنهارده هيبقى يوم حلو". هتحس بفرق في مزاجك لما تبدأ يومك بطاقة إيجابية.

لو حاسس إنك عالق في دايرة الحزن، افتكر إن كل حاجة ليها حل. الحياة مش دايمًا وردي، بس دايمًا فيه فرصة تبدأ من جديد. خليك صبور مع نفسك، وافتكر إنك تستحق تكون سعيد
"""
        }
    ]
    put_markdown("# 🧠 مقالات نفسية🧠")
    
    
    put_button("🔙 العودة للصفحة الرئيسية", onclick=lambda: (clear(), show_patient_screen()))
    daily_articles = random.sample(articles, 1)
    
    for article in daily_articles:
        put_markdown(f"## {article['title']}")
        put_markdown(article['content'])
        put_markdown("---")
    with open(r"D:\my website your mind\IMAGE REA.jpg", "rb") as img_file:
        put_image(img_file.read())   
    put_button("قراءة مقالة اخرى",onclick=show_read_Articles)
def manage_articles():
    username = session_storage.user
    """Doctor interface for managing articles."""
    add_global_style()  
    clear()
    add_back_button()
    
    put_markdown("# إدارة المقالات")
    
    def add_new_article():
        article_info = input_group("إضافة مقال جديد", [
            input("عنوان المقال:", name="title", required=True),
            input("محتوى المقال:", name="content", type="text", required=True)
        ])
        if article_info:
            try:
                db.child("articles").push({
                    "title": article_info["title"],
                    "content": article_info["content"],
                    "author": username,
                    "date": datetime.now().isoformat()
                })
                popup("تم", "تم إضافة المقال بنجاح")
                manage_articles()
            except Exception as e:
                popup("خطأ", f"حدث خطأ أثناء إضافة المقال: {str(e)}")
    
    put_button("إضافة مقال جديد", onclick=add_new_article)
    put_markdown("## المقالات الحالية")
    articles = db.child("articles").get().val()
    if articles:
        for article_id, article in articles.items():
            put_markdown(f"### {article['title']}")
            put_text(f"الكاتب: {article.get('author', 'غير معروف')}")
            put_text(f"التاريخ: {article.get('date', 'غير معروف')}")
            put_buttons(['تعديل', 'حذف'], onclick=[
                lambda a=article_id: edit_article(a),
                lambda a=article_id: delete_article(a)
            ])
            put_markdown("---")

def edit_article(article_id):
    """Edit an existing article."""
    try:
        article = db.child("articles").child(article_id).get().val()
        if not article:
            popup("خطأ", "لم يتم العثور على المقال")
            return
            
        article_info = input_group("تعديل المقال", [
            input("عنوان المقال:", name="title", value=article['title']),
            input("محتوى المقال:", name="content", type="text", value=article['content'])
        ])
        
        if article_info:
            db.child("articles").child(article_id).update({
                "title": article_info["title"],
                "content": article_info["content"],
                "last_edited": datetime.now().isoformat()
            })
            popup("تم", "تم تحديث المقال بنجاح")
            manage_articles()
    except Exception as e:
        popup("خطأ", f"حدث خطأ أثناء تحديث المقال: {str(e)}")

def delete_article(article_id):
    """Delete an article."""
    if actions("هل أنت متأكد من حذف هذا المقال؟", ["نعم", "لا"]) == "نعم":
        try:
            db.child("articles").child(article_id).remove()
            popup("تم", "تم حذف المقال بنجاح")
            manage_articles()
        except Exception as e:
            popup("خطأ", f"حدث خطأ أثناء حذف المقال: {str(e)}")



def view_patient_profile(username):
    """عرض ملف المريض."""
    add_global_style()
    clear()
    add_back_button()
    
    
    try:
        user_data = db.child("users").child(username).get().val()
        if user_data:
            put_markdown(f"# ملف المريض: {user_data.get('name', username)}")
            put_html(f"""
                <div style="background-color: #F0FFF0; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <p><strong>اسم المستخدم:</strong> {username}</p>
                    <p><strong>البريد الإلكتروني:</strong> {user_data.get('email', '')}</p>
                    <p><strong>تاريخ التسجيل:</strong> {user_data.get('created_at', '').split('T')[0] if user_data.get('created_at') else ''}</p>
                </div>
            """)
        else:
            put_markdown("### لم يتم العثور على المريض")
            
    except Exception as e:
        print(f"Error in view_patient_profile: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض ملف المريض")
        view_patients()


        
def show_login_screen():
    """عرض شاشة تسجيل الدخول."""
    session_storage.current_page = "login"

    clear()
    add_global_style()
   
    put_button('رجوع', onclick=show_main_screen)
    
    
    put_html('<h1 style="text-align: center; color: #2c3e50; font-size: 2.5em; margin-bottom: 30px;">تسجيل الدخول</h1>')
  
    put_html('<div style="margin: 20px;"></div>')
    
    try:
       
        login_info = input_group("تسجيل الدخول", [
            input(placeholder='اسم المستخدم', name='username', required=True),
            input(placeholder='كلمة المرور', name='password', type=PASSWORD, required=True)
        ])
        
        if login_info:
            users = db.child("users").get()
            if users:
                for user in users.each():
                    user_data = user.val()
                    if (user_data.get('username') == login_info['username'] and 
                        user_data.get('password') == login_info['password']):
                        
                       
                        session_storage.user = login_info['username']
                        session_storage.role = user_data.get('role', 'patient')
                        
                     
                        if user_data.get('role') == 'doctor':
                            if user_data.get('approved', False):
                                return show_doctor_screen()
                            else:
                                popup("تنبيه", "حسابك قيد المراجعة من قبل المشرف")
                                return show_login_screen()
                        elif user_data.get('role') == 'admin':
                            return show_admin_screen()
                        else:
                            return show_patient_screen()
                            
            popup("خطأ", "اسم المستخدم أو كلمة المرور غير صحيحة")
            return show_login_screen()
            
    except Exception as e:
        print(f"Login error: {str(e)}")
        popup("خطأ", "حدث خطأ في تسجيل الدخول")
        return show_login_screen()
    
    # مسافة
    put_html('<div style="margin: 20px;"></div>')

def get_emotion_name(record_type):
    """ترجمة نوع السجل إلى العربية."""
    names = {
        'emotionless'
        'guilt': 'سجل الشعور بالذنب',
        'negative_thoughts': 'الأفكار السلبية',
        'sadness': 'سجل الحزن',
        'anger': 'سجل الغضب',
        'anxiety': 'سجل القلق',
        'stress': 'سجل التوتر',
        'psychological_assessment': 'التقييم النفسي',
        'psychological_assessment_results': 'نتائج التقييم النفسي',
        'medical_notes': 'الملاحظات الطبية'
    }
    return names.get(record_type, record_type)

def play_audio(audio_file):
    """تشغيل الملف الصوتي."""
    if audio_file and os.path.exists(audio_file):
        try:
           
            audio_html = f'<audio controls><source src="{audio_file}" type="audio/wav">Your browser does not support the audio element.</audio>'
            popup("تشغيل التسجيل الصوتي", [
                put_html(audio_html)
            ])
        except Exception as e:
            print(f"Error playing audio: {str(e)}")
            popup("خطأ", "فشل تشغيل التسجيل الصوتي")
    else:
        popup("خطأ", "الملف الصوتي غير موجود")

def add_new_patient():
    """إضافة مريض جديد."""
    clear()
    add_back_button()
    add_global_style()
    put_markdown("# إضافة مريض جديد")
    
    try:
       
        choice = radio("اختر طريقة الإضافة", options=[
            'إضافة مريض موجود',
            'إنشاء حساب جديد'
        ])
        
        if choice == 'إضافة مريض موجود':
           
            username = input("اسم المستخدم للمريض", type=TEXT, required=True)
           
            users = db.child("users").get()
            patient_found = False
            
            if users:
                for user in users.each():
                    user_data = user.val()
                    if user_data.get('username') == username and user_data.get('role') == 'patient':
                        patient_found = True
                        doctor_id = session_storage.user
                        
                       
                        doctor_patients = db.child("doctor_patients").child(doctor_id).get()
                        already_added = False
                        
                        if doctor_patients:
                            for patient in doctor_patients.each():
                                if patient.val().get('patient_username') == username:
                                    already_added = True
                                    break
                        
                        if already_added:
                            popup('تنبيه', 'المريض موجود مسبقاً في قائمتك')
                        else:
                           
                            db.child("doctor_patients").child(doctor_id).push({
                                'patient_username': username,
                                'added_at': datetime.now().isoformat()
                            })
                            popup('تم', 'تم إضافة المريض إلى قائمتك بنجاح')
                        break
            
            if not patient_found:
                if actions('لم يتم العثور على المريض. هل تريد إنشاء حساب جديد؟', 
                          ['نعم', 'لا']) == 'نعم':
                    choice = 'إنشاء حساب جديد'
                else:
                    return show_doctor_screen()
        
        if choice == 'إنشاء حساب جديد':
           
            data = input_group("معلومات المريض الجديد", [
                input('اسم المريض', name='name', required=True),
                input('اسم المستخدم', name='username', required=True),
                input('كلمة المرور', name='password', type=PASSWORD, required=True),
                input('البريد الإلكتروني', name='email', type=TEXT, required=True),
                input('رقم الهاتف', name='phone', type=TEXT, required=True),
                input('العمر', name='age', type=NUMBER, required=True),
                select('الجنس', name='gender', options=['ذكر', 'أنثى'], required=True),
                textarea('ملاحظات طبية', name='medical_notes', rows=3)
            ])
            
           
            users = db.child("users").get()
            if users:
                for user in users.each():
                    if user.val().get('username') == data['username']:
                        popup('خطأ', 'اسم المستخدم موجود مسبقاً')
                        return add_new_patient()
            
            try:
                
                user_data = {
                    'name': data['name'],
                    'username': data['username'],
                    'password': data['password'],  
                    'email': data['email'],
                    'phone': data['phone'],
                    'age': data['age'],
                    'gender': data['gender'],
                    'role': 'patient',
                    'medical_notes': data['medical_notes'],
                    'created_at': datetime.now().isoformat()
                }
                
                
                db.child("users").push(user_data)
                
               
                doctor_id = session_storage.user
                db.child("doctor_patients").child(doctor_id).push({
                    'patient_username': data['username'],
                    'added_at': datetime.now().isoformat()
                })
                
                db.child("medical_history").child(data['username']).set({
                    'created_at': datetime.now().isoformat(),
                    'doctor_id': doctor_id
                })
                
                popup('تم', 'تم إنشاء حساب المريض وإضافته إلى قائمتك بنجاح')
                
            except Exception as e:
                print(f"Error adding new patient: {str(e)}")
                popup('خطأ', 'حدث خطأ في إنشاء حساب المريض')
        
        
        view_patients()
        
    except Exception as e:
        print(f"Error in add new patient: {str(e)}")
        popup('خطأ', 'حدث خطأ في العملية')
        show_doctor_screen()  

def get_patients_count(doctor_id):
    """Get the number of patients for a doctor."""
    try:
        doctor_patients = db.child("doctor_patients").child(doctor_id).get()
        if doctor_patients and doctor_patients.val():
            return len(doctor_patients.val())
        return 0
    except Exception as e:
        print(f"Error getting patients count: {str(e)}")
        return 0
def show_doctor_screen():
    """عرض الشاشة الرئيسية للطبيب."""
    session_storage.current_page = "doctor"

    add_global_style()
    clear()
    
    try:
        if not hasattr(session_storage, 'user'):
            popup("خطأ", "الرجاء تسجيل الدخول أولاً")
            return show_login_screen()
        
        username = session_storage.user
        
       
        doctor_info = None
        users = db.child("users").get()
        if users:
            for user in users.each():
                if user.val().get('username') == username:
                    doctor_info = user.val()
                    break
        
        doctor_name = doctor_info.get('name', username) if doctor_info else username
        
        add_global_style()
        put_html(f"""
            <div style="
                background: linear-gradient(135deg, #f0fff0 0%, #e8f5e9 100%);
                padding: 30px;
                border-radius: 15px;
                margin-bottom: 30px;
                box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                text-align: center;
            ">
                <h1 style="color: #2e7d32; margin: 0; font-size: 2.5em;">مرحباً د. {doctor_name}</h1>
                <p style="color: #4caf50; margin: 10px 0;">Your Mind - منصة الصحة النفسية</p>
            </div>
        """)

       
        stats_cards = [
            {"title": "المواعيد اليوم", "value": "0", "icon": "📅"},
            {"title": "المرضى الحاليين", "value": str(get_patients_count(username)), "icon": "👥"},
            {"title": "طلبات المواعيد", "value": "0", "icon": "🔔"}
        ]
        
        put_grid([
            [
                put_html(f"""
                    <div style="
                        background: white;
                        padding: 20px;
                        border-radius: 12px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                        text-align: center;
                    ">
                        <div style="font-size: 2em; margin-bottom: 10px;">{card['icon']}</div>
                        <h3 style="color: #2e7d32; margin: 0;">{card['title']}</h3>
                        <p style="font-size: 1.5em; color: #4caf50; margin: 10px 0;">{card['value']}</p>
                    </div>
                """) for card in stats_cards
            ]
        ])
        add_global_style()
       
        put_row([
            put_button('👤 الملف الشخصي', onclick=lambda: edit_doctor_profile(username)),
            put_button('💬 المحادثات', onclick=send_message),
            put_button('📝 المقالات', onclick=manage_articles)
        ], size='auto auto auto auto')

        
        put_row([
            put_button('📅 إدارة المواعيد', onclick=manage_appointments),
            put_button('👥 عرض المرضى', onclick=view_patients),
            put_button('➕ إضافة مريض', onclick=add_new_patient)
        ], size='auto auto auto auto')

    
        put_button('🚪 تسجيل الخروج', onclick=logout)

    except Exception as e:
        print(f"Doctor screen error: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض الصفحة")
        return show_login_screen()


def handle_doctor_actions(action):
    """معالجة أزرار شاشة الطبيب."""
    actions = {
        'appointments': manage_appointments,
        'requests': view_appointment_requests,
        'patients': view_patients,
        'add_patient': add_new_patient
    }
    
    if action in actions:
        actions[action]()

def get_patient_info(patient_id):
    """Get patient information from database."""
    try:
        users = db.child("users").get().val()
        if users:
            for user in users.values():
                if user.get('username') == patient_id:
                    return user
        return None
    except Exception as e:
        logging.error(f"Error getting patient info: {str(e)}")
        return None

            
    except Exception as e:
        logging.error(f"Error managing doctors: {str(e)}")
        popup("خطأ", "حدث خطأ أثناء عرض قائمة الأطباء")
def manage_appointments():
    """إدارة المواعيد."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# إدارة المواعيد")
    
    try:
       
        put_buttons([
            {'label': '➕ موعد جديد', 'value': 'new', 'color': 'success'},
            {'label': '📅 عرض المواعيد', 'value': 'view', 'color': 'info'}
        ], onclick=handle_appointment_action)
        
    except Exception as e:
        print(f"Manage appointments error: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة المواعيد")

def edit_appointment(appointment_id):
    """تعديل موعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
        
        appointment = db.child("appointments").child(current_doctor).child(appointment_id).get()
        
        if appointment and appointment.val():
            data = appointment.val()
            
            
            updated_info = input_group("تعديل الموعد", [
                input('التاريخ', type=TEXT, name='date', value=data.get('date', '')),
                input('الوقت', type=TEXT, name='time', value=data.get('time', '')),
                select('الحالة', options=['مجدول', 'تم', 'ملغي'], name='status', value=data.get('status', 'مجدول'))
            ])
            
            if updated_info:
               
                db.child("appointments").child(current_doctor).child(appointment_id).update({
                    'date': updated_info['date'],
                    'time': updated_info['time'],
                    'status': updated_info['status'],
                    'updated_at': datetime.now().isoformat()
                })
                
                popup("تم", "تم تحديث الموعد بنجاح")
        
        manage_appointments()
        
    except Exception as e:
        print(f"Error in edit_appointment: {str(e)}")
        popup("خطأ", "فشل تعديل الموعد")
        manage_appointments()
def handle_appointment_action(action_data):
    """معالجة إجراءات المواعيد (تأكيد، إلغاء، إكمال)."""
    try:
        current_user = session_storage.user
        
       
        action = action_data[0] 
        appointment_id = action_data[1] 
       
        if action == 'confirm':
            db.child("appointments").child(current_user).child(appointment_id).update({
                'status': 'مؤكد'
            })
            popup("تم", "تم تأكيد الموعد بنجاح")
            
        elif action == 'cancel':
            db.child("appointments").child(current_user).child(appointment_id).update({
                'status': 'ملغي'
            })
            popup("تم", "تم إلغاء الموعد")
            
        elif action == 'complete':
            db.child("appointments").child(current_user).child(appointment_id).update({
                'status': 'مكتمل'
            })
            popup("تم", "تم تحديث حالة الموعد إلى مكتمل")
        
        view_appointments()
        
    except Exception as e:
        print(f"Handle appointment action error: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")
        view_appointments()

def display_appointment(app_data, role, app_id=None):
    """عرض تفاصيل الموعد."""
  
    status = app_data.get('status', 'مجدول')
    status_colors = {
        'مجدول': '#E8F5E9', 
        'مؤكد': '#E3F2FD',   
        'مكتمل': '#F3E5F5',
        'ملغي': '#FFEBEE'    
    }
    bg_color = status_colors.get(status, '#F5F5F5')
    
   
    patient_username = app_data.get('patient_username', '')
    patient_name = patient_username
    patient_info = None
    
    try:
        users = db.child("users").get()
        if users:
            for user in users.each():
                if user.val() and isinstance(user.val(), dict):
                    if user.val().get('username') == patient_username:
                        patient_info = user.val()
                        patient_name = patient_info.get('name', patient_username)
                        break
    except Exception as e:
        print(f"Error getting patient info: {str(e)}")
    
    
    doctor_id = app_data.get('doctor_id', '')
    
    put_html(f"""
        <div style="
            margin: 15px 0;
            padding: 20px;
            background-color: {bg_color};
            border-radius: 15px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            border: 1px solid #ddd;
        ">
            <div style="display: flex; justify-content: space-between; margin-bottom: 15px;">
                <div>
                    <h3 style="margin: 0; color: #333; font-size: 18px;">
                        {f'المريض: {patient_name}' if role == 'doctor' else f'الطبيب: {doctor_id}'}
                    </h3>
                    {f'<p style="margin: 3px 0; color: #666; font-size: 14px;">({patient_username})</p>' if role == 'doctor' and patient_name != patient_username else ''}
                    <p style="margin: 5px 0; color: #666;">
                        <span style="
                            display: inline-block;
                            padding: 3px 10px;
                            border-radius: 12px;
                            background-color: {bg_color};
                            border: 1px solid #ccc;
                            font-size: 14px;
                        ">{status}</span>
                    </p>
                </div>
                <div style="text-align: left;">
                    <p style="margin: 0; color: #666;">
                        <strong>التاريخ:</strong> {app_data.get('date', '')}
                    </p>
                    <p style="margin: 5px 0; color: #666;">
                        <strong>الوقت:</strong> {app_data.get('time', '')}
                    </p>
                </div>
            </div>
            
            <div style="
                background-color: white;
                padding: 10px;
                border-radius: 8px;
                margin-top: 10px;
            ">
                <p style="margin: 0; color: #666;">
                    <strong>ملاحظات:</strong><br>
                    {app_data.get('notes', 'لا توجد ملاحظات')}
                </p>
            </div>
        </div>
    """)
    
    
    if role == 'doctor':
        if status == 'مجدول':
            put_row([
                put_button('✓ تأكيد', onclick=lambda: handle_appointment_action(['confirm', app_id])),
                put_button('✕ إلغاء', onclick=lambda: handle_appointment_action(['cancel', app_id]))
            ])
        elif status == 'مؤكد':
            put_row([
                put_button('✓ إكمال', onclick=lambda: handle_appointment_action(['complete', app_id])),
                put_button('✕ إلغاء', onclick=lambda: handle_appointment_action(['cancel', app_id]))
            ])
def view_appointments():
    """عرض المواعيد."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# المواعيد")
    
    try:
        current_user = session_storage.user
        role = session_storage.role
        
        
        appointments_found = False
        
        if role == 'doctor':
            appointments = db.child("appointments").child(current_user).get()
            if appointments and appointments.val():
                appointments_found = True
                for app_id, app_data in appointments.val().items():
                    if isinstance(app_data, dict):
                        display_appointment(app_data, role, app_id)
        else:
            appointments_ref = db.child("appointments").get()
            if appointments_ref and appointments_ref.val():
                for doctor_id, doctor_appointments in appointments_ref.val().items():
                    if isinstance(doctor_appointments, dict):
                        for app_id, app_data in doctor_appointments.items():
                            if isinstance(app_data, dict) and app_data.get('patient_username') == current_user:
                                appointments_found = True
                                app_data['doctor_id'] = doctor_id
                                display_appointment(app_data, role, app_id)
        
        if not appointments_found:
            put_text("لا توجد مواعيد")
        
       
        if role == 'doctor':
            put_button('➕ إضافة موعد جديد', onclick=add_appointment)
        else:
            put_button('➕ طلب موعد جديد', onclick=request_new_appointment)
            
    except Exception as e:
        print(f"View appointments error: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض المواعيد")
def delete_appointment(appointment_id):
    """حذف موعد."""
    try:
        if actions("هل أنت متأكد من حذف هذا الموعد؟", ['نعم', 'لا']) == 'نعم':
            from pywebio.session import local as session_storage
            current_doctor = session_storage.user
            
            db.child("appointments").child(current_doctor).child(appointment_id).remove()
            popup("تم", "تم حذف الموعد بنجاح")
        
        manage_appointments()
        
    except Exception as e:
        print(f"Error in delete_appointment: {str(e)}")
        popup("خطأ", "فشل حذف الموعد")
        manage_appointments()

def show_statistics():
    """Admin interface to view system statistics."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# إحصائيات النظام")
    
    try:
        users = db.child("users").get().val()
        assessments = db.child("assessments").get().val()
        
        total_users = len(users)
        total_patients = len([u for u in users.values() if u.get('role') == 'patient'])
        total_doctors = len([u for u in users.values() if u.get('role') == 'doctor'])
        total_assessments = len(assessments)
        
        put_markdown(f"""
        ## إحصائيات المستخدمين
        - إجمالي المستخدمين: {total_users}
        - عدد المرضى: {total_patients}
        - عدد الأطباء: {total_doctors}
        
        ## إحصائيات التقييمات
        - إجمالي التقييمات: {total_assessments}
        """)
        
    except Exception as e:
        logging.error(f"Statistics error: {str(e)}")
        error_handler.handle_error('database_operation', e)

def show_main_screen():
    """عرض الشاشة الرئيسية."""
    clear()
    add_global_style()
    
    put_markdown("Your Mind").style('text-align: center; color: #2c3e50; font-size: 3.5em; margin-bottom: 40px;')
    
    
    put_text("منصتك الموثوقة للصحة النفسية Your Mind، مرحباً بك في تطبيق").style('text-align: center; color: #666; font-size: 1.3em;')
    put_text("نحن هنا لمساعدتك في رحلتك نحو الصحة النفسية الأفضل").style('text-align: center; color: #666; font-size: 1.3em; margin-bottom: 50px;')
    
   
    put_text("").style('margin: 20px')
    
  
    put_buttons([
        {'label': 'تسجيل الدخول', 'value': 'login', 'color': 'primary'},
        {'label': 'إنشاء حساب', 'value': 'register', 'color': 'success'}
    ], onclick=lambda x: show_login_screen() if x == 'login' else create_account_screen()).style('text-align: center')
    
    
    put_text("").style('margin: 20px')
   
   
    put_text("للتواصل والدعم: YOURMIND.EG@GMAIL.COM").style('text-align: center; color: #888; margin-top: 50px;')
class SessionManager:
    def __init__(self):
        self.current_user = None
        self.current_role = None  
        self.current_email = None
        self.is_logged_in = False

    def login_user(self, username, role, email):
        self.current_user = username
        self.current_role = role  
        self.current_email = email
        self.is_logged_in = True

    def logout_user(self):
        self.current_user = None
        self.current_role = None
        self.current_email = None
        self.is_logged_in = False


session_manager = SessionManager()
def create_account_screen():
    """تسجيل حساب جديد."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# إنشاء حساب جديد")
    
    try:
       
        account_type = select("نوع الحساب*", ["طبيب", "مريض"])
        
        if account_type == "طبيب":
            
            doctor_info = input_group("معلومات الطبيب", [
                input("اسم المستخدم*", name="username", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("كلمة المرور*", name="password", type='password', validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("تأكيد كلمة المرور*", name="confirm_password", type='password', validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("البريد الإلكتروني*", name="email", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("الاسم الكامل*", name="full_name", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                select("التخصص*", [
                    "نفسي",
                    "استشاري نفسي",
                    "معالج نفسي",
                    "أخصائي نفسي",
                    "معالج سلوكي"
                ], name="specialty", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                select("المحافظة*", [
                    "القاهرة",
                    "الإسكندرية",
                    "الجيزة",
                    "القليوبية",
                    "الشرقية",
                    "الغربية",
                    "المنوفية",
                    "البحيرة",
                    "كفر الشيخ",
                    "الدقهلية",
                    "الإسماعيلية",
                    "السويس",
                    "بورسعيد",
                    "شمال سيناء",
                    "جنوب سيناء",
                    "البحر الأحمر",
                    "الوادي الجديد",
                    "مطروح",
                    "الفيوم",
                    "بني سويف",
                    "المنيا",
                    "أسيوط",
                    "سوهاج",
                    "قنا",
                    "الأقصر",
                    "أسوان"
                ], name="governorate", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("العنوان التفصيلي*", name="address", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("رقم الهاتف*", name="phone", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("سعر الكشف*", name="fees", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("مواعيد العمل*", name="working_hours", 
                      placeholder="مثال: السبت-الخميس 10:00 صباحاً - 8:00 مساءً",
                      validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                textarea("نبذة عن الطبيب*", name="about", 
                        placeholder="اكتب نبذة مختصرة عن خبراتك ومؤهلاتك...",
                        validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("رقم الترخيص المهني*", name="license_number", 
                      validate=lambda x: "هذا الحقل مطلوب" if not x else None)
            ])
            
            if doctor_info["password"] != doctor_info["confirm_password"]:
                popup("خطأ", "كلمة المرور غير متطابقة")
                return show_login_screen()
            
            try:
                 
                fees = float(doctor_info["fees"])
                
                doctor_data = {
                    "username": doctor_info["username"],
                    "password": doctor_info["password"],
                    "email": doctor_info["email"],
                    "full_name": doctor_info["full_name"],
                    "specialty": doctor_info["specialty"],
                    "governorate": doctor_info["governorate"],
                    "address": doctor_info["address"],
                    "phone": doctor_info["phone"],
                    "fees": fees,
                    "working_hours": doctor_info["working_hours"],
                    "about": doctor_info["about"],
                    "license_number": doctor_info["license_number"],
                    "role": "doctor",
                    "approved": False,
                    "created_at": datetime.now().isoformat(),
                    "rating": 0,
                    "reviews_count": 0
                }
                
               
                existing_user = db.child("users").child(doctor_info["username"]).get()
                if existing_user.val():
                    popup("خطأ", "اسم المستخدم موجود بالفعل")
                    return show_login_screen()
                
                db.child("users").child(doctor_info["username"]).set(doctor_data)
                popup("تم", "تم إنشاء الحساب بنجاح! في انتظار موافقة الإدارة")
                show_login_screen()
                
            except ValueError:
                popup("خطأ", "الرجاء إدخال رقم صحيح لسعر الكشف")
                return show_login_screen()
            except Exception as e:
                print(f"Error in doctor registration: {str(e)}")
                popup("خطأ", "حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى")
        elif account_type == "مريض":
            
            patient_info = input_group("معلومات المريض", [
                input("اسم المستخدم*", name="username", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("كلمة المرور*", name="password", type='password', validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("تأكيد كلمة المرور*", name="confirm_password", type='password', validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input("البريد الإلكتروني*", name="email", validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                input('رقم الهاتف', name='phone',validate=lambda x: "هذا الحقل مطلوب" if not x else None), 
                input('العمر', name='age', type=NUMBER, validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                select('الجنس', options=['ذكر', 'أنثى'], name='gender', validate=lambda x: "هذا الحقل مطلوب" if not x else None),
                select("المحافظة*", [
                    "القاهرة",
                    "الإسكندرية",
                    "الجيزة",
                    "القليوبية",
                    "الشرقية",
                    "الغربية",
                    "المنوفية",
                    "البحيرة",
                    "كفر الشيخ",
                    "الدقهلية",
                    "الإسماعيلية",
                    "السويس",
                    "بورسعيد",
                    "شمال سيناء",
                    "جنوب سيناء",
                    "البحر الأحمر",
                    "الوادي الجديد",
                    "مطروح",
                    "الفيوم",
                    "بني سويف",
                    "المنيا",
                    "أسيوط",
                    "سوهاج",
                    "قنا",
                    "الأقصر",
                    "أسوان"
                ], name="governorate", validate=lambda x: "هذا الحقل مطلوب" if not x else None),       
                   
            ])
            
            if patient_info["password"] != patient_info["confirm_password"]:
                popup("خطأ", "كلمة المرور غير متطابقة")
                return show_login_screen()
            
            try:
                
                existing_user = db.child("users").child(patient_info["username"]).get()
                if existing_user.val():
                    popup("خطأ", "اسم المستخدم موجود بالفعل")
                    return show_login_screen()
                
                patient_data = {
                    "username": patient_info["username"],
                    "password": patient_info["password"],
                    "email": patient_info["email"],
                    "phone": patient_info["phone"],
                    "age": patient_info["age"],
                    "gender": patient_info["gender"],
                    "governorate": patient_info["governorate"],
                    "role": "patient",
                    "created_at": datetime.now().isoformat()
                }
                
                db.child("users").child(patient_info["username"]).set(patient_data)
                popup("تم", "تم إنشاء الحساب بنجاح!")
                show_login_screen()
                
            except Exception as e:
                print(f"Error in patient registration: {str(e)}")
                popup("خطأ", "حدث خطأ أثناء التسجيل. يرجى المحاولة مرة أخرى")
                
    except Exception as e:
        print(f"Registration error: {str(e)}")
        popup("خطأ", "حدث خطأ غير متوقع")
        show_main_screen()
def handle_logout():
    """Handle logout logic."""
    from pywebio.session import local as session_storage
    
    
    session_storage.user = None
    session_storage.role = None
    session_storage.is_logged_in = False
    
    clear()
    show_main_screen()
def download_medical_history(username):
    """تحميل السجل الطبي كملف PDF."""
    try:
        
        medical_ref = db.child("medical_history").child(username)
        medical_data = medical_ref.get()
        
        if medical_data and medical_data.val():
            records = medical_data.val()
            
          
            content = f"السجل الطبي للمريض: {username}\n\n"
            
           
            if 'psychological_assessment' in records:
                content += "التقييم النفسي:\n"
                psych_records = records['psychological_assessment']
                if isinstance(psych_records, dict):
                    total_score = 0
                    for record in psych_records.values():
                        timestamp = record.get('timestamp', '').split('T')[0] if record.get('timestamp') else 'غير محدد'
                        score = record.get('score', 0)
                        total_score += score
                        content += f"\nالتاريخ: {timestamp}\n"
                        content += f"السؤال: {record.get('question', '')}\n"
                        content += f"الإجابة: {record.get('answer', '')}\n"
                    content += f"\nالمجموع الكلي: {total_score}\n"
            
            
            emotions = {
                'emotionless'
                'anger': 'سجل الغضب',
                'sadness': 'سجل الحزن',
                'stress': 'سجل التوتر',
                'negative_thoughts': 'سجل الأفكار السلبية',
                'gulit': 'سجل الشعور بالذنب'
            }
            
            for emotion, title in emotions.items():
                if emotion in records:
                    content += f"\n{title}:\n"
                    emotion_records = records[emotion]
                    if isinstance(emotion_records, dict):
                        for record in emotion_records.values():
                            timestamp = record.get('timestamp', '').split('T')[0] if record.get('timestamp') else 'غير محدد'
                            content += f"\nالتاريخ: {timestamp}\n"
                            content += f"السؤال: {record.get('question', '')}\n"
                            content += f"الإجابة: {record.get('answer', '')}\n"
                            content += f"رد النظام: {record.get('system_response', '')}\n"
            
           
            filename = f"medical_history_{username}_{datetime.now().strftime('%Y%m%d')}.txt"
            
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            
            with open(filename, 'rb') as f:
                content = f.read()
            
           
            os.remove(filename)
            
            
            put_file(filename, content)
            
        else:
            popup("تنبيه", "لا يوجد سجل طبي للتحميل")
            
    except Exception as e:
        print(f"Error in download_medical_history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        popup("خطأ", "حدث خطأ في تحميل السجل الطبي")

def view_history():
    add_global_style()
    clear()
    add_back_button()
    
    
    try:
       
        current_user = session_storage.user
        
        put_markdown("# سجلي الطبي")
        
        
        medical_ref = db.child("medical_history").child(current_user)
        medical_data = medical_ref.get()
        
        if medical_data and medical_data.val():
            records = medical_data.val()
            
           
            if 'psychological_assessment' in records:
                put_markdown("## التقييم النفسي")
                put_html('<div style="background-color: #f0fff0; padding: 15px; border-radius: 8px; margin-bottom: 20px;">')
                psych_records = records['psychological_assessment']
                total_score = 0
                if isinstance(psych_records, dict):
                    for record in psych_records.values():
                        timestamp = record.get('timestamp', '').split('T')[0] if record.get('timestamp') else 'غير محدد'
                        score = record.get('score', 0)
                        total_score += score
                        put_html(f"""
                            <div style="margin: 10px 0; padding: 15px; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                <p><strong>التاريخ:</strong> {timestamp}</p>
                                <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                                <p><strong>إجابتك:</strong> {record.get('answer', '')}</p>
                            </div>
                        """)
                put_html(f'<div style="text-align: center; margin-top: 10px;"><strong>المجموع الكلي:</strong> {total_score}</div>')
                put_html('</div>')
            
            
            emotions = {
                'emotionless'
                'anger': {'title': 'سجل الغضب', 'color': '#fff0f0'},
                'sadness': {'title': 'سجل الحزن', 'color': '#f0f0ff'},
                'stress': {'title': 'سجل التوتر', 'color': '#fff0ff'},
                'negative_thoughts': {'title': 'سجل الأفكار السلبية', 'color': '#fff0f0'},
                'guilt': {'title': 'سجل الشعور بالذنب', 'color': '#fff0f0'}
            }
            
            for emotion, details in emotions.items():
                if emotion in records:
                    put_markdown(f"## {details['title']}")
                    put_html(f'<div style="background-color: {details["color"]}; padding: 15px; border-radius: 8px; margin-bottom: 20px;">')
                    emotion_records = records[emotion]
                    if isinstance(emotion_records, dict):
                        
                        sorted_records = sorted(
                            emotion_records.items(),
                            key=lambda x: x[1].get('timestamp', ''),
                            reverse=True
                        )
                        for _, record in sorted_records:
                            timestamp = record.get('timestamp', '').split('T')[0] if record.get('timestamp') else 'غير محدد'
                            put_html(f"""
                                <div style="margin: 10px 0; padding: 15px; background-color: white; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
                                    <p><strong>التاريخ:</strong> {timestamp}</p>
                                    <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                                    <p><strong>إجابتك:</strong> {record.get('answer', '')}</p>
                                    <p><strong>رد النظام:</strong> {record.get('system_response', '')}</p>
                                </div>
                            """)
                            if record.get('audio_file'):
                                put_button('🔊 تشغيل التسجيل الصوتي', 
                                         onclick=lambda f=record['audio_file']: play_audio(f),
                                         color='info')
                    put_html('</div>')
            
            
            put_button('📥 تحميل السجل الطبي', onclick=lambda: download_medical_history(current_user))
            add_back_button()
            
        else:
            put_html("""
                <div style="text-align: center; padding: 20px; background-color: #f5f5f5; border-radius: 8px;">
                    <h3>لا يوجد سجل طبي حتى الآن</h3>
                    <p>ابدأ بإجراء التقييم النفسي أو تسجيل مشاعرك</p>
                </div>
            """)
            
    except Exception as e:
        print(f"Error in view_history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        popup("خطأ", "حدث خطأ في عرض السجل الطبي")
def add_appointment():
    """إضافة موعد جديد."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# إضافة موعد جديد")
    
    try:
        current_doctor = session_storage.user
        
        
        doctor_patients = db.child("doctor_patients").child(current_doctor).get()
        patients_list = []
        
        if doctor_patients and doctor_patients.val():
            for dp in doctor_patients.each():
                patient_data = dp.val()
                if isinstance(patient_data, dict):
                    patient_username = patient_data.get('patient_username')
                    if patient_username:
                        
                        users = db.child("users").get()
                        patient_name = patient_username
                        if users:
                            for user in users.each():
                                if user.val().get('username') == patient_username:
                                    patient_name = user.val().get('name', patient_username)
                                    break
                        
                        patients_list.append({
                            'label': f"{patient_name} ({patient_username})",
                            'value': patient_username
                        })
        
        if patients_list:
           
            appointment_data = input_group("تفاصيل الموعد", [
                select('المريض', options=patients_list, name='patient_username', required=True),
                input('التاريخ', type=DATE, name='date', required=True),
                input('الوقت', type=TIME, name='time', required=True),
                input('ملاحظات', name='notes')
            ])
            
            if appointment_data:
               
                db.child("appointments").child(current_doctor).push({
                    'patient_username': appointment_data['patient_username'],
                    'date': appointment_data['date'],
                    'time': appointment_data['time'],
                    'notes': appointment_data.get('notes', ''),
                    'status': 'مجدول',
                    'created_at': datetime.now().isoformat()
                })
                
                popup("تم", "تم إضافة الموعد بنجاح")
                view_appointments()
        else:
            put_text("لا يوجد مرضى متاحين لإضافة موعد")
            put_button("إضافة مريض جديد", onclick=add_new_patient)
            
    except Exception as e:
        print(f"Add appointment error: {str(e)}")
        popup("خطأ", "حدث خطأ في إضافة الموعد")
        view_appointments()
def view_patient_recordings(patient_username):
    """عرض تسجيلات المريض."""
    add_global_style()
    clear()
    add_back_button()
    
    
    try:
        
        patient_info = db.child("users").child(patient_username).get().val()
        if not patient_info:
            put_text("لم يتم العثور على المريض")
            return
            
        put_markdown(f"# تسجيلات المريض: {patient_info.get('name', patient_username)}")
        
       
        recordings = db.child("recordings").child(patient_username).get().val()
        if recordings:
            for recording_type, type_recordings in recordings.items():
                put_markdown(f"## تسجيلات {get_recording_type_name(recording_type)}")
                
                if isinstance(type_recordings, dict):
                    for recording_id, recording_data in type_recordings.items():
                        if isinstance(recording_data, dict):
                            put_html(f"""
                                <div style="
                                    margin: 10px 0;
                                    padding: 15px;
                                    background-color: #F5F5F5;
                                    border-radius: 8px;
                                    border: 1px solid #E0E0E0;
                                ">
                                    <p><strong>التاريخ:</strong> {recording_data.get('timestamp', '')}</p>
                                    <p><strong>الملاحظات:</strong> {recording_data.get('notes', 'لا توجد ملاحظات')}</p>
                                    <audio controls>
                                        <source src="{recording_data.get('url', '')}" type="audio/mpeg">
                                        المتصفح لا يدعم تشغيل الملفات الصوتية
                                    </audio>
                                </div>
                            """)
                
        else:
            put_text("لا توجد تسجيلات")
            
    except Exception as e:
        print(f"Error viewing patient recordings: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض التسجيلات")

def get_recording_type_name(recording_type):
    """الحصول على الاسم العربي لنوع التسجيل."""
    recording_types = {
        'sadness': 'الحزن',
        'anger': 'الغضب',
        'stress': 'التوتر',
    }
    return recording_types.get(recording_type, recording_type)        

def view_patients():
    """عرض قائمة المرضى للطبيب."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# قائمة المرضى")
    
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        doctor_patients = db.child("doctor_patients").child(current_doctor).get()
        
        if not doctor_patients:
            put_text("لا يوجد مرضى حالياً")
            return
        
       
        patients_data = []
        users = db.child("users").get()
        
        if users:
            for dp in doctor_patients.each():
                patient_username = dp.val().get('patient_username')
                if patient_username:
                    for user in users.each():
                        if user.val().get('username') == patient_username:
                            patient_info = user.val()
                            patients_data.append([
                                patient_info.get('username', ''),
                                patient_info.get('email', ''),
                                dp.val().get('added_at', '').split('T')[0],
                                put_button('عرض التفاصيل', onclick=lambda u=patient_username:show_patient_medical_history(u))
                            ])
                            break
        
        if patients_data:
            put_table(
                patients_data,
                header=['اسم المستخدم', 'البريد الإلكتروني', 'تاريخ الإضافة', 'الإجراءات']
            )
        else:
            put_text("لا يوجد مرضى حالياً")
            
    except Exception as e:
        print(f"Error in view_patients: {str(e)}")
        popup("خطأ", "فشل تحميل قائمة المرضى")

def show_patient_medical_history(patient_username):
    """عرض السجل الطبي للمريض."""
    add_global_style()
    clear()
    add_back_button()
    
    
    try:
        put_markdown(f"# السجل الطبي للمريض: {patient_username}")
        
        
        medical_history = db.child("medical_history").child(patient_username).get().val()
        
        if medical_history:
            if 'psychological_assessment' in medical_history:
                put_markdown("## التقييم النفسي")
                for record in medical_history['psychological_assessment'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #f0fff0; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)
            if'negative_thoughts' in medical_history:
                put_markdown("## سجل الأفكار السلبية")
                for record in medical_history['negative_thoughts'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #fff0f0; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)

            if'guilt' in medical_history:
                put_markdown("## سجل الشعور بالذنب")
                for record in medical_history['guilt'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #fff0f0; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)
                    
            if'emotionless' in medical_history:
                put_markdown("## سجل الشعور بالذنب")
                for record in medical_history['emotionless'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #fff0f0; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)       
           
            if 'sadness' in medical_history:
                put_markdown("## سجل الحزن")
                for record in medical_history['sadness'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #f5f5f5; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)
            
          
            if 'anger' in medical_history:
                put_markdown("## سجل الغضب")
                for record in medical_history['anger'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #fff0f0; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)
            
            
            if 'stress' in medical_history:
                put_markdown("## سجل التوتر")
                for record in medical_history['stress'].values():
                    put_html(f"""
                        <div style="margin: 10px 0; padding: 15px; background-color: #f0f0ff; border-radius: 8px;">
                            <p><strong>السؤال:</strong> {record.get('question', '')}</p>
                            <p><strong>الإجابة:</strong> {record.get('answer', '')}</p>
                            <p><strong>التاريخ:</strong> {record.get('timestamp', '').split('T')[0]}</p>
                        </div>
                    """)
                    
           
            elif record.get('audio_file'):
                put_button('تشغيل التسجيل', onclick=lambda f=record['audio_file']: play_audio(f))
               
        else:
            put_text("لا يوجد سجل طبي لهذا المريض")
        put_button('تحميل السجل الطبي', onclick=lambda:download_medical_history(current_user))  
        add_back_button()    
    except Exception as e:
        print(f"Error in view_patient_medical_history: {str(e)}")
        import traceback
        print(traceback.format_exc())
        popup("خطأ", "حدث خطأ في عرض السجل الطبي")


def view_patient_profile(username):
    """عرض ملف المريض."""
    add_global_style()
    clear()
    add_back_button()
    
    
    try:
        user_data = db.child("users").child(username).get().val()
        if user_data:
            put_markdown(f"# ملف المريض: {user_data.get('name', username)}")
            put_html(f"""
                <div style="background-color: #F0FFF0; padding: 20px; border-radius: 10px; margin: 20px 0;">
                    <p><strong>اسم المستخدم:</strong> {username}</p>
                    <p><strong>البريد الإلكتروني:</strong> {user_data.get('email', '')}</p>
                    <p><strong>تاريخ التسجيل:</strong> {user_data.get('created_at', '').split('T')[0] if user_data.get('created_at') else ''}</p>
                </div>
            """)
        else:
            put_markdown("### لم يتم العثور على المريض")
            
    except Exception as e:
        print(f"Error in view_patient_profile: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض ملف المريض")
        view_patients()   
def edit_doctor_profile(username):
    """تعديل الملف الشخصي للطبيب."""
    add_global_style() 
    clear()
    add_back_button()
    
    try:
        
        users = db.child("users").get()
        user_data = None
        user_key = None
        
        if users:
            for user in users.each():
                if user.val().get('username') == username:
                    user_data = user.val()
                    user_key = user.key()
                    break
        
        if not user_data:
            popup("خطأ", "لم يتم العثور على بيانات الطبيب")
            return show_doctor_screen()

       
        updated_data = input_group("تعديل الملف الشخصي", [
            
            input('الاسم', name='name', value=user_data.get('name', '')),
            input('البريد الإلكتروني', name='email', value=user_data.get('email', '')),
            input('رقم الهاتف', name='phone', value=user_data.get('phone', '')),
            
           
            select('التخصص', name='specialty', options=[
                'طب نفسي', 'علاج نفسي', 'إرشاد نفسي', 'طب نفسي للأطفال'
            ], value=user_data.get('specialty', '')),
            input('رقم الترخيص المهني', name='license_number', value=user_data.get('license_number', '')),
            input('المؤهلات العلمية', name='education', value=user_data.get('education', '')),
            input('الخبرات السابقة', name='experience', value=user_data.get('experience', '')),
            
           
            select('المحافظة', name='governorate', options=[
            'القاهرة',
            'الجيزة',
            'القليوبية',
            'الإسكندرية',
            'البحيرة',
            'مطروح',
            'دمياط',
            'الدقهلية',
            'كفر الشيخ',
            'الغربية',
            'المنوفية',
            'الشرقية',
            'بورسعيد',
            'الإسماعيلية',
            'السويس',
            'شمال سيناء',
            'جنوب سيناء',
            'بني سويف',
            'الفيوم',
            'المنيا',
            'أسيوط',
            'الوادي الجديد',
            'البحر الأحمر',
            'سوهاج',
            'قنا',
            'الأقصر',
            'أسوان'], value=user_data.get('governorate', '')),
            input('عنوان العيادة', name='clinic_address', value=user_data.get('clinic_address', '')),
            input('رسوم الكشف', name='fees', type=NUMBER, value=user_data.get('fees', 0)),
            input('مدة الجلسة (بالدقائق)', name='session_duration', type=NUMBER, value=user_data.get('session_duration', 30)),
            input('مواعيد العمل', name='working_hours', 
                  value=user_data.get('working_hours', ''),
                  placeholder='مثال: السبت - الخميس: 2 مساءً - 9 مساءً'),
            input('نبذة عن الطبيب', name='bio', value=user_data.get('bio', ''),
                  placeholder='اكتب نبذة مختصرة عن خبراتك وتخصصك...')
        ])

        if updated_data:
           
            updated_data.update({
                'username': username,
                'role': 'doctor',
                'password': user_data.get('password'),
                'approved': user_data.get('approved', True)
            })
            
           
            db.child("users").child(user_key).set(updated_data)
            popup("تم", "تم تحديث البيانات بنجاح")
            
        show_doctor_screen()

    except Exception as e:
        print(f"Error editing doctor profile: {str(e)}")
        popup("خطأ", "حدث خطأ في تعديل البيانات")
        show_doctor_screen()

def view_appointment_requests():
    """عرض طلبات المواعيد الجديدة."""
    add_global_style() 
    clear()
    add_back_button()
    
    put_markdown("# طلبات المواعيد الجديدة")
    
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        requests = db.child("appointment_requests").child(current_doctor).get()
        
        if requests and requests.val():
            requests_data = []
            for req in requests.each():
                data = req.val()
                if data and data.get('status') == 'pending':
                    requests_data.append([
                        data.get('patient_username', ''),
                        data.get('requested_date', ''),
                        data.get('requested_time', ''),
                        data.get('notes', ''),
                        put_button('قبول', onclick=lambda r=req.key(): approve_appointment_request(r)),
                        put_button('رفض', onclick=lambda r=req.key(): reject_appointment_request(r))
                    ])
            
            if requests_data:
                put_table(
                    requests_data,
                    header=['المريض', 'التاريخ المطلوب', 'الوقت المطلوب', 'ملاحظات', '', '']
                )
            else:
                put_text("لا توجد طلبات مواعيد جديدة")
        else:
            put_text("لا توجد طلبات مواعيد جديدة")
            
    except Exception as e:
        print(f"Error in view_appointment_requests: {str(e)}")
        popup("خطأ", "فشل تحميل طلبات المواعيد")
        show_doctor_screen()

def approve_appointment_request(request_id):
    """قبول طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
      
        request = db.child("appointment_requests").child(current_doctor).child(request_id).get().val()
        
        if request:
            
            db.child("appointments").child(current_doctor).push({
                'patient_username': request.get('patient_username'),
                'date': request.get('requested_date'),
                'time': request.get('requested_time'),
                'status': 'مجدول',
                'created_at': datetime.now().isoformat()
            })
            
           
            db.child("appointment_requests").child(current_doctor).child(request_id).update({
                'status': 'approved'
            })
            
            popup("تم", "تم قبول طلب الموعد وإضافته للجدول")
        
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in approve_appointment_request: {str(e)}")
        popup("خطأ", "فشل قبول طلب الموعد")
        view_appointment_requests()

def reject_appointment_request(request_id):
    """رفض طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        db.child("appointment_requests").child(current_doctor).child(request_id).update({
            'status': 'rejected'
        })
        
        popup("تم", "تم رفض طلب الموعد")
        view_appointment_requests()
    
    except Exception as e:
        print(f"Error in reject_appointment_request: {str(e)}")
        popup("خطأ", "فشل رفض طلب الموعد")
        view_appointment_requests()

def approve_appointment_request(request_id):
    """قبول طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        request = db.child("appointment_requests").child(current_doctor).child(request_id).get().val()
        
        if request:
            
            db.child("appointments").child(current_doctor).push({
                'patient_username': request.get('patient_username'),
                'date': request.get('requested_date'),
                'time': request.get('requested_time'),
                'status': 'مجدول',
                'created_at': datetime.now().isoformat()
            })
            
           
            db.child("appointment_requests").child(current_doctor).child(request_id).update({
                'status': 'approved'
            })
            
            popup("تم", "تم قبول طلب الموعد وإضافته للجدول")
        
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in approve_appointment_request: {str(e)}")
        popup("خطأ", "فشل قبول طلب الموعد")
        view_appointment_requests()

def reject_appointment_request(request_id):
    """رفض طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
      
        db.child("appointment_requests").child(current_doctor).child(request_id).update({
            'status': 'rejected'
        })
        
        popup("تم", "تم رفض طلب الموعد")
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in reject_appointment_request: {str(e)}")
        popup("خطأ", "فشل رفض طلب الموعد")
        view_appointment_requests()
def get_emotion_name(emotion_type):
    """Get Arabic name for emotion type."""
    emotion_names = {
        "sadness": "الحزن",
        "anger": "الغضب",
        "stress": "التوتر",
        "negative_thoughts": "الأفكار السلبية",
        "guilt":"الذنب"

    }
    return emotion_names.get(emotion_type, emotion_type)
def approve_appointment_request(request_id):
    """قبول طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        request = db.child("appointment_requests").child(current_doctor).child(request_id).get().val()
        
        if request:
           
            db.child("appointments").child(current_doctor).push({
                'patient_username': request.get('patient_username'),
                'date': request.get('requested_date'),
                'time': request.get('requested_time'),
                'status': 'مجدول',
                'created_at': datetime.now().isoformat()
            })
            
           
            db.child("appointment_requests").child(current_doctor).child(request_id).update({
                'status': 'approved'
            })
            
            popup("تم", "تم قبول طلب الموعد وإضافته للجدول")
        
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in approve_appointment_request: {str(e)}")
        popup("خطأ", "فشل قبول طلب الموعد")
        view_appointment_requests()

def reject_appointment_request(request_id):
    """رفض طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
        db.child("appointment_requests").child(current_doctor).child(request_id).update({
            'status': 'rejected'
        })
        
        popup("تم", "تم رفض طلب الموعد")
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in reject_appointment_request: {str(e)}")
        popup("خطأ", "فشل رفض طلب الموعد")
        view_appointment_requests()
def reject_appointment_request(request_id):
    """رفض طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        db.child("appointment_requests").child(current_doctor).child(request_id).update({
            'status': 'rejected'
        })
        
        popup("تم", "تم رفض طلب الموعد")
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in reject_appointment_request: {str(e)}")
        popup("خطأ", "فشل رفض طلب الموعد")
        view_appointment_requests()


def request_new_appointment():
    """طلب موعد جديد."""
    clear()
    try:
        if not hasattr(session_storage, 'user'):
            popup("خطأ", "الرجاء تسجيل الدخول أولاً")
            return show_login_screen()

        username = session_storage.user
        put_markdown("# طلب موعد جديد")

       
        doctors = []
        doctors_ref = db.child("users").get()
        if doctors_ref:
            for doc in doctors_ref.each():
                doc_data = doc.val()
                if doc_data.get('role') == 'doctor' and doc_data.get('approved', False):
                    doctors.append({
                        'id': doc.key(),
                        'name': doc_data.get('username', 'طبيب غير معروف')
                    })

        if not doctors:
            popup("تنبيه", "لا يوجد أطباء متاحين حالياً")
            return view_appointments()

       
        data = input_group("طلب موعد جديد", [
            select('اختر الطبيب', [{'label': d['name'], 'value': d['id']} for d in doctors], name='doctor'),
            input('التاريخ المطلوب', type=DATE, name='date'),
            input('الوقت المطلوب', type=TIME, name='time'),
            textarea('ملاحظات', name='notes', placeholder='أي ملاحظات إضافية؟')
        ])

        if data:
           
            appointment_data = {
                'patient_username': username,
                'date': data['date'],
                'time': data['time'],
                'notes': data['notes'],
                'status': 'معلق',
                'created_at': datetime.now().isoformat()
            }

            db.child("appointments").child(data['doctor']).push(appointment_data)
            popup("تم", "تم إرسال طلب الموعد بنجاح")
            return view_appointments()

    except Exception as e:
        print(f"Request appointment error: {str(e)}")
        popup("خطأ", "حدث خطأ في طلب الموعد")
        return view_appointments()
def search_doctors():
    """البحث عن الأطباء المتاحين."""
    add_global_style()
    clear()
    add_back_button()
    
    put_markdown("# البحث عن طبيب")
    
    try:
        
        users = db.child("users").get()
        doctors = []
        if users:
            for user in users.each():
                user_data = user.val()
                if user_data.get('role') == 'doctor' and user_data.get('approved', False):
                    doctors.append(user_data)

        
        put_input('search_query', type=TEXT, placeholder='ابحث باسم الطبيب أو التخصص أو المحافظة')
        
       
        def display_doctors(filtered_doctors=None):
            doctors_to_display = filtered_doctors if filtered_doctors is not None else doctors
            clear('doctors_list') 
            
            with use_scope('doctors_list'):
                if not doctors_to_display:
                    put_text("لا يوجد أطباء متطابقين مع البحث")
                    return
                
                for doctor in doctors_to_display:
                    put_grid([
                        [
        put_markdown(f"""
                            ### د. {doctor.get('name', doctor.get('username', ''))}
                            **التخصص:** {doctor.get('specialty', 'غير محدد')}
                            **المحافظة:** {doctor.get('governorate', 'غير محدد')}
                            """),
                            put_column([
                                put_button('عرض الملف الشخصي', 
                                         onclick=lambda d=doctor: view_doctor_profile(d.get('username')),
                                         color='info'),
                                put_button('طلب موعد',
                                         onclick=lambda d=doctor: request_appointment(d.get('username')),
                                         color='primary')
                            ])
                        ]
                    ], cell_width='auto auto')
                    put_markdown('---')

       
        def on_search(query):
            if not query:
                display_doctors()
                return
            
            query = query.lower()
            filtered = [d for d in doctors if 
                       query in d.get('name', '').lower() or
                       query in d.get('specialty', '').lower() or
                       query in d.get('governorate', '').lower()]
            display_doctors(filtered)

         
        display_doctors()
        
        
        while True:
            query = pin_wait_change('search_query')
            on_search(query['value'])
            
    except Exception as e:
        print(f"Error in search_doctors: {str(e)}")
        popup("خطأ", "حدث خطأ في البحث")
        show_patient_screen()
def view_doctor_profile(doctor_username):
    """عرض الملف الشخصي للطبيب."""
    add_global_style()
    clear()
    add_back_button()
    
    try:
      
        users = db.child("users").get()
        doctor_data = None
        
        if users:
            for user in users.each():
                if user.val().get('username') == doctor_username:
                    doctor_data = user.val()
                    break
        
        if not doctor_data:
            popup("خطأ", "لم يتم العثور على بيانات الطبيب")
            return search_doctors()

       
        put_markdown(f"""
        # د. {doctor_data.get('name', doctor_data.get('username', ''))}
        
        ### المعلومات المهنية
        - **التخصص:** {doctor_data.get('specialty', 'غير محدد')}
        - **رقم الترخيص:** {doctor_data.get('license_number', 'غير محدد')}
        - **المؤهلات العلمية:** {doctor_data.get('education', 'غير محدد')}
        - **الخبرات:** {doctor_data.get('experience', 'غير محدد')}
        
        ### معلومات العيادة
        - **المحافظة:** {doctor_data.get('governorate', 'غير محدد')}
        - **العنوان:** {doctor_data.get('clinic_address', 'غير محدد')}
        - **رسوم الكشف:** {doctor_data.get('fees', 'غير محدد')} جنيه
        - **مدة الجلسة:** {doctor_data.get('session_duration', 'غير محدد')} دقيقة
        - **مواعيد العمل:** {doctor_data.get('working_hours', 'غير محدد')}
        
        ### نبذة عن الطبيب
        {doctor_data.get('bio', 'لا توجد نبذة متاحة')}
        """)
        
        
        put_button('تواصل مع الطبيب', 
                  onclick=lambda: start_chat(doctor_username),
                  color='primary')
        put_button('طلب موعد', 
                  onclick=lambda: request_appointment(doctor_username),
                  color='success')
                  
    except Exception as e:
        print(f"Error in view_doctor_profile: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض الملف الشخصي")
        search_doctors()
def request_appointment(doctor_username):
    """طلب موعد مع الطبيب."""
    add_global_style()
    clear()
    add_back_button()
      
    put_markdown("# طلب موعد جديد")
    
    try:
        from pywebio.session import local as session_storage
        patient_username = session_storage.user
        
       
        appointment_info = input_group("تفاصيل الموعد", [
            input('التاريخ المطلوب', name='requested_date', type=DATE),
            input('الوقت المطلوب', name='requested_time', type=TIME),
            textarea('ملاحظات إضافية', name='notes', placeholder='أي معلومات إضافية تريد إخبار الطبيب بها')
        ])
        
        if appointment_info:
           
            db.child("appointment_requests").child(doctor_username).push({
                'patient_username': patient_username,
                'requested_date': appointment_info['requested_date'],
                'requested_time': appointment_info['requested_time'],
                'notes': appointment_info['notes'],
                'status': 'pending',
                'created_at': datetime.now().isoformat()
            })
            
            popup("تم", "تم إرسال طلب الموعد بنجاح")
            view_doctor_profile(doctor_username)
            
    except Exception as e:
        print(f"Error in request_appointment: {str(e)}")
        popup("خطأ", "فشل في طلب الموعد")
        view_doctor_profile(doctor_username)

def show_doctor_patients():
    """عرض قائمة مرضى الطبيب."""
    add_global_style()  
    clear()
    add_back_button()
    
    put_markdown("# قائمة المرضى")
    
    try:
        doctor_username = session_storage.user
        
       
        put_button('➕ إضافة مريض جديد', onclick=add_new_patient)
        
       
        doctor_patients = db.child("doctor_patients").child(doctor_username).get().val()
        
        if doctor_patients:
            patients_data = []
            users = db.child("users").get().val()
            
            if users:
                for dp_key, dp_value in doctor_patients.items():
                    patient_username = dp_value.get('patient_username')
                    for user_key, user_data in users.items():
                        if user_data.get('username') == patient_username:
                            patients_data.append({
                                'key': user_key,
                                'data': user_data
                            })
            
            if patients_data:
                for patient in patients_data:
                    with put_collapse(f"👤 {patient['data'].get('username')}"):
                       
                        put_table([
                            ['البريد الإلكتروني', patient['data'].get('email', '')],
                            ['تاريخ الإضافة', patient['data'].get('created_at', '')]
                        ])
                        
                        put_row([
                            put_button('السجل الطبي', 
                                     onclick=lambda p=patient: view_history(p['data']['username']),
                                     color='info'),
                            put_button('إرسال رسالة',
                                     onclick=lambda p=patient: start_chat(p['data']['username']),
                                     color='primary')
                        ])
        else:
                put_markdown("_لا يوجد مرضى_")
            
    except Exception as e:
        print(f"Show patients error: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض قائمة المرضى")

def cancel_patient_appointment(appointment_id, doctor_id):
    """إلغاء موعد من قبل المريض."""
    try:
        if actions("هل أنت متأكد من إلغاء هذا الموعد؟", ["نعم", "لا"]) == "نعم":
            db.child("appointments").child(doctor_id).child(appointment_id).update({
                'status': 'cancelled'
            })
            popup("تم", "تم إلغاء الموعد بنجاح")
            show_patient_appointments()
    except Exception as e:
        print(f"Error cancelling appointment: {str(e)}")
        popup("خطأ", "حدث خطأ في إلغاء الموعد")
def approve_appointment_request(request_id):
    """قبول طلب الموعد."""
    try:
        from pywebio.session import local as session_storage
        current_doctor = session_storage.user
        
       
        request = db.child("appointment_requests").child(current_doctor).child(request_id).get().val()
        
        if request:
            
            appointment_data = {
                'patient_username': request.get('patient_username'),
                'date': request.get('requested_date'),
                'time': request.get('requested_time'),
                'status': 'approved',  
                'created_at': datetime.now().isoformat()
            }
            
           
            db.child("appointments").child(current_doctor).push(appointment_data)
            
           
            db.child("appointment_requests").child(current_doctor).child(request_id).update({
                'status': 'approved'
            })
            
            popup("تم", "تم قبول طلب الموعد وإضافته للجدول")
        
        view_appointment_requests()
        
    except Exception as e:
        print(f"Error in approve_appointment_request: {str(e)}")
        popup("خطأ", "فشل قبول طلب الموعد")
        view_appointment_requests()
def get_appointment_status_arabic(status):
    """ترجمة حالة الموعد للعربية."""
    status_dict = {
        'pending': 'قيد الانتظار',
        'approved': 'تم التأكيد',
        'completed': 'مكتمل',
        'cancelled': 'ملغي',
        'scheduled': 'مجدول'
    }
    return status_dict.get(status, status)
         
def edit_patient_profile(username, role):
    """تعديل الملف الشخصي للمريض."""
    
    clear()
    add_global_style() 
    put_button("🔙 العودة للصفحة الرئيسية", onclick=lambda: (clear(), show_patient_screen()))
    
    try:
       
        users = db.child("users").get()
        user_data = None
        user_key = None
        
        if users:
            for user in users.each():
                if user.val().get('username') == username:
                    user_data = user.val()
                    user_key = user.key()
                    break
        
        if not user_data:
            popup("خطأ", "لم يتم العثور على بيانات المستخدم")
            return show_patient_screen()

       
        governorates = [
            'القاهرة',
            'الجيزة',
            'القليوبية',
            'الإسكندرية',
            'البحيرة',
            'مطروح',
            'دمياط',
            'الدقهلية',
            'كفر الشيخ',
            'الغربية',
            'المنوفية',
            'الشرقية',
            'بورسعيد',
            'الإسماعيلية',
            'السويس',
            'شمال سيناء',
            'جنوب سيناء',
            'بني سويف',
            'الفيوم',
            'المنيا',
            'أسيوط',
            'الوادي الجديد',
            'البحر الأحمر',
            'سوهاج',
            'قنا',
            'الأقصر',
            'أسوان'
        ]

       
        updated_data = input_group("تعديل الملف الشخصي", [
            input('الاسم', name='name', value=user_data.get('name', '')),
            input('البريد الإلكتروني', name='email', value=user_data.get('email', '')),
            input('رقم الهاتف', name='phone', value=user_data.get('phone', '')),
            select('المحافظة', name='governorate', 
                  options=governorates,
                  value=user_data.get('governorate', '')),
            input('العمر', name='age', type=NUMBER, value=user_data.get('age', '')),
            textarea('نبذة شخصية', name='bio', value=user_data.get('bio', ''))
        ])

        if updated_data:
             
            updated_data.update({
                'username': username,
                'role': 'patient',
                'password': user_data.get('password')
            })
            
           
            db.child("users").child(user_key).set(updated_data)
            popup("تم", "تم تحديث البيانات بنجاح")

        clear()    
        show_patient_screen()
        
    except Exception as e:
        print(f"Error editing patient profile: {str(e)}")
        popup("خطأ", "حدث خطأ في تعديل البيانات")
        show_patient_screen()


def check_session_status():
    """Enhanced session checking."""
    username = session_storage.user
    if not username:
        popup("تنبيه", "يرجى تسجيل الدخول")
        show_login_screen()
        return False
    
    if session_manager.is_session_expired():
        popup("تنبيه", "انتهت الجلسة")
        handle_logout()
        return False
        
    session_manager.update_last_activity()
    return True 
def show_patient_appointments():
    """عرض مواعيد المريض."""
    add_global_style() 
    clear()
    add_back_button()
    
    put_markdown("# مواعيدي")
    
    try:
        current_user = session_storage.user
        
       
        appointments = db.child("appointments").get()
        
        if appointments and appointments.val():
            appointments_found = False
            appointments_list = []
            
           
            for doctor_appointments in appointments.each():
                doctor_id = doctor_appointments.key()
                doctor_data = doctor_appointments.val()
                
                if isinstance(doctor_data, dict):
                    for appointment_id, apt_data in doctor_data.items():
                        if isinstance(apt_data, dict) and apt_data.get('patient_username') == current_user:
                            appointments_found = True
                            appointments_list.append({
                                'doctor_id': doctor_id,
                                'appointment_id': appointment_id,
                                'date': apt_data.get('date', ''),
                                'time': apt_data.get('time', ''),
                                'status': apt_data.get('status', 'مجدول')
                            })
            
            if appointments_found:
                 
                appointments_list.sort(key=lambda x: x['date'])
                
               
                for apt in appointments_list:
                    put_html(f"""
                        <div class="card">
                            <h3>موعد مع د. {apt['doctor_id']}</h3>
                            <p>التاريخ: {apt['date']}</p>
                            <p>الوقت: {apt['time']}</p>
                            <p>الحالة: {apt['status']}</p>
                        </div>
                    """)
                    
                   
                    put_row([
                        put_button('إلغاء الموعد', 
                                 onclick=lambda a=apt['appointment_id'], d=apt['doctor_id']: 
                                     cancel_patient_appointment(a, d),
                                 color='danger'),
                        put_button('مراسلة الطبيب',
                                 onclick=lambda d=apt['doctor_id']: 
                                     start_chat(d),  
                                 color='success')
                    ])
        
            else:
                put_text("لا توجد مواعيد مسجلة")
        else:
            put_text("لا توجد مواعيد مسجلة")
            
    except Exception as e:
        print(f"Error showing patient appointments: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض المواعيد")
        show_patient_screen()
def send_message():
    """عرض واجهة المحادثات."""
    add_global_style() 
    clear()
    add_back_button()
    
    put_markdown("# المحادثات")
    
    try:
        current_user = session_storage.user
        current_role = session_storage.role
        
        if current_role == 'patient':
          
            appointments = db.child("appointments").get()
            doctors_list = set()
            
            if appointments:
                for doctor_appointments in appointments.each():
                    doctor_id = doctor_appointments.key()
                    doctor_data = doctor_appointments.val()
                    
                    if isinstance(doctor_data, dict):
                        for apt in doctor_data.values():
                            if isinstance(apt, dict) and apt.get('patient_username') == current_user:
                                doctors_list.add(doctor_id)
            
            if doctors_list:
                for doctor_id in doctors_list:
                    doctor_info = get_user_info(doctor_id)
                    put_button(f"د. {doctor_info['name']}", 
                             onclick=lambda d=doctor_id: start_chat(d),
                             color='success')
            else:
                put_text("لا يوجد أطباء متابعين لحالتك حالياً")
                put_button('البحث عن طبيب', 
                          onclick=search_doctors,
                          color='success')
                
        elif current_role == 'doctor':
          
            appointments = db.child("appointments").child(current_user).get()
            patients_list = set()
            
            if appointments:
                for apt in appointments.val().values():
                    if isinstance(apt, dict):
                        patient_username = apt.get('patient_username')
                        if patient_username:
                            patients_list.add(patient_username)
            
            if patients_list:
                for patient_id in patients_list:
                    patient_info = get_user_info(patient_id)
                    put_button(patient_info['name'], 
                             onclick=lambda p=patient_id: start_chat(p),
                             color='success')
            else:
                put_text("لا يوجد مرضى مسجلين في قائمتك حالياً")
                
    except Exception as e:
        print(f"Error in messages screen: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض المحادثات")

def start_chat(other_user):
    """بدء محادثة مع مستخدم."""
    add_global_style()
    clear()
    add_back_button()
    
    try:
        current_user = session_storage.user
        chat_id = get_chat_id(current_user, other_user)
        
       
        user_info = get_user_info(other_user)
        display_name = f"د. {user_info['name']}" if user_info['role'] == 'doctor' else user_info['name']
        
        put_markdown(f"# محادثة مع {display_name}")
        
       
        put_scope('messages')
        display_messages(chat_id)
        
       
        with use_scope('message_input', clear=True):
            put_input('message', placeholder='اكتب رسالتك هنا')
            put_button('إرسال', 
                      onclick=lambda: send_new_message(chat_id, other_user),
                      color='success')
            
    except Exception as e:
        print(f"Error in start chat: {str(e)}")
        popup("خطأ", "حدث خطأ في فتح المحادثة")
        send_message()

def send_new_message(chat_id, receiver):
    """إرسال رسالة جديدة."""
    try:
        message = pin.message.strip()
        if message:
            current_user = session_storage.user
            
          
            db.child("chats").child(chat_id).push({
                'sender': current_user,
                'receiver': receiver,
                'text': message,
                'timestamp': datetime.now().isoformat(),
                'read': False
            })
            
           
            pin.message = '' 
            display_messages(chat_id) 
            
           
            with use_scope('message_input', clear=True):
                put_input('message', placeholder='اكتب رسالتك هنا')
                put_button('إرسال', onclick=lambda: send_new_message(chat_id, receiver))
            
    except Exception as e:
        print(f"Error sending message: {str(e)}")
        popup("خطأ", "حدث خطأ في إرسال الرسالة")
def get_user_info(username):
    """جلب معلومات المستخدم."""
    try:
        users = db.child("users").get()
        if users:
            for user in users.each():
                user_data = user.val()
                if isinstance(user_data, dict) and user_data.get('username') == username:
                    return {
                        'name': user_data.get('name', username),
                        'role': user_data.get('role', 'patient')
                    }
        return {'name': username, 'role': 'patient'}
    except Exception as e:
        print(f"Error getting user info: {str(e)}")
        return {'name': username, 'role': 'patient'}

def get_chat_id(user1, user2):
    """إنشاء معرف موحد للمحادثة."""
    users = sorted([user1, user2])
    return f"{users[0]}_{users[1]}"
def display_messages(chat_id):
    """عرض رسائل المحادثة."""
    try:
        current_user = session_storage.user
        messages = db.child("chats").child(chat_id).get()
        
        with use_scope('messages', clear=True):
            if messages and messages.val():
                messages_list = []
                for msg in messages.each():
                    msg_data = msg.val()
                    if isinstance(msg_data, dict):
                        messages_list.append(msg_data)
                
               
                messages_list.sort(key=lambda x: x.get('timestamp', ''))
                
                for msg in messages_list:
                    is_current_user = msg.get('sender') == current_user
                    
                    
                    if is_current_user:
                       
                        put_html(f"""
                            <div style="margin: 5px 0; padding: 10px; border-radius: 15px; 
                                      background-color: #B0FFB0; color: black;
                                      text-align: right; margin-left: 20%;
                                      box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                <p style="margin: 5px 0;">{msg.get('text', '')}</p>
                                <small style="color: #666;">{format_timestamp(msg.get('timestamp', ''))}</small>
                            </div>
                        """)
                    else:
                        
                        put_html(f"""
                            <div style="margin: 5px 0; padding: 10px; border-radius: 15px;
                                      background-color: #F0FFF0; color: black;
                                      text-align: left; margin-right: 20%;
                                      box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                                <strong style="color: #666;">{msg.get('sender')}</strong>
                                <p style="margin: 5px 0;">{msg.get('text', '')}</p>
                                <small style="color: #666;">{format_timestamp(msg.get('timestamp', ''))}</small>
                            </div>
                        """)
            else:
                put_text("لا توجد رسائل")
                
    except Exception as e:
        print(f"Error displaying messages: {str(e)}")
        put_text("حدث خطأ في عرض الرسائل")
def format_timestamp(timestamp):
    """تنسيق الوقت."""
    try:
        dt = datetime.fromisoformat(timestamp)
        return dt.strftime("%I:%M %p")
    except:
        return timestamp
def show_settings():
    """عرض إعدادات المستخدم."""
    clear()
    add_back_button()
    add_global_style()
    
    try:
        current_user = session_storage.user
        user_settings = db.child("user_settings").child(current_user).get().val() or {}
        
        put_markdown("# الإعدادات")
        
       
        checkbox("تفعيل الإشعارات", 
                name='notifications',
                options=[{'label': 'تفعيل', 'value': True}],
                value=[True] if user_settings.get('notifications', True) else [])
        
       
        put_button("حفظ الإعدادات", onclick=lambda: save_settings(), color='success')
        
    except Exception as e:
        print(f"Error in settings: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض الإعدادات")

def save_settings():
    """حفظ إعدادات المستخدم."""
    try:
        current_user = session_storage.user
        
       
        data = {
            'notifications': True if pin.notifications else False,
            'updated_at': datetime.now().isoformat()
        }
        
       
        db.child("user_settings").child(current_user).update(data)
        
        popup("تم", "تم حفظ الإعدادات بنجاح")
        
       
        show_settings()
        
    except Exception as e:
        print(f"Error saving settings: {str(e)}")
        popup("خطأ", "حدث خطأ في حفظ الإعدادات")
def show_admin_screen():
    """عرض الشاشة الرئيسية للمشرف."""
    clear()
    add_global_style()
    
    try:
        if not hasattr(session_storage, 'user') or session_storage.role != 'admin':
            popup("خطأ", "غير مصرح بالدخول")
            return show_login_screen()
        
        put_html("""
            <style>
                .admin-container { max-width: 1200px; margin: 0 auto; padding: 20px; }
                .admin-card {
                    background: #f8fff8;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 15px 0;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }
                .stats-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                    gap: 15px;
                    margin: 15px 0;
                }
                .stat-card {
                    background: white;
                    padding: 15px;
                    border-radius: 8px;
                    text-align: center;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.05);
                }
            </style>
        """)

       
        put_markdown("# 👨‍💼 لوحة تحكم المشرف").style('text-align: center; color: #2E7D32;')

        
        put_html('<div class="admin-card">')
        put_markdown("### 📊 إحصائيات النظام")
        stats = get_system_stats()
        put_html(f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>المستخدمين</h4>
                    <p style="font-size: 24px; color: #2E7D32;">{stats['total_users']}</p>
                </div>
                <div class="stat-card">
                    <h4>الأطباء</h4>
                    <p style="font-size: 24px; color: #2E7D32;">{stats['total_doctors']}</p>
                </div>
                <div class="stat-card">
                    <h4>المرضى</h4>
                    <p style="font-size: 24px; color: #2E7D32;">{stats['total_patients']}</p>
                </div>
                <div class="stat-card">
                    <h4>المواعيد</h4>
                    <p style="font-size: 24px; color: #2E7D32;">{stats['total_appointments']}</p>
                </div>
            </div>
        """)
        put_html('</div>')

        
       
        put_html('<div class="admin-card">')
        put_markdown("### 📝 إدارة المحتوى")
        put_buttons([
            {'label': 'المقالات والنصائح', 'value': 'articles', 'color': 'success'},
            {'label': 'التقييمات النفسية', 'value': 'assessments', 'color': 'success'},
            {'label': 'التحديات اليومية', 'value': 'challenges', 'color': 'success'}
        ], onclick=handle_content_management)
        put_html('</div>')

        
        put_html('<div class="admin-card">')
        put_markdown("### 📈 التقارير والتحليلات")
        put_buttons([
            {'label': 'تقارير النشاط', 'value': 'activity', 'color': 'info'},
            {'label': 'تقارير المواعيد', 'value': 'appointments', 'color': 'info'},
            {'label': 'تحليل البيانات', 'value': 'analytics', 'color': 'info'}
        ], onclick=handle_reports)
        put_html('</div>')

         
        put_html('<div class="admin-card">')
        put_markdown("### ⚙️ إعدادات النظام")
        put_buttons([
            {'label': 'إعدادات عامة', 'value': 'general', 'color': 'secondary'},
            {'label': 'النسخ الاحتياطي', 'value': 'backup', 'color': 'secondary'},
            {'label': 'سجل النظام', 'value': 'logs', 'color': 'secondary'}
        ], onclick=handle_system_settings)
        put_html('</div>')

         
        put_button('🚪 تسجيل الخروج', onclick=handle_logout, color='danger')

    except Exception as e:
        print(f"Admin screen error: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض لوحة التحكم")
        show_login_screen()


def manage_doctors():
    """إدارة الأطباء."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# إدارة الأطباء")
    
    try:
        
        pending_doctors = get_pending_doctors()
        if pending_doctors:
            put_markdown("## طلبات الانضمام الجديدة")
            for doctor in pending_doctors:
                put_html(f"""
                    <div class="admin-card">
                        <h4>د. {doctor.get('name', '')}</h4>
                        <p><strong>التخصص:</strong> {doctor.get('specialty', '')}</p>
                        <p><strong>رقم الترخيص:</strong> {doctor.get('license_number', '')}</p>
                    </div>
                """)
                put_buttons([
                    {'label': 'قبول', 'value': ('approve', doctor['username']), 'color': 'success'},
                    {'label': 'رفض', 'value': ('reject', doctor['username']), 'color': 'danger'}
                ], onclick=handle_doctor_approval)

        approved_doctors = get_approved_doctors()
        if approved_doctors:
            put_markdown("## الأطباء المعتمدون")
            for doctor in approved_doctors:
                put_html(f"""
                    <div class="admin-card">
                        <h4>د. {doctor.get('name', '')}</h4>
                        <p><strong>التخصص:</strong> {doctor.get('specialty', '')}</p>
                        <p><strong>الحالة:</strong> {doctor.get('status', 'نشط')}</p>
                    </div>
                """)
                put_buttons([
                    {'label': 'تعليق الحساب', 'value': ('suspend', doctor['username']), 'color': 'warning'},
                    {'label': 'حذف', 'value': ('delete', doctor['username']), 'color': 'danger'}
                ], onclick=handle_doctor_management)

    except Exception as e:
        print(f"Error managing doctors: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة الأطباء")
        show_admin_screen()

def get_pending_doctors():
    """جلب قائمة الأطباء المنتظرين للموافقة."""
    try:
        pending_doctors = []
        users = db.child("users").get()
        if users:
            for user in users.each():
                user_data = user.val()
                if (user_data.get('role') == 'doctor' and 
                    not user_data.get('approved', False)):
                    user_data['username'] = user.key()
                    pending_doctors.append(user_data)
        return pending_doctors
    except Exception as e:
        print(f"Error getting pending doctors: {str(e)}")
        return []

def get_approved_doctors():
    """جلب قائمة الأطباء المعتمدين."""
    try:
        approved_doctors = []
        users = db.child("users").get()
        if users:
            for user in users.each():
                user_data = user.val()
                if (user_data.get('role') == 'doctor' and 
                    user_data.get('approved', False)):
                    user_data['username'] = user.key()
                    approved_doctors.append(user_data)
        return approved_doctors
    except Exception as e:
        print(f"Error getting approved doctors: {str(e)}")
        return []

def handle_doctor_approval(action):
    """معالجة الموافقة على الأطباء."""
    action_type, doctor_username = action
    try:
        if action_type == 'approve':
            db.child("users").child(doctor_username).update({'approved': True})
            popup("تم", "تمت الموافقة على الطبيب بنجاح")
        elif action_type == 'reject':
            
            send_notification(doctor_username, 
                            "تم رفض طلب انضمامك",
                            "نأسف لإبلاغك برفض طلب انضمامك للمنصة")
            db.child("users").child(doctor_username).remove()
            popup("تم", "تم رفض الطبيب وحذف بياناته")
        manage_doctors()  
    except Exception as e:
        print(f"Error in doctor approval: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الطلب")

def handle_doctor_management(action):
    """معالجة إدارة الأطباء المعتمدين."""
    action_type, doctor_username = action
    try:
        if action_type == 'suspend':
            db.child("users").child(doctor_username).update({'status': 'suspended'})
            send_notification(doctor_username, 
                            "تم تعليق حسابك",
                            "تم تعليق حسابك مؤقتاً. يرجى التواصل مع الإدارة")
            popup("تم", "تم تعليق حساب الطبيب")
        elif action_type == 'delete':
            if actions("هل أنت متأكد من حذف هذا الطبيب؟", ["نعم", "لا"]) == "نعم":
               
                delete_doctor_data(doctor_username)
                popup("تم", "تم حذف الطبيب وجميع بياناته")
        manage_doctors() 
    except Exception as e:
        print(f"Error in doctor management: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة الطبيب")

def delete_doctor_data(doctor_username):
    """حذف جميع بيانات الطبيب."""
    try:
       
        db.child("users").child(doctor_username).remove()
        
        db.child("appointments").child(doctor_username).remove()
        
        chats = db.child("chats").get()
        if chats:
            for chat in chats.each():
                chat_data = chat.val()
                if doctor_username in chat.key():
                    db.child("chats").child(chat.key()).remove()
    except Exception as e:
        print(f"Error deleting doctor data: {str(e)}")
        raise e

def send_notification(username, title, message):
    """إرسال إشعار للمستخدم."""
    try:
        db.child("notifications").child(username).push({
            'title': title,
            'message': message,
            'timestamp': datetime.now().isoformat(),
            'read': False
        })
    except Exception as e:
        print(f"Error sending notification: {str(e)}")
def get_system_stats():
    """جلب إحصائيات النظام."""
    try:
        stats = {
            'total_users': 0,
            'total_doctors': 0,
            'total_patients': 0,
            'total_appointments': 0
        }
        
       
        users = db.child("users").get()
        if users:
            for user in users.each():
                user_data = user.val()
                stats['total_users'] += 1
                
                if user_data.get('role') == 'doctor':
                    stats['total_doctors'] += 1
                elif user_data.get('role') == 'patient':
                    stats['total_patients'] += 1
        
       
        appointments = db.child("appointments").get()
        if appointments:
            for doctor_appointments in appointments.each():
                if isinstance(doctor_appointments.val(), dict):
                    stats['total_appointments'] += len(doctor_appointments.val())
        
        return stats
        
    except Exception as e:
        print(f"Error getting system stats: {str(e)}")
        
        return {
            'total_users': 0,
            'total_doctors': 0,
            'total_patients': 0,
            'total_appointments': 0
        }  
def handle_content_management(action):
    """معالجة إدارة المحتوى."""
    try:
        if action == 'articles':
            manage_articles()
        elif action == 'assessments':
            manage_assessments()
        elif action == 'challenges':
            manage_challenges()
    except Exception as e:
        print(f"Error in content management: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة المحتوى")

def manage_articles():
    """إدارة المقالات والنصائح."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# إدارة المقالات والنصائح")
    
    try:
    
        put_button("➕ إضافة مقال جديد", onclick=add_new_article, color='success')
        
        articles = db.child("articles").get()
        if articles:
            for article in articles.each():
                article_data = article.val()
                put_html(f"""
                    <div class="admin-card">
                        <h4>{article_data.get('title', '')}</h4>
                        <p><small>تاريخ النشر: {article_data.get('date', '')}</small></p>
                    </div>
                """)
                put_buttons([
                    {'label': 'تعديل', 'value': ('edit', article.key()), 'color': 'warning'},
                    {'label': 'حذف', 'value': ('delete', article.key()), 'color': 'danger'}
                ], onclick=lambda x: handle_article_action(x))
        else:
            put_text("لا توجد مقالات")
            
    except Exception as e:
        print(f"Error managing articles: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة المقالات")

def manage_assessments():
    """إدارة التقييمات النفسية."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# إدارة التقييمات النفسية")
    
    try:
       
        put_button("➕ إضافة تقييم جديد", onclick=add_new_assessment, color='success')
        
        
        assessments = db.child("assessments").get()
        if assessments:
            for assessment in assessments.each():
                assessment_data = assessment.val()
                put_html(f"""
                    <div class="admin-card">
                        <h4>{assessment_data.get('title', '')}</h4>
                        <p>عدد الأسئلة: {len(assessment_data.get('questions', []))}</p>
                    </div>
                """)
                put_buttons([
                    {'label': 'تعديل', 'value': ('edit', assessment.key()), 'color': 'warning'},
                    {'label': 'حذف', 'value': ('delete', assessment.key()), 'color': 'danger'}
                ], onclick=lambda x: handle_assessment_action(x))
        else:
            put_text("لا توجد تقييمات")
            
    except Exception as e:
        print(f"Error managing assessments: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة التقييمات")

def manage_challenges():
    """إدارة التحديات اليومية."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# إدارة التحديات اليومية")
    
    try:
        
        put_button("➕ إضافة تحدي جديد", onclick=add_new_challenge, color='success')
        
       
        challenges = db.child("challenges").get()
        if challenges:
            for challenge in challenges.each():
                challenge_data = challenge.val()
                put_html(f"""
                    <div class="admin-card">
                        <h4>{challenge_data.get('title', '')}</h4>
                        <p>المدة: {challenge_data.get('duration', '')} أيام</p>
                    </div>
                """)
                put_buttons([
                    {'label': 'تعديل', 'value': ('edit', challenge.key()), 'color': 'warning'},
                    {'label': 'حذف', 'value': ('delete', challenge.key()), 'color': 'danger'}
                ], onclick=lambda x: handle_challenge_action(x))
        else:
            put_text("لا توجد تحديات")
            
    except Exception as e:
        print(f"Error managing challenges: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة التحديات")

def add_new_article():
    """إضافة مقال جديد."""
    clear()
    add_back_button(manage_articles)
    put_markdown("# إضافة مقال جديد")
    
    try:
        data = input_group("معلومات المقال", [
            input('title', type=TEXT, name='title', placeholder='عنوان المقال'),
            textarea('content', name='content', placeholder='محتوى المقال'),
            input('tags', type=TEXT, name='tags', placeholder='الوسوم (مفصولة بفواصل)')
        ])
        
        if data:
            article_data = {
                'title': data['title'],
                'content': data['content'],
                'tags': [tag.strip() for tag in data['tags'].split(',')],
                'date': datetime.now().isoformat(),
                'author': session_storage.user
            }
            
            db.child("articles").push(article_data)
            popup("تم", "تم إضافة المقال بنجاح")
            manage_articles()
            
    except Exception as e:
        print(f"Error adding article: {str(e)}")
        popup("خطأ", "حدث خطأ في إضافة المقال")

def handle_article_action(action):
    """معالجة إجراءات المقالات."""
    action_type, article_id = action
    try:
        if action_type == 'edit':
            edit_article(article_id)
        elif action_type == 'delete':
            if actions("هل أنت متأكد من حذف هذا المقال؟", ["نعم", "لا"]) == "نعم":
                db.child("articles").child(article_id).remove()
                popup("تم", "تم حذف المقال بنجاح")
                manage_articles()
    except Exception as e:
        print(f"Error in article action: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")  
def handle_reports(action):
    """معالجة التقارير والتحليلات."""
    try:
        if action == 'activity':
            show_activity_reports()
        elif action == 'appointments':
            show_appointment_reports()
        elif action == 'analytics':
            show_analytics()
    except Exception as e:
        print(f"Error in reports handling: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض التقارير")

def show_activity_reports():
    """عرض تقارير النشاط."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# تقارير النشاط")
    
    try:
       
        put_html('<div class="admin-card">')
        put_markdown("### النشاط اليومي")
        
       
        today = datetime.now().date()
        daily_stats = get_daily_activity_stats(today)
        
        put_html(f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>تسجيلات الدخول</h4>
                    <p>{daily_stats['logins']}</p>
                </div>
                <div class="stat-card">
                    <h4>المواعيد الجديدة</h4>
                    <p>{daily_stats['new_appointments']}</p>
                </div>
                <div class="stat-card">
                    <h4>المحادثات النشطة</h4>
                    <p>{daily_stats['active_chats']}</p>
                </div>
            </div>
        """)
        put_html('</div>')
        
    except Exception as e:
        print(f"Error showing activity reports: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض تقارير النشاط")

def show_appointment_reports():
    """عرض تقارير المواعيد."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# تقارير المواعيد")
    
    try:
       
        appointments_stats = get_appointment_stats()
        
        put_html('<div class="admin-card">')
        put_markdown("### إحصائيات المواعيد")
        put_html(f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>المواعيد اليوم</h4>
                    <p>{appointments_stats['today']}</p>
                </div>
                <div class="stat-card">
                    <h4>المواعيد هذا الأسبوع</h4>
                    <p>{appointments_stats['this_week']}</p>
                </div>
                <div class="stat-card">
                    <h4>نسبة الحضور</h4>
                    <p>{appointments_stats['attendance_rate']}%</p>
                </div>
            </div>
        """)
        put_html('</div>')
        
    except Exception as e:
        print(f"Error showing appointment reports: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض تقارير المواعيد")

def show_analytics():
    """عرض التحليلات."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# تحليل البيانات")
    
    try:
       
        user_analytics = get_user_analytics()
        
        put_html('<div class="admin-card">')
        put_markdown("### تحليلات المستخدمين")
        put_html(f"""
            <div class="stats-grid">
                <div class="stat-card">
                    <h4>معدل النمو الشهري</h4>
                    <p>{user_analytics['monthly_growth']}%</p>
                </div>
                <div class="stat-card">
                    <h4>نسبة الاحتفاظ</h4>
                    <p>{user_analytics['retention_rate']}%</p>
                </div>
                <div class="stat-card">
                    <h4>متوسط التقييم</h4>
                    <p>{user_analytics['avg_rating']}/5</p>
                </div>
            </div>
        """)
        put_html('</div>')
        
    except Exception as e:
        print(f"Error showing analytics: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض التحليلات")

def get_daily_activity_stats(date):
    """جلب إحصائيات النشاط اليومي."""
    try:
       
        return {
            'logins': 0,
            'new_appointments': 0,
            'active_chats': 0
        }
    except Exception as e:
        print(f"Error getting daily stats: {str(e)}")
        return {'logins': 0, 'new_appointments': 0, 'active_chats': 0}

def get_appointment_stats():
    """جلب إحصائيات المواعيد."""
    try:
        
        return {
            'today': 0,
            'this_week': 0,
            'attendance_rate': 0
        }
    except Exception as e:
        print(f"Error getting appointment stats: {str(e)}")
        return {'today': 0, 'this_week': 0, 'attendance_rate': 0}

def get_user_analytics():
    """جلب تحليلات المستخدمين."""
    try:
       
        return {
            'monthly_growth': 0,
            'retention_rate': 0,
            'avg_rating': 0
        }
    except Exception as e:
        print(f"Error getting user analytics: {str(e)}")
        return {'monthly_growth': 0, 'retention_rate': 0, 'avg_rating': 0}   
def handle_system_settings(action):
    """معالجة إعدادات النظام."""
    try:
        if action == 'general':
            show_general_settings()
        elif action == 'backup':
            handle_backup()
        elif action == 'logs':
            show_system_logs()
    except Exception as e:
        print(f"Error in system settings: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإعدادات")

def show_general_settings():
    """عرض الإعدادات العامة."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# الإعدادات العامة")
    
    try:
        
        settings = db.child("settings").get().val() or {}
        
        
        data = input_group("إعدادات النظام", [
            input('site_name', type=TEXT, name='site_name', 
                  value=settings.get('site_name', 'YOUR MIND'),
                  label='اسم الموقع'),
            input('contact_email', type=TEXT, name='contact_email',
                  value=settings.get('contact_email', ''),
                  label='البريد الإلكتروني للتواصل'),
            input('max_appointments', type=NUMBER, name='max_appointments',
                  value=settings.get('max_appointments', 10),
                  label='الحد الأقصى للمواعيد اليومية'),
            checkbox('maintenance_mode', name='maintenance_mode',
                    label='وضع الصيانة',
                    value=settings.get('maintenance_mode', False))
        ])
        
        if data:
            db.child("settings").update(data)
            popup("تم", "تم تحديث الإعدادات بنجاح")
            
    except Exception as e:
        print(f"Error in general settings: {str(e)}")
        popup("خطأ", "حدث خطأ في تحديث الإعدادات")

def handle_backup():
    """إدارة النسخ الاحتياطي."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# النسخ الاحتياطي")
    
    try:
      
        last_backup = db.child("backup_info").get().val()
        if last_backup:
            put_text(f"آخر نسخة احتياطية: {last_backup.get('date', 'غير متوفر')}")
        
        def create_backup():
            try:
               
                backup_data = {
                    'users': db.child("users").get().val(),
                    'appointments': db.child("appointments").get().val(),
                    'articles': db.child("articles").get().val(),
                    'assessments': db.child("assessments").get().val(),
                    'challenges': db.child("challenges").get().val()
                }
                
              
                db.child("backup_info").set({
                    'date': datetime.now().isoformat(),
                    'size': len(str(backup_data))
                })
                
               
                db.child("backups").push(backup_data)
                popup("تم", "تم إنشاء نسخة احتياطية بنجاح")
                
            except Exception as e:
                print(f"Error creating backup: {str(e)}")
                popup("خطأ", "حدث خطأ في إنشاء النسخة الاحتياطية")
        
        put_button("إنشاء نسخة احتياطية جديدة", onclick=create_backup)
        
    except Exception as e:
        print(f"Error in backup handling: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة النسخ الاحتياطي")

def show_system_logs():
    """عرض سجلات النظام."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# سجلات النظام")
    
    try:
       
        logs = db.child("system_logs").order_by_child("timestamp").limit_to_last(50).get()
        
        if logs:
            for log in logs.each():
                log_data = log.val()
                put_html(f"""
                    <div class="log-entry" style="margin: 10px 0; padding: 10px; border-left: 3px solid 
                        {'#dc3545' if log_data.get('level') == 'error' else 
                         '#ffc107' if log_data.get('level') == 'warning' else '#28a745'};
                        background-color: #f8f9fa;">
                        <strong>{log_data.get('timestamp', '')}</strong><br>
                        <span>{log_data.get('message', '')}</span>
                    </div>
                """)
        else:
            put_text("لا توجد سجلات متاحة")
            
    except Exception as e:
        print(f"Error showing system logs: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض السجلات")

def log_system_event(message, level='info'):
    """تسجيل حدث في سجلات النظام."""
    try:
        db.child("system_logs").push({
            'timestamp': datetime.now().isoformat(),
            'message': message,
            'level': level
        })
    except Exception as e:
        print(f"Error logging system event: {str(e)}")
def add_new_assessment():
    """إضافة تقييم نفسي جديد."""
    clear()
    add_back_button(manage_assessments)
    put_markdown("# إضافة تقييم جديد")
    
    try:
        data = input_group("معلومات التقييم", [
            input('title', type=TEXT, name='title', placeholder='عنوان التقييم'),
            input('description', type=TEXT, name='description', placeholder='وصف التقييم'),
            textarea('questions', name='questions', 
                    placeholder='الأسئلة (سؤال واحد في كل سطر)'),
            input('min_score', type=NUMBER, name='min_score', 
                  placeholder='أقل درجة'),
            input('max_score', type=NUMBER, name='max_score', 
                  placeholder='أعلى درجة')
        ])
        
        if data:
            assessment_data = {
                'title': data['title'],
                'description': data['description'],
                'questions': [q.strip() for q in data['questions'].split('\n') if q.strip()],
                'min_score': data['min_score'],
                'max_score': data['max_score'],
                'created_at': datetime.now().isoformat(),
                'created_by': session_storage.user
            }
            
            db.child("assessments").push(assessment_data)
            popup("تم", "تم إضافة التقييم بنجاح")
            manage_assessments()
            
    except Exception as e:
        print(f"Error adding assessment: {str(e)}")
        popup("خطأ", "حدث خطأ في إضافة التقييم")

def add_new_challenge():
    """إضافة تحدي جديد."""
    clear()
    add_back_button(manage_challenges)
    put_markdown("# إضافة تحدي جديد")
    
    try:
        data = input_group("معلومات التحدي", [
            input('title', type=TEXT, name='title', placeholder='عنوان التحدي'),
            input('description', type=TEXT, name='description', 
                  placeholder='وصف التحدي'),
            input('duration', type=NUMBER, name='duration', 
                  placeholder='مدة التحدي بالأيام'),
            textarea('tasks', name='tasks', 
                    placeholder='المهام اليومية (مهمة واحدة في كل سطر)'),
            input('points', type=NUMBER, name='points', 
                  placeholder='النقاط المكتسبة عند إكمال التحدي')
        ])
        
        if data:
            challenge_data = {
                'title': data['title'],
                'description': data['description'],
                'duration': data['duration'],
                'tasks': [task.strip() for task in data['tasks'].split('\n') if task.strip()],
                'points': data['points'],
                'created_at': datetime.now().isoformat(),
                'created_by': session_storage.user
            }
            
            db.child("challenges").push(challenge_data)
            popup("تم", "تم إضافة التحدي بنجاح")
            manage_challenges()
            
    except Exception as e:
        print(f"Error adding challenge: {str(e)}")
        popup("خطأ", "حدث خطأ في إضافة التحدي")

def handle_assessment_action(action):
    """معالجة إجراءات التقييمات."""
    action_type, assessment_id = action
    try:
        if action_type == 'edit':
            edit_assessment(assessment_id)
        elif action_type == 'delete':
            if actions("هل أنت متأكد من حذف هذا التقييم؟", ["نعم", "لا"]) == "نعم":
                db.child("assessments").child(assessment_id).remove()
                popup("تم", "تم حذف التقييم بنجاح")
                manage_assessments()
    except Exception as e:
        print(f"Error in assessment action: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")

def handle_challenge_action(action):
    """معالجة إجراءات التحديات."""
    action_type, challenge_id = action
    try:
        if action_type == 'edit':
            edit_challenge(challenge_id)
        elif action_type == 'delete':
            if actions("هل أنت متأكد من حذف هذا التحدي؟", ["نعم", "لا"]) == "نعم":
                db.child("challenges").child(challenge_id).remove()
                popup("تم", "تم حذف التحدي بنجاح")
                manage_challenges()
    except Exception as e:
        print(f"Error in challenge action: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")

def edit_assessment(assessment_id):
    """تعديل تقييم."""
    clear()
    add_back_button(manage_assessments)
    put_markdown("# تعديل التقييم")
    
    try:
       
        assessment = db.child("assessments").child(assessment_id).get().val()
        if assessment:
            data = input_group("تعديل التقييم", [
                input('title', type=TEXT, name='title', 
                      value=assessment.get('title', ''),
                      placeholder='عنوان التقييم'),
                input('description', type=TEXT, name='description',
                      value=assessment.get('description', ''),
                      placeholder='وصف التقييم'),
                textarea('questions', name='questions',
                        value='\n'.join(assessment.get('questions', [])),
                        placeholder='الأسئلة (سؤال واحد في كل سطر)'),
                input('min_score', type=NUMBER, name='min_score',
                      value=assessment.get('min_score', 0),
                      placeholder='أقل درجة'),
                input('max_score', type=NUMBER, name='max_score',
                      value=assessment.get('max_score', 100),
                      placeholder='أعلى درجة')
            ])
            
            if data:
                assessment_data = {
                    'title': data['title'],
                    'description': data['description'],
                    'questions': [q.strip() for q in data['questions'].split('\n') if q.strip()],
                    'min_score': data['min_score'],
                    'max_score': data['max_score'],
                    'updated_at': datetime.now().isoformat()
                }
                
                db.child("assessments").child(assessment_id).update(assessment_data)
                popup("تم", "تم تحديث التقييم بنجاح")
                manage_assessments()
                
    except Exception as e:
        print(f"Error editing assessment: {str(e)}")
        popup("خطأ", "حدث خطأ في تعديل التقييم")

def edit_challenge(challenge_id):
    """تعديل تحدي."""
    clear()
    add_back_button(manage_challenges)
    put_markdown("# تعديل التحدي")
    
    try:
       
        challenge = db.child("challenges").child(challenge_id).get().val()
        if challenge:
            data = input_group("تعديل التحدي", [
                input('title', type=TEXT, name='title',
                      value=challenge.get('title', ''),
                      placeholder='عنوان التحدي'),
                input('description', type=TEXT, name='description',
                      value=challenge.get('description', ''),
                      placeholder='وصف التحدي'),
                input('duration', type=NUMBER, name='duration',
                      value=challenge.get('duration', 7),
                      placeholder='مدة التحدي بالأيام'),
                textarea('tasks', name='tasks',
                        value='\n'.join(challenge.get('tasks', [])),
                        placeholder='المهام اليومية (مهمة واحدة في كل سطر)'),
                input('points', type=NUMBER, name='points',
                      value=challenge.get('points', 100),
                      placeholder='النقاط المكتسبة عند إكمال التحدي')
            ])
            
            if data:
                challenge_data = {
                    'title': data['title'],
                    'description': data['description'],
                    'duration': data['duration'],
                    'tasks': [task.strip() for task in data['tasks'].split('\n') if task.strip()],
                    'points': data['points'],
                    'updated_at': datetime.now().isoformat()
                }
                
                db.child("challenges").child(challenge_id).update(challenge_data)
                popup("تم", "تم تحديث التحدي بنجاح")
                manage_challenges()
                
    except Exception as e:
        print(f"Error editing challenge: {str(e)}")
        popup("خطأ", "حدث خطأ في تعديل التحدي")

def manage_patients():
    """إدارة المرضى."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# إدارة المرضى")
    
    try:
        
        users = db.child("users").get()
        if users:
            for user in users.each():
                user_data = user.val()
                if user_data.get('role') == 'patient':
                    put_html(f"""
                        <div class="admin-card">
                            <h4>{user_data.get('name', 'مريض')}</h4>
                            <p>البريد: {user_data.get('email', '')}</p>
                            <p>الحالة: {user_data.get('status', 'نشط')}</p>
                        </div>
                    """)
                    put_buttons([
                        {'label': 'عرض الملف', 'value': ('view', user.key()), 'color': 'info'},
                        {'label': 'تعليق الحساب', 'value': ('suspend', user.key()), 'color': 'warning'},
                        {'label': 'حذف', 'value': ('delete', user.key()), 'color': 'danger'}
                    ], onclick=handle_patient_action)
        else:
            put_text("لا يوجد مرضى مسجلين")
            
    except Exception as e:
        print(f"Error managing patients: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة المرضى")

def handle_patient_action(action):
    """معالجة إجراءات المرضى."""
    action_type, patient_id = action
    try:
        if action_type == 'view':
            view_patient_profile(patient_id)
        elif action_type == 'suspend':
            if actions("هل أنت متأكد من تعليق هذا الحساب؟", ["نعم", "لا"]) == "نعم":
                db.child("users").child(patient_id).update({'status': 'suspended'})
                popup("تم", "تم تعليق الحساب بنجاح")
                manage_patients()
        elif action_type == 'delete':
            if actions("هل أنت متأكد من حذف هذا الحساب؟", ["نعم", "لا"]) == "نعم":
                db.child("users").child(patient_id).remove()
                popup("تم", "تم حذف الحساب بنجاح")
                manage_patients()
    except Exception as e:
        print(f"Error in patient action: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")

def manage_articles():
    """إدارة المقالات والنصائح."""
    clear()
    add_back_button(show_admin_screen)
    put_markdown("# إدارة المقالات والنصائح")
    
    try:
       
        put_button("➕ إضافة مقال جديد", onclick=add_new_article, color='success')
        
       
        articles = db.child("articles").get()
        
        if articles and articles.val():  
            for article in articles.each():
                article_data = article.val()
                put_html(f"""
                    <div class="admin-card">
                        <h4>{article_data.get('title', '')}</h4>
                        <p><small>تاريخ النشر: {article_data.get('date', '')}</small></p>
                        <p>{article_data.get('content', '')[:200]}...</p>
                    </div>
                """)
                put_buttons([
                    {'label': 'تعديل', 'value': ('edit', article.key()), 'color': 'warning'},
                    {'label': 'حذف', 'value': ('delete', article.key()), 'color': 'danger'}
                ], onclick=handle_article_action)
        else:
            put_html("""
                <div class="admin-card" style="text-align: center; padding: 20px;">
                    <p>لا توجد مقالات حالياً</p>
                </div>
            """)
            
    except Exception as e:
        print(f"Error managing articles: {str(e)}")
        popup("خطأ", "حدث خطأ في إدارة المقالات")

def handle_article_action(action):
    """معالجة إجراءات المقالات."""
    action_type, article_id = action
    try:
        if action_type == 'edit':
            edit_article(article_id)
        elif action_type == 'delete':
            if actions("هل أنت متأكد من حذف هذا المقال؟", ["نعم", "لا"]) == "نعم":
                db.child("articles").child(article_id).remove()
                popup("تم", "تم حذف المقال بنجاح")
                manage_articles()
    except Exception as e:
        print(f"Error in article action: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")

def edit_article(article_id):
    """تعديل مقال."""
    clear()
    add_back_button(manage_articles)
    put_markdown("# تعديل المقال")
    
    try:
        article = db.child("articles").child(article_id).get().val()
        if article:
            data = input_group("تعديل المقال", [
                input('title', type=TEXT, name='title', 
                      value=article.get('title', ''),
                      placeholder='عنوان المقال'),
                textarea('content', name='content',
                        value=article.get('content', ''),
                        placeholder='محتوى المقال'),
                input('tags', type=TEXT, name='tags',
                      value=','.join(article.get('tags', [])),
                      placeholder='الوسوم (مفصولة بفواصل)')
            ])
            
            if data:
                article_data = {
                    'title': data['title'],
                    'content': data['content'],
                    'tags': [tag.strip() for tag in data['tags'].split(',') if tag.strip()],
                    'updated_at': datetime.now().isoformat()
                }
                
                db.child("articles").child(article_id).update(article_data)
                popup("تم", "تم تحديث المقال بنجاح")
                manage_articles()
                
    except Exception as e:
        print(f"Error editing article: {str(e)}")
        popup("خطأ", "حدث خطأ في تعديل المقال")

def show_community():
    """عرض صفحة المجتمع."""
    clear()
    add_back_button()
    put_markdown("# مجتمع YOUR MIND")
    
    try:
        put_button("✍️ إنشاء منشور جديد", onclick=create_new_post, color='success')
        posts = db.child("community_posts").get()
        
        if posts and posts.val():
            sorted_posts = sorted(
                posts.each(),
                key=lambda x: x.val().get('timestamp', ''),
                reverse=True
            )
            for post in sorted_posts:
                display_post(post.key(), post.val())
        else:
            put_html("""
                <div style="text-align: center; padding: 20px; background: #f8fff8; border-radius: 10px;">
                    <h3>لا توجد منشورات بعد</h3>
                    <p>كن أول من يشارك في المجتمع!</p>
                </div>
            """)
    except Exception as e:
        print(f"Error in community: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض المجتمع")
def create_new_post():
    """إنشاء منشور جديد."""
    clear()
    add_back_button
    put_markdown("# إنشاء منشور جديد")
    username=session_storage.user
    
    try:
       
        user_ref = db.child("users").child(username)
        user_data = user_ref.get().val() or {}
        user_name = user_data.get('users', username)
        user_role = getattr(session_storage, 'role', 'user')

        input_fields = [
            textarea('content', name='content', 
                    placeholder='اكتب منشورك هنا...',
                    required=True),
            input('tags', name='tags', 
                  placeholder='الوسوم (اختياري، افصل بينها بفواصل)')
        ]
        
       
        is_anonymous = False
        if hasattr(session_storage, 'role') and session_storage.role == 'patient':
            input_fields.append(
                checkbox(name='anonymous', 
                        options=[{'label': 'إخفاء الاسم (نشر كمجهول)', 'value': 'yes'}])
            )
        
        data = input_group("منشور جديد", input_fields)
        
        if data:
           
            is_anonymous = bool(data.get('anonymous', []))
            display_name = "مجهول" if (user_role == 'patient' and is_anonymous) else user_name
            
            post_data = {
                'content': data['content'],
                'tags': [tag.strip() for tag in data.get('tags', '').split(',') if tag.strip()],
                'author': username,
                'author_name': display_name,
                'author_role': user_role,
                'is_anonymous': is_anonymous,
                'timestamp': datetime.now().isoformat(),
                'likes': 0,
                'liked_by': []
            }
            
            db.child("community_posts").push(post_data)
            popup("تم", "تم نشر المنشور بنجاح")
            show_community()
            
    except Exception as e:
        print(f"Error creating post: {str(e)}")
        popup("خطأ", "حدث خطأ في إنشاء المنشور")
        show_community()
def add_comment(post_id):
    """إضافة تعليق على منشور."""
    try:
       
        users = db.child("users").get()
        user_name = session_storage.user  
        user_role = 'user' 

        
        if users:
            for user in users.each():
                user_data = user.val()
                if user_data and user_data.get('username') == session_storage.user:
                    user_name = user_data.get('name', session_storage.user)
                    user_role = user_data.get('role', 'user')
                    break

        input_fields = [
            textarea('content', name='content', 
                    placeholder='اكتب تعليقك هنا...',
                    required=True)
        ]
        
       
        is_anonymous = False
        if user_role == 'patient':
            input_fields.append(
                checkbox(name='anonymous',
                        options=[{'label': 'إخفاء الاسم (تعليق كمجهول)', 'value': 'yes'}])
            )
        
        comment = input_group("إضافة تعليق", input_fields)
        
        if comment and comment.get('content'):
           
            is_anonymous = bool(comment.get('anonymous', []))
            display_name = "مجهول" if (user_role == 'patient' and is_anonymous) else user_name
            
            comment_data = {
                'content': comment['content'],
                'author': session_storage.user,
                'author_name': display_name,
                'author_role': user_role,
                'is_anonymous': is_anonymous,
                'timestamp': datetime.now().isoformat()
            }
            
            db.child("post_comments").child(post_id).push(comment_data)
            show_community()
            
    except Exception as e:
        print(f"Error adding comment: {str(e)}")
        popup("خطأ", "حدث خطأ في إضافة التعليق")
        show_community()
def display_post(post_id, post_data):
    """عرض منشور واحد."""
    try:
        role_badge = ""
        if post_data.get('author_role') == 'doctor':
            role_badge = '<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 10px; margin-right: 5px;">طبيب</span>'
        elif post_data.get('author_role') == 'admin':
            role_badge = '<span style="background: #2196F3; color: white; padding: 2px 8px; border-radius: 10px; margin-right: 5px;">مشرف</span>'
        
        liked = session_storage.user in post_data.get('liked_by', [])
        
        
        user_data = db.child("users").child(post_data.get('author')).get().val()
        author_name = user_data.get('name', 'مستخدم') if user_data else 'مستخدم'
        
        if post_data.get('is_anonymous', False):
            author_name = "مجهول"
        
        put_html(f"""
            <div class="post-card" style="
                background: white;
                border-radius: 15px;
                padding: 20px;
                margin: 15px 0;
                box-shadow: 0 2px 5px rgba(0,0,0,0.1);">
                
                <div style="display: flex; align-items: center; margin-bottom: 10px;">
                    {role_badge}
                    <strong style="color: #2E7D32;">{author_name}</strong>
                    <small style="margin-right: 10px; color: #666;">
                        {format_timestamp(post_data.get('timestamp', ''))}
                    </small>
                </div>
                
                <p style="white-space: pre-wrap;">{post_data.get('content', '')}</p>
                
                <div style="margin: 10px 0;">
                    {' '.join([f'<span style="background: #E8F5E9; padding: 3px 8px; border-radius: 12px; margin-right: 5px; font-size: 0.9em;">#{tag}</span>' 
                             for tag in post_data.get('tags', [])])}
                </div>
            </div>
        """)
        
        put_buttons([
            {'label': f"{'❤️' if liked else '🤍'} {post_data.get('likes', 0)}", 
             'value': ('like', post_id), 'color': 'danger' if liked else 'light'},
            {'label': '💬 تعليق', 'value': ('comment', post_id), 'color': 'success'}
        ], onclick=lambda x: handle_post_action(x))
        
        comments = db.child("post_comments").child(post_id).get()
        if comments and comments.val():
            put_html('<div style="margin-right: 20px;">')
            for comment in comments.each():
                comment_data = comment.val()
                comment_role_badge = ""
                if comment_data.get('author_role') == 'doctor':
                    comment_role_badge = '<span style="background: #4CAF50; color: white; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-size: 0.8em;">طبيب</span>'
                elif comment_data.get('author_role') == 'admin':
                    comment_role_badge = '<span style="background: #2196F3; color: white; padding: 2px 8px; border-radius: 10px; margin-right: 5px; font-size: 0.8em;">مشرف</span>'
                
              
                comment_user_data = db.child("users").child(comment_data.get('author')).get().val()
                comment_author_name = comment_user_data.get('name', 'مستخدم') if comment_user_data else 'مستخدم'
                
                if comment_data.get('is_anonymous', False):
                    comment_author_name = "مجهول"
                
                put_html(f"""
                    <div style="
                        background: #f8fff8;
                        border-radius: 10px;
                        padding: 10px;
                        margin: 5px 0;">
                        {comment_role_badge}
                        <strong>{comment_author_name}</strong>
                        <p style="margin: 5px 0;">{comment_data.get('content', '')}</p>
                        <small style="color: #666;">
                            {format_timestamp(comment_data.get('timestamp', ''))}
                        </small>
                    </div>
                """)
            put_html('</div>')
            
    except Exception as e:
        print(f"Error displaying post: {str(e)}")
def handle_post_action(action):
    """معالجة إجراءات المنشور."""
    action_type, post_id = action
    try:
        if action_type == 'like':
            toggle_like(post_id)
        elif action_type == 'comment':
            add_comment(post_id)
    except Exception as e:
        print(f"Error in post action: {str(e)}")
        popup("خطأ", "حدث خطأ في معالجة الإجراء")

def toggle_like(post_id):
    """تبديل حالة الإعجاب بالمنشور."""
    try:
        post = db.child("community_posts").child(post_id).get().val()
        liked_by = post.get('liked_by', [])
        
        if session_storage.user in liked_by:
            liked_by.remove(session_storage.user)
            new_likes = post.get('likes', 1) - 1
        else:
            liked_by.append(session_storage.user)
            new_likes = post.get('likes', 0) + 1
        
        db.child("community_posts").child(post_id).update({
            'likes': new_likes,
            'liked_by': liked_by
        })
        
        show_community()
        
    except Exception as e:
        print(f"Error toggling like: {str(e)}")
        popup("خطأ", "حدث خطأ في تحديث الإعجاب")

def format_timestamp(timestamp_str):
    """تنسيق الطابع الزمني."""
    try:
        timestamp = datetime.fromisoformat(timestamp_str)
        now = datetime.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"منذ {diff.days} يوم" if diff.days == 1 else f"منذ {diff.days} أيام"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"منذ {hours} ساعة" if hours == 1 else f"منذ {hours} ساعات"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"منذ {minutes} دقيقة" if minutes == 1 else f"منذ {minutes} دقائق"
        else:
            return "منذ لحظات"
    except:
        return timestamp_str

def emergency():
    """التعامل مع حالات الطوارئ."""
    popup("طوارئ", 
          """للحالات الطارئة يرجى الاتصال على:
          911 - الطوارئ العامة
          937 - الطوارئ الصحية
          920033360 - مركز الأزمات النفسية""")
 
def get_upcoming_appointments_count():
    """جلب عدد المواعيد القادمة."""
    try:
        appointments = db.child("appointments").get().val()
        if appointments:
            count = sum(1 for app in appointments.values() 
                       if app.get('patient') == session_storage.user 
                       and app.get('status') == 'scheduled')
            return count
        return 0
    except Exception as e:
        print(f"Error getting appointments count: {str(e)}")
        return 0

def get_active_challenges_count():
    """جلب عدد التحديات النشطة."""
    try:
        challenges = db.child("user_challenges").child(session_storage.user).get().val()
        if challenges:
            count = sum(1 for challenge in challenges.values() 
                       if challenge.get('status') == 'active')
            return count
        return 0
    except Exception as e:
        print(f"Error getting challenges count: {str(e)}")
        return 0

def get_last_assessment_date():
    """جلب تاريخ آخر تقييم."""
    try:
        assessments = db.child("assessments").child(session_storage.user).get().val()
        if assessments:
            dates = [assessment.get('date') for assessment in assessments.values()]
            return max(dates)
        return "لا يوجد"
    except Exception as e:
        print(f"Error getting last assessment date: {str(e)}")
        return "لا يوجد"
def show_patient_screen():
    """عرض الشاشة الرئيسية للمريض."""
    session_storage.current_page ="patient"

    clear()
    add_global_style()
    try:
        username = session_storage.user
        
       
        put_html(f"""
            <div class="admin-header">
                <h1>لوحة التحكم</h1>
                <p>مرحباً، {username}</p>
            </div>
            <style>
                .admin-header {{
                    background: linear-gradient(135deg, #4B72A28, #4B72A2);
                    color: white;
                    padding: 20px;
                    border-radius: 10px;
                    margin-bottom: 20px;
                    text-align: center;
                }}
                .admin-card {{
                    background: white;
                    border-radius: 10px;
                    padding: 20px;
                    margin: 10px 0;
                    box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    transition: transform 0.2s;
                }}
                .admin-card:hover {{
                    transform: translateY(-2px);
                }}
                .card-title {{
                    color: #2E7D32;
                    margin: 0 0 15px 0;
                    display: flex;
                    align-items: center;
                    gap: 10px;
                }}
                .card-buttons {{
                    display: flex;
                    flex-direction: column;
                    gap: 10px;
                }}
                .card-buttons button {{
                    width: 100%;
                    padding: 12px;
                    margin: 5px 0;
                    text-align: right;
                }}
            </style>
        """)

       
        put_html('<div class="admin-card" style="background: #ffebee;">')
        put_button('🚨 للطوارئ - اضغط هنا', onclick=emergency, color='danger')
        put_html('</div>')

        
        put_html("""
            <div class="admin-card">
                <h2 class="card-title">⚡ الإجراءات السريعة</h2>
                <div class="card-buttons">
        """)
        for btn in [
            {'label': '👤 الملف الشخصي', 'value': 'profile', 'action': lambda: edit_patient_profile(username, 'patient')},
            {'label': '🔍 البحث عن طبيب', 'value': 'search', 'action': search_doctors}
        ]:
            put_button(btn['label'], onclick=btn['action'], color='success')
        put_html("</div></div>")

       
        put_html("""
            <div class="admin-card">
                <h2 class="card-title">📊 التقييمات والمتابعة</h2>
                <div class="card-buttons">
        """)
        for btn in [
            {'label': '📋 التقييم النفسي', 'value': 'assessment', 'action': start_beck_assessment},
            {'label': '😊 المشاعر', 'value': 'emotions', 'action': show_emotions_menu},
            {'label': '📚 سجلي الطبي', 'value': 'history', 'action': view_history}
        ]:
            put_button(btn['label'], onclick=btn['action'], color='success')
        put_html("</div></div>")

     
        put_html("""
            <div class="admin-card">
                <h2 class="card-title">🎯 الأنشطة والتحديات</h2>
                <div class="card-buttons">
        """)
        for btn in [

            {'label': '📖 المقالات', 'value': 'articles', 'action': show_articles},
            {'label': '✏️ مذكراتي', 'value': 'diary', 'action': show_diary}
        ]:
            put_button(btn['label'], onclick=btn['action'], color='success')
        put_html("</div></div>")

       
        put_html("""
            <div class="admin-card">
                <h2 class="card-title">📅 التواصل والمواعيد</h2>
                <div class="card-buttons">
        """)
        for btn in [
            {'label': '📅 مواعيدي', 'value': 'appointments', 'action': show_patient_appointments},
            {'label': '💬 المحادثات', 'value': 'messages', 'action': send_message},
             {'label': 'المجتمع', 'value': 'messages', 'action': show_community}
        ]:
            put_button(btn['label'], onclick=btn['action'], color='success')
        put_html("</div></div>")

       
        put_html('<div class="admin-card" style="text-align: center;">')
        put_button('🚪 تسجيل الخروج', onclick=handle_logout, color='warning')
        put_html('</div>')

    except Exception as e:
        print(f"Patient screen error: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض الصفحة")
        return show_login_screen()
def validate_password_strength(password):
    """Validate password strength and provide feedback."""
    strength = 0
    feedback = []
    if len(password) >= 8: strength += 1
    if any(c.isupper() for c in password): strength += 1
    if any(c.islower() for c in password): strength += 1
    if any(c.isdigit() for c in password): strength += 1
    if strength < 3:
        feedback.append("كلمة المرور يجب أن تحتوي على 8 أحرف على الأقل، وحرف كبير، وحرف صغير، ورقم.")
    return strength, feedback

def show_diary():
    clear()
    add_global_style()
    add_back_button()
    
    
    put_row([put_button("📝 كتابة مذكرة جديدة", onclick=write_diary_entry),
    put_button("📖 تسجيل المذكرات بالصوت", onclick=show_diary_record)
    ])
    put_button("📜 عرض المذكرات", onclick=show_diaries)
def show_diaries():
    clear()
    add_global_style()
    
    
    
    username = session_storage.user
    try:
         entries = db.child("diary").child(username).get().val()
         if entries:
             for entry in entries.values():
                 put_text(entry.get('content'))
                 put_text(f"التاريخ: {entry.get('date')}")
                 put_markdown("---")
    except Exception as e:
         logging.error(f"Error showing diary: {str(e)}")
         popup("خطأ", "حدث خطأ أثناء عرض المذكرات")
    put_row([
        put_button("🔙 الرجوع", onclick=show_diary)
    ])
def show_diary_record():
    
    clear()
    add_global_style()
    put_row([
        put_button("🔙 الرجوع", onclick=show_diary)
    ])
    
    put_markdown("# مذكراتي")
    def start_recording():
        """🔹 بدء التسجيل"""
        global recording, record_start_time, audio_data
        recording = True
        record_start_time = time.time()
        toast("🎤 جاري التسجيل...")
        audio_data = sd.rec(int(10 * 44100), samplerate=44100, channels=1)
        sd.wait()

    def stop_recording():
        """🔹 إيقاف التسجيل وتحليل الصوت وإضافته إلى السجل الطبي"""
        global recording, record_start_time, record_count, audio_data
        if recording:
            recording = False
            duration = time.time() - record_start_time
            if duration > 1:
                if not hasattr(session_storage, 'user'):
                    popup('خطأ', 'الرجاء تسجيل الدخول أولاً')
                    return

                username = session_storage.user  
                filename = f"{username}_diary_{record_count}.wav"
                filepath = os.path.join(SAVE_PATH, filename)
                record_count += 1 

                 
                sf.write(filepath, audio_data, 44100)

                try:
                    r = sr.Recognizer()
                    with sr.AudioFile(filepath) as source:
                        audio = r.record(source)
                        text = r.recognize_google(audio, language='ar-AR')

                    put_markdown("### 📌 إجابتك:")
                    put_markdown(f"💬 {text}")

                   
                    db.child("diary").child(username).push({
                        "content": text,
                        "date": datetime.now().isoformat()
                    })
                    popup("✅ تم", "تمت إضافة المذكرة بنجاح")
                except Exception as e:
                    popup("❌ خطأ", f"حدث خطأ أثناء تحليل الصوت: {str(e)}")

    put_button("🎙️ بدء التسجيل", onclick=start_recording, color='success')
    put_button("⏹️ إيقاف التسجيل", onclick=stop_recording, color='danger')

def write_diary_entry():
    """Show patient diary interface."""
   
    clear()
    add_global_style()
    put_row([
        put_button("🔙 الرجوع", onclick=show_diary)
    ])
     
    put_markdown("# مذكراتي")
    username = session_storage.user
    
    def add_entry():
        entry_info = input_group("إضافة مذكرة جديدة", [
            input("المحتوى:", name="content", type="text")
        ])
        
        if entry_info:
            try:
                db.child("diary").child(username).push({

                    "content": entry_info["content"],
                    "date": datetime.now().isoformat()
                })
                popup("تم", "تمت إضافة المذكرة بنجاح")
                show_diary()
            except Exception as e:
                popup("خطأ", f"حدث خطأ أثناء حفظ المذكرة: {str(e)}")
    
    put_button("إضافة مذكرة جديدة", onclick=add_entry)
    
    
    
    
    
def show_happiness_challenges():
    """Display random happiness challenges."""
    add_global_style() 
    clear()
    add_back_button()
  
    challenges = [
        "ابتسم لخمسة أشخاص اليوم 😊",
        "اكتب ثلاثة أشياء جميلة حدثت لك اليوم ✍️",
        "اتصل بصديق قديم لم تكلمه منذ فترة 📞",
        "مارس رياضة لمدة 15 دقيقة 🏃‍♂️",
        "اقرأ كتاباً لمدة 20 دقيقة 📚",
        "استمع إلى موسيقى تحبها 🎵",
        "تمشى في الطبيعة لمدة 10 دقائق 🌳",
        "قم بعمل تطوعي بسيط 🤝",
        "تعلم شيئاً جديداً اليوم 🎯",
        "اكتب رسالة شكر لشخص تقدره ❤️",
        "تناول وجبة صحية 🥗",
        "تأمل لمدة 5 دقائق 🧘‍♂️",
        "رتب غرفتك 🏠",
        "اشترِ هدية صغيرة لنفسك 🎁",
        "شارك قصة إيجابية مع الآخرين 📢"
    ]
    daily_challenges = random.sample(challenges, 3)
    put_markdown("# تحديات السعادة اليومية")
    put_markdown("## تحدياتك لليوم:")
    for i, challenge in enumerate(daily_challenges, 1):
        put_markdown(f"### {i}. {challenge}")
def cancel_appointment(appointment_id):
    """Cancel an appointment."""
    try:
        if actions("هل أنت متأكد من إلغاء هذا الموعد؟", ["نعم", "لا"]) == "نعم":
            db.child("appointments").child(appointment_id).update({"status": "cancelled"})
            popup("تم", "تم إلغاء الموعد بنجاح")
            manage_appointments()
    except Exception as e:
        popup("خطأ", f"حدث خطأ أثناء إلغاء الموعد: {str(e)}")

def view_patient_assessments(patient_username):
    """View patient's assessment results."""
    add_global_style() 
    clear()
    add_back_button()
  
    put_markdown(f"# نتائج تقييمات {patient_username}")
    
    try:
        assessments = db.child("assessments").child(patient_username).get().val()
        if not assessments:
            put_text("لا توجد تقييمات")
            return
            
        for assessment in assessments.values():
            put_markdown(f"### {assessment.get('type', 'تقييم')}")
            put_text(f"التاريخ: {assessment.get('date')}")
            put_text(f"النتيجة: {assessment.get('score')}")
            put_text(f"التفسير: {assessment.get('interpretation')}")
    except Exception as e:
        logging.error(f"Error viewing patient assessments: {str(e)}")
        popup("خطأ", "حدث خطأ أثناء عرض التقييمات")
def put_grid(content, cell_width='auto', cell_height='auto'):
    """Create a grid layout of elements."""
    grid_html = f"""
    <div class="grid-container" style="
        display: grid;
        grid-template-columns: repeat({len(content[0])}, {cell_width});
        grid-auto-rows: {cell_height};
        gap: 10px;
        padding: 10px;
    ">
    """
    for row in content:
        for item in row:
            grid_html += f"""
            <div class="grid-item" style="
                padding: 10px;
                text-align: center;
                display: flex;
                justify-content: center;
                align-items: center;
            ">
                {item}
            </div>
            """
    grid_html += "</div>"
    grid_html += """
    <style>
        .grid-container {
            width: 100%;
            max-width: 1200px;
            margin: 0 auto;
        }
        .grid-item {
            background: #f5fff5;
            border-radius: 10px;
            transition: all 0.3s ease;
        }
        .grid-item:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }
        @media (max-width: 768px) {
            .grid-container {
                grid-template-columns: 1fr !important;
            }
        }
    </style>
    """
    put_html(grid_html)

@contextmanager
def put_loading(message="جاري التحميل..."):
    """Enhanced loading indicator."""
    loading_scope = f'loading_{random.randint(0, 10000)}'
    try:
        with use_scope(loading_scope):
            put_html(f"""
                <div class="loading-container">
                    <div class="spinner"></div>
                    <div class="loading-text">{message}</div>
                </div>
                <style>
                    .loading-container {{
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        padding: 20px;
                    }}
                    .loading-text {{
                        margin-top: 10px;
                        color: #666;
                    }}
                </style>
            """)
        yield
    finally:
        clear(loading_scope)

def handle_errors(func):
    """Enhanced error handling decorator."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            with put_loading():
                return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error in {func.__name__}: {str(e)}")
            error_message = "حدث خطأ غير متوقع"
            if isinstance(e, ConnectionError):
                error_message = "خطأ في الاتصال. تأكد من اتصالك بالإنترنت"
            elif isinstance(e, TimeoutError):
                error_message = "انتهت مهلة الاتصال. حاول مرة أخرى"
            popup("خطأ", error_message)
            return None
    return wrapper

def check_session(func):
    """Improved session checking."""
    @wraps(func)
    def wrapper(*args, **kwargs):
        if not session_manager.is_logged_in():
            popup("تنبيه", "انتهت الجلسة. الرجاء تسجيل الدخول مرة أخرى")
            show_login_screen()
            return
        
        remaining_time = session_manager._get_remaining_time()
        if remaining_time <= timedelta(minutes=5):
            if actions("ستنتهي الجلسة قريباً. هل تريد التمديد؟", ["نعم", "لا"]) == "نعم":
                session_manager.extend_session()
        
        return func(*args, **kwargs)
    return wrapper

def add_emergency_support():
    """Add emergency support information."""
    put_markdown("""
    # 🚨 في حالة الطوارئ
    ### أرقام الطوارئ:
    - اتصل على 911 للطوارئ العامة
    - الخط الساخن للصحة النفسية: 1-800-XXX-XXXX (24/7)
    - خط الأزمات: 1-800-XXX-XXXX
    ### أقرب المستشفيات:
    - مستشفى الصحة النفسية المركزي: XXX-XXXX
    - مركز الطوارئ النفسية: XXX-XXXX
    ### نصائح سريعة:
    - لا تبق وحيداً
    - تواصل مع شخص تثق به
    - خذ أنفاساً عميقة
    - اطلب المساعدة فوراً إذا كنت تفكر في إيذاء نفسك
    """)
    put_button("اتصل بالطوارئ", onclick=lambda: run_js('window.location.href = "tel:911"'), color='danger')
  


def save_assessment_progress(index):
    """Save current assessment progress."""
    username = session_storage.user
    try:
        progress_data = {
            'index': index,
            'answers': answers_history,
            'total_score': total_score,
            'timestamp': datetime.now().isoformat()
        }
        db.child("assessment_progress").child(username).set(progress_data)
        popup("تم", "تم حفظ التقدم بنجاح")
    except Exception as e:
        popup("خطأ", "فشل حفظ التقدم")



def resume_assessment():
    """Resume paused assessment."""
    username = session_storage.user
    try:
        progress = db.child("assessment_progress").child(username).get().val()
        if progress:
            global total_score, answers_history
            total_score = progress.get('total_score', 0)
            answers_history = progress.get('answers', [])
            show_beck_question(progress.get('index', 0))
        else:
            start_beck_assessment()
    except Exception as e:
        popup("خطأ", "فشل استعادة التقييم")

def update_volume_meter(volume_level):
    """Update volume meter display."""
    try:
        run_js(f"document.querySelector('.meter-bar').style.height = '{volume_level}%';")
    except Exception as e:
        logging.error(f"Error updating volume meter: {str(e)}")

def update_recording_timer(seconds):
    """Update recording timer display."""
    try:
        minutes = seconds // 60
        seconds = seconds % 60
        run_js(f"document.getElementById('recording-timer').innerText = '{minutes:02d}:{seconds:02d}';")
    except Exception as e:
        logging.error(f"Error updating timer: {str(e)}")

class NavigationManager:
    def __init__(self):
        self.history = []
        
    def push(self, screen):
        self.history.append(screen)
        
    def pop(self):
        if self.history:
            previous = self.history.pop()
            if callable(previous):
                previous()
        else:
            main()

navigation_manager = NavigationManager()

class ErrorHandler:
    def __init__(self):
        self.error_messages = {
            'auth': "خطأ في المصادقة. يرجى المحاولة مرة أخرى.",
            'database_operation': "خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى.",
            'validation': "البيانات المدخلة غير صالحة. يرجى التحقق منها.",
            'unknown': "حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى."
        }
    
    def handle_error(self, error_type, exception=None):
        message = self.error_messages.get(error_type, self.error_messages['unknown'])
        if exception:
            print(f"Debug - Error details: {str(exception)}")
            logging.error(f"{error_type} error: {str(exception)}")
        popup("خطأ", message)

error_handler = ErrorHandler()

def show_progress_indicator(progress_value):
    """Show progress indicator."""
    put_processbar('progress', progress_value)
    put_text(f"Progress: {progress_value}%")

def show_immediate_feedback(answer):
    """Show immediate feedback after answering."""
    put_markdown("### Feedback")
    put_text("Thank you for your answer.")
    put_text("Processing...")
    time.sleep(1)
    put_text("✓ Answer recorded")

def add_audio_preview(recording):
    """Add audio playback preview."""
    put_html(f"""
        <audio controls>
            <source src="{recording}" type="audio/wav">
        </audio>
    """)

def show_recording_timer():
    """Show recording timer and volume meter."""
    put_html("""
        <div id="timer">00:00</div>
        <div id="volume-meter"></div>
    """)

def show_breadcrumb():
    """Show breadcrumb navigation."""
    path = navigation_manager.get_breadcrumb()
    put_html(f"""
        <div class="breadcrumb">
            {' > '.join(path)}
        </div>
    """)

def add_quick_access():
    """Add quick access menu."""
    put_buttons(['Home', 'Emergency', 'Settings'], 
                onclick=[show_main_screen, add_emergency_support, show_settings])

def apply_responsive_styles():
    """Apply responsive design styles."""
    put_html("""
        <style>
            @media (max-width: 768px) {
                .button { width: 100%; }
                .text { font-size: 1.2em; }
                .input { height: 44px; }
            }
        </style>
    """)

def add_emergency_button():
    """Add emergency help button."""
    put_button("🚨 Emergency Help", 
               onclick=add_emergency_support,
               color='danger',
               position='fixed')


def handle_error(error_type, message=None):
    """Centralized error handling."""
    error_messages = {
        'auth': "خطأ في المصادقة. يرجى تسجيل الدخول مرة أخرى.",
        'connection': "خطأ في الاتصال. تأكد من اتصالك بالإنترنت.",
        'timeout': "انتهت مهلة الطلب. يرجى المحاولة مرة أخرى.",
        'database': "خطأ في قاعدة البيانات. يرجى المحاولة مرة أخرى.",
        'unknown': "حدث خطأ غير متوقع. يرجى المحاولة مرة أخرى."
    }
    error_msg = message or error_messages.get(error_type, error_messages['unknown'])
    logging.error(f"Error ({error_type}): {error_msg}")
    popup("خطأ", error_msg)

def add_navigation_bar():
    """Add consistent navigation bar."""
    put_html("""
        <nav class="nav-bar">
            <div class="nav-buttons">
                <button onclick="window.history.back()">رجوع</button>
                <button onclick="window.location.href='/'">الرئيسية</button>
            </div>
            <div class="breadcrumb"></div>
        </nav>
        <style>
            .nav-bar {
                position: fixed;
                top: 0;
                width: 100%;
                background: #fff;
                padding: 10px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                z-index: 1000;
                direction: rtl;
            }
        </style>
    """)

def check_session_timeout():
    """Check and handle session timeout."""
    if session_manager.is_session_expired():
        popup("تنبيه", "انتهت الجلسة. الرجاء تسجيل الدخول مرة أخرى")
        handle_logout()
        return False
    
    if session_manager.is_session_expiring_soon():
        if actions("ستنتهي الجلسة قريباً. هل تريد التمديد؟", ["نعم", "لا"]) == "نعم":
            session_manager.extend_session()
    return True

@contextmanager
def show_loading_state():
    """Show loading state with better feedback."""
    loading_id = f"loading_{random.randint(1000, 9999)}"
    try:
        put_html(f"""
            <div id="{loading_id}" class="loading-overlay">
                <div class="spinner"></div>
                <div class="loading-text">جاري التحميل...</div>
                <div class="progress-bar"></div>
                <button onclick="cancelOperation()">إلغاء</button>
            </div>
            <style>
                .loading-overlay {{
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    height: 100%;
                    background: rgba(255,255,255,0.9);
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                    justify-content: center;
                    z-index: 9999;
                }}
                .spinner {{
                    width: 50px;
                    height: 50px;
                    border: 5px solid #f3f3f3;
                    border-top: 5px solid #3498db;
                    border-radius: 50%;
                    animation: spin 1s linear infinite;
                }}
                @keyframes spin {{
                    0% {{ transform: rotate(0deg); }}
                    100% {{ transform: rotate(360deg); }}
                }}
            </style>
        """)
        yield
    finally:
        run_js(f"document.getElementById('{loading_id}').remove()")



def add_navigation_controls():
    """Add enhanced navigation controls."""
    put_html("""
        <nav class="nav-bar">
            <div class="nav-left">
                <button onclick="window.history.back()">رجوع</button>
                <button onclick="window.location.href='/'">الرئيسية</button>
            </div>
            <div class="nav-center">
                <div class="breadcrumb"></div>
            </div>
            <div class="nav-right">
                <button onclick="showHelp()">مساعدة</button>
                <button onclick="showEmergencyContacts()" class="emergency-btn">طوارئ</button>
            </div>
            <style>
                .nav-bar {
                    position: fixed;
                    top: 0;
                    left: 0;
                    width: 100%;
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    padding: 10px 20px;
                    background: white;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    z-index: 1000;
                }
                .emergency-btn {
                    background: #ff4444;
                    color: white;
                    font-weight: bold;
                }
            </style>
        </nav>
    """)

def update_failed_attempts(username):
    """Update failed login attempts for user."""
    try:
        user_data = db_manager.get_user_data(username)
        if user_data:
            user_data['failed_attempts'] = user_data.get('failed_attempts', 0) + 1
            user_data['last_failed_attempt'] = datetime.now().isoformat()
            db_manager.save_user_data(username, user_data)
    except Exception as e:
        logging.error(f"Error updating failed attempts: {str(e)}")

def reset_failed_attempts(username):
    """Reset failed login attempts for user."""
    try:
        user_data = db_manager.get_user_data(username)
        if user_data:
            user_data['failed_attempts'] = 0
            user_data['last_failed_attempt'] = None
            db_manager.save_user_data(username, user_data)
    except Exception as e:
        logging.error(f"Error resetting failed attempts: {str(e)}")

def check_lockout_period(user_data):
    """Check if account is locked due to failed attempts."""
    try:
        failed_attempts = user_data.get('failed_attempts', 0)
        if failed_attempts >= 5:
            last_attempt = user_data.get('last_failed_attempt')
            if last_attempt:
                last_attempt_time = datetime.fromisoformat(last_attempt)
                if datetime.now() - last_attempt_time < timedelta(minutes=15):
                    return False
        return True
    except Exception as e:
        logging.error(f"Error checking lockout period: {str(e)}")
        return True

class DataValidator:
    @staticmethod
    def validate_user_data(user_data):
        """Validate user data before saving to database."""
        if len(user_data['username']) < 3:
            raise ValueError("اسم المستخدم يجب أن يكون 3 أحرف على الأقل")
        if len(user_data['password']) < 8:
            raise ValueError("كلمة المرور يجب أن تكون 8 أحرف على الأقل")
        if not re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', user_data['email']):
            raise ValueError("البريد الإلكتروني غير صالح")
        return True
        
    @staticmethod
    def sanitize_input(data):
        """Sanitize input data before database operations."""
        if isinstance(data, str):
            return re.sub(r'[<>\'\"&]', '', data)
        elif isinstance(data, dict):
            return {k: DataValidator.sanitize_input(v) for k, v in data.items()}
        return data

data_validator = DataValidator()
def test_database_connection():
    """Test database connection and configuration."""
    try:
        logging.info("Testing database connection...")
        logging.info(f"Database URL: {db.database_url}")
        
        test = db.child("users").shallow().get()
        if test is None:
            logging.error("Database test returned None")
            return False
            
        logging.info("Database connection successful")
        return True
        
    except Exception as e:
        logging.error(f"Database connection test failed: {str(e)}")
        logging.error(f"Error type: {type(e)}")
        return False



def verify_firebase_config():
    """Verify Firebase configuration."""
    try:
       
        config = {
            "apiKey": "your-api-key",
            "authDomain": "yourmind-default-rtdb.europe-west1.firebasedatabase.app",
            "databaseURL": "https://yourmind-default-rtdb.europe-west1.firebasedatabase.app",
            "storageBucket": "yourmind.appspot.com"
        }
        
       
        logging.info("Initializing Firebase...")
        firebase = pyrebase.initialize_app(config)
        db = firebase.database()
        
        
        logging.info("Testing database connection...")
        test = db.child("users").get()
        
        if test is None:
            logging.error("Database test returned None")
            return False, None
            
        logging.info("Firebase configuration verified successfully")
        return True, db
        
    except Exception as e:
        logging.error(f"Firebase configuration error: {str(e)}")
        return False, None

class UIManager:
    def __init__(self):
        self.current_user = None
        self.current_role = None
        self.is_logged_in = False

    def set_user(self, username, role):
        self.current_user = username
        self.current_role = role
        self.is_logged_in = True

    def clear_user(self):
        self.current_user = None
        self.current_role = None
        self.is_logged_in = False

    def get_user(self):
        return self.current_user
    
    def get_role(self):
        return self.current_role
    
    def is_authenticated(self):
        return self.is_logged_in


ui_manager = UIManager()

def request_new_appointment():
    """طلب موعد جديد."""
    clear()
    try:
        if not hasattr(session_storage, 'user'):
            popup("خطأ", "الرجاء تسجيل الدخول أولاً")
            return show_login_screen()

        username = session_storage.user
        put_markdown("# طلب موعد جديد")

        
        doctors = []
        doctors_ref = db.child("users").get()
        if doctors_ref:
            for doc in doctors_ref.each():
                doc_data = doc.val()
                if doc_data.get('role') == 'doctor' and doc_data.get('approved', False):
                    doctors.append({
                        'id': doc.key(),
                        'name': doc_data.get('username', 'طبيب غير معروف')
                    })

        if not doctors:
            popup("تنبيه", "لا يوجد أطباء متاحين حالياً")
            return view_appointments()

        
        data = input_group("طلب موعد جديد", [
            select('اختر الطبيب', [{'label': d['name'], 'value': d['id']} for d in doctors], name='doctor'),
            input('التاريخ المطلوب', type=DATE, name='date'),
            input('الوقت المطلوب', type=TIME, name='time'),
            textarea('ملاحظات', name='notes', placeholder='أي ملاحظات إضافية؟')
        ])

        if data:
           
            appointment_data = {
                'patient_username': username,
                'date': data['date'],
                'time': data['time'],
                'notes': data['notes'],
                'status': 'معلق',
                'created_at': datetime.now().isoformat()
            }

            db.child("appointments").child(data['doctor']).push(appointment_data)
            popup("تم", "تم إرسال طلب الموعد بنجاح")
            return view_appointments()

    except Exception as e:
        print(f"Request appointment error: {str(e)}")
        popup("خطأ", "حدث خطأ في طلب الموعد")
        return view_appointments()

def show_available_doctors(search_query=''):
    """عرض الأطباء المتاحين."""
    try:
        clear_scope('search_results')
        
       
        put_row([
            put_select('specialty_filter', options=[
                {'label': 'كل التخصصات', 'value': 'all'},
                {'label': 'نفسي', 'value': 'psychiatrist'},
                {'label': 'استشاري نفسي', 'value': 'consultant'},
                {'label': 'معالج نفسي', 'value': 'therapist'},
                {'label': 'أخصائي نفسي', 'value': 'psychologist'},
                {'label': 'معالج سلوكي', 'value': 'behavioral_therapist'}
            ], label='التخصص', value='all'),
            
            put_select('governorate_filter', 
                      options=governorate,
                      label='المحافظة', 
                      value='all')
        ], scope='search_results')

       
        doctors = db.child("users").get()
        found_doctors = []
        
        if doctors:
            for doc in doctors.each():
                doc_data = doc.val()
                if (doc_data and 
                    doc_data.get('role') == 'doctor' and 
                    doc_data.get('approved', False)):
                    
                   
                    search_in = [
                        doc_data.get('username', ''),
                        doc_data.get('specialty', ''),
                        doc_data.get('governorate', ''),
                        doc_data.get('address', '')
                    ]
                    
                    matches_search = not search_query or any(
                        search_query.lower() in field.lower() 
                        for field in search_in if field
                    )
                    
                    specialty = pin.specialty_filter
                    governorate = pin.governorate_filter
                    
                    matches_specialty = (specialty == 'all' or 
                                      doc_data.get('specialty') == specialty)
                    matches_governorate = (governorate == 'all' or 
                                        doc_data.get('governorate') == governorate)
                    
                    if matches_search and matches_specialty and matches_governorate:
                        found_doctors.append({
                            'key': doc.key(),
                            'data': doc_data
                        })
        
        if found_doctors:
            for doc in found_doctors:
                with use_scope('search_results'):
                   
                    put_markdown("---")  
                    
                   
                    put_row([
                        put_markdown(f"""
                            ### د. {doc['data'].get('username', 'غير معروف')}
                            **التخصص:** {doc['data'].get('specialty', 'غير محدد')}
                            **المحافظة:** {doc['data'].get('governorate', 'غير محدد')}
                            """),
                        put_column([
                            put_button('عرض الملف الشخصي', 
                                     onclick=lambda d=doc['key']: view_doctor_profile(d.get('username')),
                                     color='info'),
                            put_button('طلب موعد',
                                     onclick=lambda d=doc['key']: request_appointment(d.get('username')),
                                     color='primary')
                        ])
                    ], size='80% 20%')
                    
                   
                    put_grid([
                        [
                            put_markdown(f"🏥 **التخصص:** {doc['data'].get('specialty', 'غير متوفر')}"),
                            put_markdown(f"📍 **المحافظة:** {doc['data'].get('governorate', 'غير متوفر')}")
                        ],
                        [
                            put_markdown(f"⏰ **ساعات العمل:** {doc['data'].get('working_hours', 'غير متوفر')}"),
                            put_markdown(f"💰 **رسوم الكشف:** {doc['data'].get('fees', 'غير متوفر')}")
                        ]
                    ])
                    
                   
                    if doc['data'].get('about'):
                        put_markdown(f"ℹ️ **نبذة:** {doc['data'].get('about')}")
                    
                   
                    put_row([
                        put_button('📅 حجز موعد', 
                                 onclick=lambda d=doc['key']: request_new_appointment(d),  
                                 color='primary'),
                        put_button('💬 مراسلة', 
                                 onclick=lambda d=doc['key']: send_message(d),
                                 color='success')
                    ])
        else:
            put_markdown("### 🔍 لا يوجد أطباء متطابقين مع معايير البحث", scope='search_results')
            put_markdown("جرب تغيير كلمات البحث أو الفلترة", scope='search_results')

    except Exception as e:
        print(f"Search error: {str(e)}")
        put_text("⚠️ حدث خطأ في عرض الأطباء", scope='search_results')

def view_doctor_profile(doctor_key):
    """عرض الملف الشخصي للطبيب."""
    clear()
    try:
        doctor_data = db.child("users").child(doctor_key).get().val()
        if not doctor_data:
            popup("خطأ", "لم يتم العثور على بيانات الطبيب")
            return show_patient_screen()

        put_button('رجوع', onclick=show_patient_screen)
        put_markdown(f"# د. {doctor_data.get('username', 'غير معروف')}")
        
       
        put_markdown("## المعلومات الأساسية")
        put_grid([
            [put_markdown(f"**التخصص:** {doctor_data.get('specialty', 'غير متوفر')}"),
             put_markdown(f"**المحافظة:** {doctor_data.get('governorate', 'غير متوفر')}")],
            [put_markdown(f"**ساعات العمل:** {doctor_data.get('working_hours', 'غير متوفر')}"),
             put_markdown(f"**رسوم الكشف:** {doctor_data.get('fees', 'غير متوفر')}")]
        ])
        
       
        put_markdown("## معلومات الاتصال")
        put_markdown(f"**العنوان:** {doctor_data.get('address', 'غير متوفر')}")
        put_markdown(f"**البريد الإلكتروني:** {doctor_data.get('email', 'غير متوفر')}")
        put_markdown(f"**الهاتف:** {doctor_data.get('phone', 'غير متوفر')}")
        
        
        put_button('حجز موعد', onclick=lambda: request_new_appointment(doctor_key), color='primary')

    except Exception as e:
        print(f"Error viewing doctor profile: {str(e)}")
        popup("خطأ", "حدث خطأ في عرض الملف الشخصي")
        return show_patient_screen()


def request_new_appointment(doctor_key):
    """طلب موعد جديد."""
    clear()
    try:
        if not hasattr(session_storage, 'user'):
            popup("خطأ", "الرجاء تسجيل الدخول أولاً")
            return show_login_screen()

        username = session_storage.user
        
        doctor_data = db.child("users").child(doctor_key).get().val()
        if not doctor_data:
            popup("خطأ", "لم يتم العثور على بيانات الطبيب")
            return show_patient_screen()

        put_markdown(f"# طلب موعد مع د. {doctor_data.get('username', 'غير معروف')}")
        put_button('رجوع', onclick=show_patient_screen)

       
        data = input_group("تفاصيل الموعد", [
            input('التاريخ المطلوب', type=DATE, name='date'),
            input('الوقت المطلوب', type=TIME, name='time'),
            textarea('ملاحظات', name='notes', placeholder='أي ملاحظات إضافية؟')
        ])

        if data:
          
            appointment_data = {
                'patient_username': username,
                'doctor_id': doctor_key,
                'date': data['date'],
                'time': data['time'],
                'notes': data['notes'],
                'status': 'معلق',
                'created_at': datetime.now().isoformat()
            }

            db.child("appointments").child(doctor_key).push(appointment_data)
            popup("تم", "تم إرسال طلب الموعد بنجاح")
            return view_appointments()

    except Exception as e:
        print(f"Request appointment error: {str(e)}")
        popup("خطأ", "حدث خطأ في طلب الموعد")
        return show_patient_screen()
from flask import Flask
from pywebio.platform.flask import webio_view
from pywebio.session import set_env
import logging
import sys

app = Flask(__name__)

def main():
    """Main application entry point."""
    try:
        set_env(
            title="YOUR MIND",
            output_animation=False,
            auto_scroll_bottom=True
        )
        show_main_screen()
    except Exception as e:
        logging.error(f"Main error: {str(e)}")
        put_markdown("# حدث خطأ في تشغيل التطبيق")

# التأكد من الاتصال بقاعدة البيانات قبل تشغيل التطبيق
if not test_database_connection():
    print("❌ فشل الاتصال بقاعدة البيانات، سيتم إيقاف التشغيل")
    sys.exit(1)

# دمج PyWebIO مع Flask
app.add_url_rule("/", "webio", webio_view(main), methods=["GET", "POST", "OPTIONS"])
if __name__ == '__main__':
    logging.basicConfig(
        filename='app.log',
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

    try:
        print("🚀 Starting Flask server on port 5000...")
        app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)  # منع إعادة التشغيل التلقائي
    except Exception as e:
        print(f"❌ Failed to start Flask server: {str(e)}")
        sys.exit(1)


from flask import Flask, request, jsonify
