import os
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes: Izin untuk membaca dan menulis file
SCOPES = ['https://www.googleapis.com/auth/drive.file']

def get_drive_service():
    """Menangani otentikasi Google Drive (Login sekali, simpan token)"""
    creds = None
    # Cek apakah sudah pernah login sebelumnya (token.json ada)
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Jika tidak ada login atau login kadaluarsa
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # PENTING: credentials.json harus ada di folder project
            if not os.path.exists('credentials.json'):
                print("Error: File credentials.json tidak ditemukan.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            # Run local server untuk login pertama kali
            creds = flow.run_local_server(port=0)
        
        # Simpan token agar besok tidak perlu login lagi
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def upload_file_background(filepath, parent_window=None):
    """Fungsi wrapper untuk dijalankan di Thread terpisah"""
    thread = threading.Thread(target=_upload_process, args=(filepath, parent_window))
    thread.daemon = True # Agar thread mati jika aplikasi ditutup
    thread.start()

def _upload_process(filepath, parent_window):
    """Logika upload sesungguhnya"""
    filename = os.path.basename(filepath)
    print(f"[Drive] Memulai upload untuk: {filename}")
    
    try:
        service = get_drive_service()
        if not service:
            print("[Drive] Gagal inisialisasi service.")
            return

        file_metadata = {'name': filename}
        media = MediaFileUpload(filepath, mimetype='application/pdf')
        
        # Eksekusi Upload
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()
        
        print(f"[Drive] Sukses! File ID: {file.get('id')}")
        # Opsional: Bisa tambahkan notifikasi GUI disini jika diinginkan
        
    except Exception as e:
        # ERROR HANDLING UTAMA
        # Jika internet mati atau api error, kode masuk sini.
        # Kita hanya print error, JANGAN crash aplikasi.
        print(f"[Drive] Gagal Upload (Mode Offline Tetap Aman): {e}")