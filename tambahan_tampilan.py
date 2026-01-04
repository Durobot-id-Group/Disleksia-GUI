def save_to_pdf(self):
        """Menyimpan PDF dengan Kolom Nama Manual + Visualisasi Stacked"""
        # Import lokal
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

            # ================= HEADER UTAMA =================
            draw_box(w/2 - 150, h - 80, 300, 50, COLOR_TITLE_BG, radius=15)
            draw_centered_text("HASIL DIAGNOSA", w/2, h - 68, size=22)
            
            c.setFont("Helvetica", 10)
            c.setFillColor(HexColor("#636e72"))
            c.drawCentredString(w/2, h - 100, f"Tanggal: {datetime.now().strftime('%d %B %Y')}")

            # ================= KOLOM KIRI =================
            LEFT_X = 50
            COL_WIDTH = 240
            
            # --- BAGIAN 0: IDENTITAS PESERTA (MANUAL PRINT) ---
            # Kita taruh ini di paling atas kolom kiri (posisi awal kolom kiri sebelumnya)
            
            # Header Identitas
            ID_HEADER_Y = h - 150
            draw_box(LEFT_X + 20, ID_HEADER_Y, 200, 30, COLOR_HEADER_BG, radius=10)
            draw_centered_text("Identitas Peserta", LEFT_X + 120, ID_HEADER_Y + 8, size=12)
            
            # Kotak Isi Nama (Titik-titik manual)
            ID_BOX_Y = h - 200
            draw_box(LEFT_X, ID_BOX_Y, COL_WIDTH, 40, COLOR_CONTENT_BG, radius=10)
            
            # Teks Nama
            c.setFont("Helvetica-Bold", 12)
            c.setFillColor(COLOR_TEXT)
            c.drawString(LEFT_X + 15, ID_BOX_Y + 15, "Nama : ...............................................")

            # --- BAGIAN 1: VISUALISASI GELOMBANG ---
            # Kita turunkan posisinya sekitar 80 pixel ke bawah karena ada kotak nama
            VIS_HEADER_Y = h - 250
            draw_box(LEFT_X + 20, VIS_HEADER_Y, 200, 35, COLOR_HEADER_BG, radius=10)
            draw_centered_text("Visualisasi Gelombang", LEFT_X + 120, VIS_HEADER_Y + 8, size=14)
            
            # --- GENERATE PLOT STACKED ---
            fig = plt.figure(figsize=(5, 6)) 
            
            t = ar['t']
            fs = ar.get('fs', 256)
            samples_to_show = int(2 * fs) 
            
            if len(t) > samples_to_show:
                t_slice = t[:samples_to_show]
            else:
                t_slice = t
                samples_to_show = len(t)

            filtered = ar['filtered']
            
            bands_data = [
                ("Delta", filtered.get("Delta (0.5–4 Hz)", [])[:samples_to_show], '#1f77b4'),
                ("Theta", filtered.get("Theta (4–8 Hz)", [])[:samples_to_show], '#ff7f0e'),
                ("Alpha", filtered.get("Alpha (8–13 Hz)", [])[:samples_to_show], '#2ca02c'),
                ("Beta",  filtered.get("Beta (13–30 Hz)", [])[:samples_to_show],  '#d62728'),
                ("Gamma", filtered.get("Gamma (30–45 Hz)", [])[:samples_to_show], '#9467bd')
            ]

            for i, (name, sig, color) in enumerate(bands_data):
                ax = fig.add_subplot(5, 1, i+1)
                if len(sig) > 0:
                    ax.plot(t_slice, sig, color=color, lw=1.2)
                ax.axis('off')
                ax.text(-0.02, 0.5, name, transform=ax.transAxes, 
                        fontsize=11, fontweight='bold', 
                        verticalalignment='center', horizontalalignment='right', color='#2d3436')

            plt.tight_layout()
            
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=120, bbox_inches='tight', pad_inches=0.1)
            img_buf.seek(0)
            
            # Tempel Gambar (Posisi Y juga diturunkan)
            # Y = h - 550 (karena tingginya 280)
            c.drawImage(reportlab.lib.utils.ImageReader(img_buf), LEFT_X - 10, h - 550, width=COL_WIDTH + 20, height=280)
            plt.close(fig)

            # --- BAGIAN 2: SARAN ---
            # Geser posisi Y lebih ke bawah lagi
            REC_Y_HEADER = h - 580
            draw_box(LEFT_X + 20, REC_Y_HEADER, 200, 35, COLOR_HEADER_BG, radius=10)
            draw_centered_text("Saran & Rekomendasi", LEFT_X + 120, REC_Y_HEADER + 8, size=14)
            
            REC_Y = h - 750
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

            # ================= KOLOM KANAN (Tidak Berubah Posisi) =================
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
            
            # 2. Tampilkan Notifikasi Loading
            self.loading_popup = tk.Toplevel(self)
            self.loading_popup.title("Upload")
            self.loading_popup.geometry("300x100")
            
            x = self.winfo_rootx() + 50
            y = self.winfo_rooty() + 100
            self.loading_popup.geometry(f"+{x}+{y}")
            
            tk.Label(self.loading_popup, text="Menyimpan PDF lokal selesai.\nSedang upload ke Drive untuk QR Code...", font=("Arial", 10)).pack(expand=True)
            self.loading_popup.update()

            # 3. UPLOAD DRIVE
            drive_sync.upload_file_background(filename, callback_success=self.on_upload_success)
            
        except Exception as e:
            messagebox.showerror("Gagal Simpan PDF", str(e))
            if hasattr(self, 'loading_popup'): self.loading_popup.destroy()
