    
    def save_to_pdf(self):
        """Menyimpan PDF dengan Visualisasi Gelombang Terpisah (Stacked) + QR Code"""
        # Import lokal agar tidak error undefined
        import io
        import matplotlib.pyplot as plt
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok'):
            messagebox.showerror("Error", "Tidak ada data untuk disimpan.")
            return
        
        try:
            # 1. Setup File
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Hasil_Tes_{timestamp}.pdf"
            
            c = canvas.Canvas(filename, pagesize=A4)
            w, h = A4
            
            # --- PALET WARNA ---
            COLOR_TITLE_BG = HexColor("#7bed9f")
            COLOR_HEADER_BG = HexColor("#ffcccc")
            COLOR_CONTENT_BG = HexColor("#d1f2eb")
            COLOR_TEXT = HexColor("#2d3436")
            
            # Helper: Gambar Kotak Rounded
            def draw_box(x, y, width, height, color, radius=10):
                c.setFillColor(color)
                c.setStrokeColor(color)
                c.roundRect(x, y, width, height, radius, fill=1, stroke=0)

            # Helper: Text Tengah
            def draw_centered_text(text, x_center, y, font="Helvetica-Bold", size=14, color=HexColor("#000000")):
                c.setFont(font, size)
                c.setFillColor(color)
                c.drawCentredString(x_center, y, text)

            # ================= HEADER =================
            draw_box(w/2 - 150, h - 80, 300, 50, COLOR_TITLE_BG, radius=15)
            draw_centered_text("HASIL DIAGNOSA", w/2, h - 68, size=22)
            
            c.setFont("Helvetica", 10)
            c.setFillColor(HexColor("#636e72"))
            c.drawCentredString(w/2, h - 100, f"Tanggal: {datetime.now().strftime('%d %B %Y')}")

            # ================= KOLOM KIRI =================
            LEFT_X = 50
            COL_WIDTH = 240
            
            # --- BAGIAN 1: HASIL SENSOR (VISUALISASI GELOMBANG) ---
            # Header
            draw_box(LEFT_X + 20, h - 150, 200, 35, COLOR_HEADER_BG, radius=10)
            draw_centered_text("Visualisasi Gelombang", LEFT_X + 120, h - 142, size=14)
            
            # --- GENERATE PLOT STACKED (MIRIP REFERENSI) ---
            # Kita buat figur agak tinggi agar muat 5 gelombang vertikal
            fig = plt.figure(figsize=(5, 6)) 
            
            # Data Preparation
            t = ar['t']
            fs = ar.get('fs', 256)
            
            # TEKNIK "ZOOM": Ambil 2 detik saja agar gelombang terlihat detil & tidak hitam blok
            samples_to_show = int(2 * fs) 
            
            if len(t) > samples_to_show:
                t_slice = t[:samples_to_show]
            else:
                t_slice = t
                samples_to_show = len(t)

            # Ambil sinyal terfilter
            filtered = ar['filtered']
            
            # Mapping Nama Pendek ke Data & Warna
            # Menggunakan .get() dengan default array kosong agar tidak error jika key beda
            bands_data = [
                ("Delta", filtered.get("Delta (0.5–4 Hz)", [])[:samples_to_show], '#1f77b4'),  # Biru
                ("Theta", filtered.get("Theta (4–8 Hz)", [])[:samples_to_show], '#ff7f0e'),   # Oranye
                ("Alpha", filtered.get("Alpha (8–13 Hz)", [])[:samples_to_show], '#2ca02c'),   # Hijau
                ("Beta",  filtered.get("Beta (13–30 Hz)", [])[:samples_to_show],  '#d62728'),   # Merah
                ("Gamma", filtered.get("Gamma (30–45 Hz)", [])[:samples_to_show], '#9467bd')    # Ungu
            ]

            # Loop Membuat 5 Subplot Vertikal
            for i, (name, sig, color) in enumerate(bands_data):
                # 5 Baris, 1 Kolom, Posisi ke i+1
                ax = fig.add_subplot(5, 1, i+1)
                
                # Plot Sinyal (Cek jika data ada)
                if len(sig) > 0:
                    ax.plot(t_slice, sig, color=color, lw=1.2)
                
                # Styling Minimalis (Hapus Kotak & Angka)
                ax.axis('off')
                
                # Tambahkan Label Nama di Kiri Sinyal
                # Koordinat (-0.02, 0.5) artinya di kiri luar area plot, tengah vertikal
                ax.text(-0.02, 0.5, name, transform=ax.transAxes, 
                        fontsize=11, fontweight='bold', 
                        verticalalignment='center', horizontalalignment='right', color='#2d3436')

            plt.tight_layout()
            
            # Simpan ke Memory Buffer
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=120, bbox_inches='tight', pad_inches=0.1)
            img_buf.seek(0)
            
            # Tempel Gambar ke PDF (Sesuaikan posisi Y agar tidak menabrak header)
            # Posisi Y: h - 450 (menyesuaikan tinggi gambar 280-300px)
            c.drawImage(reportlab.lib.utils.ImageReader(img_buf), LEFT_X - 10, h - 450, width=COL_WIDTH + 20, height=280)
            plt.close(fig)

            # --- BAGIAN 2: SARAN ---
            # Geser posisi Y agak ke bawah karena gambar grafik sekarang lebih tinggi (Stacked)
            REC_Y_HEADER = h - 480
            draw_box(LEFT_X + 20, REC_Y_HEADER, 200, 35, COLOR_HEADER_BG, radius=10)
            draw_centered_text("Saran & Rekomendasi", LEFT_X + 120, REC_Y_HEADER + 8, size=14)
            
            REC_Y = h - 650
            REC_H = 150
            draw_box(LEFT_X, REC_Y, COL_WIDTH, REC_H, COLOR_CONTENT_BG, radius=15)
            
            an = ar['analysis']
            rekomendasi_text = an['rekomendasi']
            
            c.setFont("Helvetica", 11)
            c.setFillColor(COLOR_TEXT)
            text_obj = c.beginText(LEFT_X + 15, REC_Y + REC_H - 25)
            
            words = rekomendasi_text.split()
            line = ""
            for word in words:
                if c.stringWidth(line + word, "Helvetica", 11) < (COL_WIDTH - 30):
                    line += word + " "
                else:
                    text_obj.textLine(line)
                    line = word + " "
            text_obj.textLine(line)
            c.drawText(text_obj)

            # ================= KOLOM KANAN =================
            RIGHT_X = 310
            
            draw_box(RIGHT_X + 20, h - 150, 200, 35, COLOR_TITLE_BG, radius=10)
            draw_centered_text("Keterangan", RIGHT_X + 120, h - 142, size=16)

            # --- SKOR ---
            Y_POS = h - 210
            draw_box(RIGHT_X + 40, Y_POS, 160, 30, COLOR_HEADER_BG, radius=8)
            draw_centered_text("Hasil Skor", RIGHT_X + 120, Y_POS + 8, size=12)
            
            Y_POS -= 80
            draw_box(RIGHT_X, Y_POS, COL_WIDTH, 70, COLOR_CONTENT_BG, radius=15)
            
            score_val = an['confidence_score']
            kriteria_num = an['kriteria_terpenuhi']
            
            if kriteria_num >= 6:
                status_txt = "TINGGI (Kuat)"
                color_status = HexColor("#d63031")
            elif kriteria_num >= 4:
                status_txt = "SEDANG (Indikasi)"
                color_status = HexColor("#e17055")
            else:
                status_txt = "NORMAL"
                color_status = HexColor("#00b894")
            
            c.setFont("Helvetica-Bold", 28)
            c.setFillColor(color_status)
            c.drawCentredString(RIGHT_X + 120, Y_POS + 35, f"{score_val:.0f}")
            c.setFont("Helvetica", 12)
            c.setFillColor(COLOR_TEXT)
            c.drawCentredString(RIGHT_X + 120, Y_POS + 15, status_txt)

            # --- DIAGNOSA ---
            Y_POS -= 60
            draw_box(RIGHT_X + 40, Y_POS, 160, 30, COLOR_HEADER_BG, radius=8)
            draw_centered_text("Status Diagnosa", RIGHT_X + 120, Y_POS + 8, size=12)
            
            Y_POS -= 80
            draw_box(RIGHT_X, Y_POS, COL_WIDTH, 70, COLOR_CONTENT_BG, radius=15)
            
            diagnosis_final = "TERINDIKASI DISLEKSIA" if kriteria_num >= 6 else "NORMAL"
            
            font_diag_size = 16 if len(diagnosis_final) < 20 else 14
            c.setFont("Helvetica-Bold", font_diag_size)
            c.setFillColor(COLOR_TEXT)
            c.drawCentredString(RIGHT_X + 120, Y_POS + 35, diagnosis_final)

            # --- DETAIL KRITERIA ---
            Y_POS -= 200
            draw_box(RIGHT_X, Y_POS, COL_WIDTH, 180, HexColor("#f1f2f6"), radius=15)
            
            c.setFont("Helvetica-Bold", 10)
            c.setFillColor(COLOR_TEXT)
            c.drawString(RIGHT_X + 15, Y_POS + 160, "Detail Indikator:")
            
            c.setFont("Helvetica", 9)
            text_y = Y_POS + 140
            for k, v in an['kriteria'].items():
                if v['passed']:
                    marker = "(+)"
                    c.setFillColor(HexColor("#d63031"))
                else:
                    marker = "(-)"
                    c.setFillColor(HexColor("#2d3436"))
                
                desc = v['description'][:35]
                c.drawString(RIGHT_X + 15, text_y, f"{marker} {desc}")
                text_y -= 15

            # FOOTER
            c.setFont("Helvetica-Oblique", 8)
            c.setFillColor(HexColor("#b2bec3"))
            c.drawCentredString(w/2, 30, "Dokumen ini digenerate otomatis oleh Sistem Deteksi Dini Disleksia")

            c.save()
            
            # 2. Tampilkan Notifikasi Loading (Agar user tahu sedang proses upload)
            self.loading_popup = tk.Toplevel(self)
            self.loading_popup.title("Upload")
            self.loading_popup.geometry("300x100")
            tk.Label(self.loading_popup, text="Menyimpan PDF lokal selesai.\nSedang upload ke Drive untuk QR Code...", font=("Arial", 10)).pack(expand=True)
            self.loading_popup.update()

            # 3. UPLOAD DRIVE DENGAN CALLBACK QR CODE (PENTING!)
            # Ini akan memicu fungsi on_upload_success -> show_qr_popup
            drive_sync.upload_file_background(filename, callback_success=self.on_upload_success)
            
        except Exception as e:
            messagebox.showerror("Gagal Simpan PDF", str(e))
            if hasattr(self, 'loading_popup'): self.loading_popup.destroy()

    def on_upload_success(self, web_link):
        """Dipanggil otomatis saat upload selesai"""
        # Hancurkan popup loading
        if hasattr(self, 'loading_popup') and self.loading_popup.winfo_exists():
            self.loading_popup.destroy()
            
        # Tampilkan QR Code (gunakan after agar aman di thread UI)
        self.after(0, lambda: self.show_qr_popup(web_link))

    def show_qr_popup(self, url):
        """Menampilkan Popup QR Code"""
        import qrcode
        from PIL import Image, ImageTk

        qr_window = tk.Toplevel(self)
        qr_window.title("Scan Download")
        qr_window.geometry("320x380")
        qr_window.configure(bg="white")
        
        tk.Label(qr_window, text="UPLOAD BERHASIL!", font=("Arial", 14, "bold"), fg="#27ae60", bg="white").pack(pady=(10, 5))
        
        # QR Code Generation
        qr = qrcode.QRCode(box_size=8, border=2)
        qr.add_data(url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        img_qr = img_qr.resize((200, 200), Image.Resampling.LANCZOS)
        photo_qr = ImageTk.PhotoImage(img_qr)

        lbl_img = tk.Label(qr_window, image=photo_qr, bg="white")
        lbl_img.image = photo_qr
        lbl_img.pack(pady=5)
        
        tk.Label(qr_window, text="Scan untuk unduh PDF", font=("Arial", 10), bg="white").pack()

        tk.Button(qr_window, text="Tutup", command=qr_window.destroy, bg="#e74c3c", fg="white", width=15).pack(pady=10)

    def restart_test(self):
        self.controller.current_question = 1
        self.controller.frames[self.controller.frames[StartPage].__class__].load_label.config(text="File EEG: (belum dimuat)") # Reset label file (opsional)
        self.controller.show_frame(StartPage)



==========================================
#drive_sync.py
import os
import threading
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Scopes: Izin untuk membaca dan menulis file
SCOPES = ['https://www.googleapis.com/auth/drive.file']
FOLDER_ID = "19kFeBwffk4FtkGbxByhKrdbAsnHJXiNw"

def get_drive_service():
    """Menangani otentikasi Google Drive (Login sekali, simpan token)"""
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not os.path.exists('credentials.json'):
                print("Error: File credentials.json tidak ditemukan.")
                return None
            
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return build('drive', 'v3', credentials=creds)

def _upload_logic(pdf_path, folder_id=FOLDER_ID, make_public=True):
    """
    Logika asli upload (Synchronous/Blocking).
    Dipanggil oleh wrapper thread di bawah.
    """
    if not os.path.exists(pdf_path):
        print("❌ File tidak ditemukan:", pdf_path)
        return None

    try:
        service = get_drive_service()
        if not service: return None

        file_metadata = {
            'name': os.path.basename(pdf_path),
            'parents': [folder_id] if folder_id else []
        }

        media = MediaFileUpload(pdf_path, mimetype='application/pdf')

        # Upload file
        print(f"[Drive] Mulai upload {pdf_path}...")
        file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id, webViewLink, webContentLink'
        ).execute()

        file_id = file.get('id')
        view_link = file.get('webViewLink')
        
        # Buat Public (Agar bisa di-scan QR oleh siapa saja)
        if make_public:
            service.permissions().create(
                fileId=file_id,
                body={'type': 'anyone', 'role': 'reader'}
            ).execute()

        print("✅ Upload berhasil!")
        print("📄 File ID:", file_id)
        print("🔗 Link:", view_link)

        return view_link # Kembalikan Link untuk QR Code

    except Exception as e:
        print(f"❌ Error Upload: {e}")
        return None

def upload_file_background(pdf_path, callback_success=None):
    """
    Wrapper Thread-Safe untuk dipanggil dari UI.
    """
    def task():
        # Jalankan logika upload
        link = _upload_logic(pdf_path, FOLDER_ID, make_public=True)
        
        # Jika sukses dan ada callback (fungsi UI), panggil fungsi tersebut
        if link and callback_success:
            callback_success(link)

    # Jalankan di thread terpisah agar GUI tidak freeze
    t = threading.Thread(target=task)
    t.daemon = True
    t.start()

#=============================================================================


def show_qr_popup(self, url):
        """Menampilkan Popup QR Code Fullscreen dengan Tombol Tutup"""
        import qrcode
        from PIL import Image, ImageTk

        # Hapus popup loading jika masih ada
        if hasattr(self, 'loading_popup') and self.loading_popup.winfo_exists():
            self.loading_popup.destroy()

        # 1. Buat Window Baru
        qr_window = tk.Toplevel(self)
        qr_window.title("Scan Download")
        
        # 2. Set Fullscreen (Menyesuaikan ukuran layar berapapun)
        qr_window.attributes("-fullscreen", True)
        qr_window.configure(bg="white")
        
        # Frame utama agar isi berada di tengah
        main_frame = tk.Frame(qr_window, bg="white")
        main_frame.pack(expand=True, fill="both")

        # Judul
        tk.Label(main_frame, text="UPLOAD BERHASIL!", font=("Arial", 16, "bold"), fg="#27ae60", bg="white").pack(pady=(15, 5))
        
        # 3. Generate QR Code
        qr = qrcode.QRCode(box_size=10, border=1) # Border tipis agar muat
        qr.add_data(url)
        qr.make(fit=True)
        img_qr = qr.make_image(fill_color="black", back_color="white")
        
        # Resize QR agar pas di layar 3.5 inch (tinggi 320px)
        # Kita pakai ukuran 180x180 agar sisa ruang untuk tombol
        img_qr = img_qr.resize((180, 180), Image.Resampling.LANCZOS)
        photo_qr = ImageTk.PhotoImage(img_qr)

        lbl_img = tk.Label(main_frame, image=photo_qr, bg="white")
        lbl_img.image = photo_qr # PENTING: Simpan referensi gambar
        lbl_img.pack(pady=5)
        
        # Instruksi Kecil
        tk.Label(main_frame, text="Scan untuk unduh PDF", font=("Arial", 10), bg="white", fg="#7f8c8d").pack(pady=(0, 5))

        # 4. TOMBOL TUTUP (BESAR & JELAS)
        # tombol ditaruh di pack side bottom agar selalu di bawah
        btn_close = tk.Button(main_frame, text="TUTUP WINDOW", font=("Arial", 12, "bold"), 
                              bg="#e74c3c", fg="white", 
                              activebackground="#c0392b", activeforeground="white",
                              width=20, height=2, relief="flat",
                              command=qr_window.destroy) # Fungsi menutup window
        btn_close.pack(side="bottom", pady=15)
