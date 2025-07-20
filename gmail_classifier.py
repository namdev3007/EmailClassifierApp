import tkinter as tk
from tkinter import ttk, scrolledtext
import base64
import os
import re
import joblib
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Load mô hình và vectorizer
model = joblib.load("spam_classifier_model.pkl")
vectorizer = joblib.load("tfidf_vectorizer.pkl")

def clean_text(text):
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = re.sub(r"[^a-z\s]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

def predict_email(text):
    cleaned = clean_text(text)
    vec = vectorizer.transform([cleaned])
    return "Spam" if model.predict(vec)[0] == 1 else "Ham"

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def fetch_and_classify():
    output_box.delete('1.0', tk.END)  # Xóa kết quả cũ
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', maxResults=5).execute()
        messages = results.get('messages', [])

        if not messages:
            output_box.insert(tk.END, "Không tìm thấy email nào.\n")
            return

        for msg in messages:
            msg_data = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = msg_data.get('payload', {})
            parts = payload.get('parts', [])
            body = ''

            if parts:
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        data = part.get('body', {}).get('data', '')
                        body += base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8', errors='ignore')
            else:
                data = payload.get('body', {}).get('data', '')
                body += base64.urlsafe_b64decode(data.encode('ASCII')).decode('utf-8', errors='ignore')

            subject = next((h['value'] for h in payload['headers'] if h['name'] == 'Subject'), 'Không tiêu đề')
            result = predict_email(body)
            output_box.insert(tk.END, f"📩 Tiêu đề: {subject}\n🔍 Phân loại: {result}\n{'-'*50}\n")

    except Exception as e:
        output_box.insert(tk.END, f"Lỗi: {str(e)}\n")

# === Giao diện Tkinter ===
app = tk.Tk()
app.title("Gmail Spam Classifier")
app.geometry("700x500")

title_label = ttk.Label(app, text="📬 Gmail Email Classifier", font=("Arial", 16))
title_label.pack(pady=10)

fetch_btn = ttk.Button(app, text="📥 Phân loại 5 email gần nhất", command=fetch_and_classify)
fetch_btn.pack(pady=5)

output_box = scrolledtext.ScrolledText(app, width=80, height=20, font=("Courier", 10))
output_box.pack(pady=10)

app.mainloop()
