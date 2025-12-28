import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from datetime import datetime
import io

# Import file buatan kita sendiri
from config import *
from hardware import EEGSerialLogger
from analysis import run_eeg_pipeline

# # ================== INIT AUDIO ==================
# pygame.mixer.init()

# Setup Audio (Pygame) tetap disini karena terkait UI/Experience
try:
    import pygame
    if 'SDL_AUDIODRIVER' not in os.environ:
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.music.set_volume(0.8)
except Exception:
    pygame = None

# ================== STOPWATCH CLASS ==================
class Stopwatch:
    def __init__(self, parent, label, on_tick=None):
        self.parent = parent
        self.label = label
        self.on_tick = on_tick
        self.elapsed_time = 0
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self._update()

    def stop(self):
        self.running = False

    def reset(self):
        self.elapsed_time = 0
        self.running = False
        self.label.config(text="00:00")

    def _update(self):
        if not self.running:
            return
        minutes = self.elapsed_time // 60
        seconds = int(self.elapsed_time % 60)
        self.label.config(text=f"{minutes:02d}:{seconds:02d}")
        self.elapsed_time += 1
        if self.on_tick:
            self.on_tick(self.elapsed_time)
        self.parent.after(1000, self._update)
        
# ================== MAIN APP/UI ==================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tes Disleksia (EEG + GUI)")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.destroy())
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.current_question = 1
        self.test_result = None
        self.eeg_filename = None
        self.analysis_results = None
        self.eeg_logger = None

        self.container = tk.Frame(self, bg="#f5f7fa")
        self.container.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.frames = {}
        for F in (IntroPage, StartPage, TestPage, ProcessPage, ResultPage):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame(IntroPage)
        self.frames[IntroPage].start_intro()

    def show_frame(self, page):
        self.frames[page].tkraise()

class IntroPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="nw")
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        self.logo_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.logo_frame.pack(expand=True, fill="both", pady=(12,8))
        self.logo_label = None
        self.load_company_logo()
        if self.logo_label is None:
            self.logo_text = tk.Label(self.logo_frame, text="TES DISLEKSIA", font=("Arial", 32, "bold"), bg="#f5f7fa", fg="#2c5aa0")
            self.logo_text.pack(expand=True)
        self.loading_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.loading_frame.pack(side="bottom", pady=15)
        self.progress_canvas = tk.Canvas(self.loading_frame, width=280, height=6, bg="#f5f7fa", highlightthickness=0)
        self.progress_canvas.pack()
        self.alpha = 0
        self.progress_value = 0
        self.progress_t = 0.0

    def load_company_logo(self):
        logo_paths = ["logo.ico","logo.png","logo.jpg","assets/logo.png","images/logo.png"]
        try:
            from PIL import Image, ImageTk
            for logo_path in logo_paths:
                if os.path.exists(logo_path):
                    img = Image.open(logo_path)
                    screen_width = self.controller.screen_width
                    screen_height = self.controller.screen_height
                    max_height = int(screen_height * 0.75)
                    max_width = int(screen_width * 0.85)
                    ratio = min(max_width / img.width, max_height / img.height)
                    new_size = (int(img.width * ratio * 0.9), int(img.height * ratio * 0.9))
                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(img)
                    self.logo_label = tk.Label(self.logo_frame, image=photo, bg="#f5f7fa")
                    self.logo_label.image = photo
                    self.logo_label.pack()
                    return
        except Exception: pass

    def on_canvas_configure(self, event):
        canvas_width = event.width
        canvas_height = event.height
        content_width = self.content_frame.winfo_reqwidth()
        content_height = self.content_frame.winfo_reqheight()
        x = max(0, (canvas_width - content_width) // 2)
        y = max(0, (canvas_height - content_height) // 2)
        self.canvas.coords(self.canvas_window, x, y)

    def start_intro(self):
        self.fade_in()
        self.animate_progress()

    def fade_in(self):
        if self.alpha < 1.0:
            self.alpha += 0.05
            self.after(30, self.fade_in)

    def animate_progress(self):
        if self.progress_t < 1.0:
            self.progress_t += 0.01
            eased = 1 - pow(2, -10 * self.progress_t)
            self.progress_value = eased * 100
            self.progress_canvas.delete("all")
            self.progress_canvas.create_rectangle(0,0,280,6, fill="#e1e8ed", outline="", width=0)
            progress_width = int(280 * (self.progress_value / 100))
            if progress_width > 0:
                self.progress_canvas.create_rectangle(0,0,progress_width,6, fill="#4a90e2", outline="", width=0)
            self.after(30, self.animate_progress)
        else:
            self.after(500, self.go_to_start)

    def go_to_start(self):
        self.controller.show_frame(StartPage)

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.title_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.title_frame.pack(pady=(0,5))
        self.title_label = tk.Label(self.title_frame, text="TES DISLEKSIA", font=("Arial", 14, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        self.title_label.pack(pady=(0,2))
        self.title_line = tk.Frame(self.title_frame, bg="#4a90e2", height=3)
        self.title_line.pack(fill="x", padx=30)
        self.desc_label = tk.Label(self.content_frame, text="Tekan tombol untuk memuat data EEG lalu mulai tes", font=("Arial", 11), bg="#f5f7fa", fg="#5a6c7d", wraplength=420)
        self.desc_label.pack(pady=12)
        
        self.button_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.button_frame.pack(pady=10)

        self.load_button = tk.Button(self.button_frame, text="Muat Data EEG (CSV)", font=("Arial", 12), bg="#6aa84f", fg="white", relief="flat", cursor="hand2", command=self.load_eeg)
        self.load_button.grid(row=0, column=0, padx=6)

        self.start_button = tk.Button(self.button_frame, text="MULAI TES", font=("Arial", 18, "bold"), bg="#4a90e2", fg="white", relief="flat", cursor="hand2", padx=24, pady=10, command=self.start_with_audio)
        self.start_button.grid(row=0, column=1, padx=6)

        self.load_label = tk.Label(self.content_frame, text="File EEG: (belum dimuat)", font=("Arial", 10), bg="#f5f7fa", fg="#5a6c7d")
        self.load_label.pack(pady=(6,0))

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def load_eeg(self):
        fname = filedialog.askopenfilename(title="Pilih file CSV EEG", filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if fname:
            self.controller.eeg_filename = fname
            self.load_label.config(text=f"File EEG: {os.path.basename(fname)}")

    def start_with_audio(self):
        if not self.controller.eeg_filename:
            try:
                csv_name = f"eeg_live_{int(time.time())}.csv"
                self.controller.eeg_filename = csv_name
                self.controller.eeg_logger = EEGSerialLogger(COM_PORT, BAUD_RATE, csv_name)
                self.controller.eeg_logger.start()
            except Exception as e:
                print("Logger error", e)

        try:
            if pygame:
                if os.path.exists("audio/soal 1.mp3"):
                    pygame.mixer.music.load("audio/soal 1.mp3")
                    pygame.mixer.music.play()
        except: pass

        self.check_audio_finished()

    def check_audio_finished(self):
        try:
            if pygame.mixer.music.get_busy():
                self.after(200, self.check_audio_finished)
            else:
                self.go_to_test()
        except:
            self.go_to_test()

    def go_to_test(self):
        self.controller.show_frame(TestPage)
        self.controller.frames[TestPage].start_test_sequence()

class TestPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        self.progress_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.progress_container.pack(pady=(0,12))
        self.progress_label = tk.Label(self.progress_container, text="Soal 1 dari {}".format(TOTAL_QUESTIONS), font=("Arial", 14, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        self.progress_label.pack()

        self.timer_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.timer_container.pack(pady=10)
        self.timer_frame = tk.Frame(self.timer_container, bg="white", highlightbackground="#4a90e2", highlightthickness=3)
        self.timer_frame.pack()
        self.label_timer = tk.Label(self.timer_frame, text="00:00", font=("Arial", 72, "bold"), bg="white", fg="#2c5aa0", padx=24, pady=12)
        self.label_timer.pack()
        
        self.question_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.question_container.pack(pady=(12,0))
        self.question_frame = tk.Frame(self.question_container, bg="#4a90e2")
        self.question_frame.pack()
        self.label_question = tk.Label(self.question_frame, text="Soal ke-1", font=("Arial", 20, "bold"), bg="#4a90e2", fg="white", padx=18, pady=8)
        self.label_question.pack()

        self.stopwatch = Stopwatch(self, self.label_timer, on_tick=self.on_tick)

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def start_test_sequence(self):
        self.controller.current_question = 1
        self.update_ui_labels()
        self.stopwatch.start()
    
    def update_ui_labels(self):
        q = self.controller.current_question
        self.progress_label.config(text=f"Soal {q} dari {TOTAL_QUESTIONS}")
        self.label_question.config(text=f"Soal ke-{q}")

    def on_tick(self, elapsed_time):
        current_limit = QUESTION_DURATION * self.controller.current_question
        if elapsed_time >= current_limit:
            self.next_question()

    def next_question(self):
        if self.controller.current_question < TOTAL_QUESTIONS:
            self.controller.current_question += 1
            self.update_ui_labels()
            try:
                if pygame:
                    f = f"audio/soal {self.controller.current_question}.mp3"
                    if os.path.exists(f):
                        pygame.mixer.music.load(f)
                        pygame.mixer.music.play()
            except: pass
        else:
            self.finish_test()

    def finish_test(self):
        try:
            if self.controller.eeg_logger:
                self.controller.eeg_logger.stop()
        except: pass
        
        self.stopwatch.stop()
        self.stopwatch.reset()
        
        try:
            if pygame and os.path.exists("audio/tes selesai.mp3"):
                pygame.mixer.music.load("audio/tes selesai.mp3")
                pygame.mixer.music.play()
        except: pass

        self.controller.show_frame(ProcessPage)
        self.controller.frames[ProcessPage].start_processing()

class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.title_label = tk.Label(self.content_frame, text="MEMPROSES HASIL", font=("Arial", 14, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        self.title_label.pack(pady=(0,6))
        self.dots_label = tk.Label(self.content_frame, text="Mohon tunggu sebentar...", font=("Arial", 16), bg="#f5f7fa", fg="#5a6c7d")
        self.dots_label.pack(pady=8)
        
        self.circle_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.circle_container.pack(pady=10)
        self.progress_canvas = tk.Canvas(self.circle_container, width=100, height=100, bg="#f5f7fa", highlightthickness=0)
        self.progress_canvas.pack()
        
        self.angle = 0
        self.is_processing = False

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def start_processing(self):
        self.is_processing = True
        self.animate_loading()
        threading.Thread(target=self.run_analysis_logic, daemon=True).start()

    def animate_loading(self):
        if not self.is_processing: return
        self.progress_canvas.delete("all")
        w, h = 100, 100
        start_ang = self.angle
        extent = 280
        self.progress_canvas.create_arc(10, 10, w-10, h-10, start=start_ang, extent=extent, style="arc", width=8, outline="#4a90e2")
        self.angle = (self.angle - 10) % 360
        self.after(50, self.animate_loading)

    def run_analysis_logic(self):
        time.sleep(2)
        
        fname = self.controller.eeg_filename
        if fname and os.path.exists(fname):
            res = run_eeg_pipeline(fname)
        else:
            res = {"ok": False, "message": "File EEG tidak ditemukan"}
        
        self.controller.analysis_results = res
        self.after(0, self.finish_processing)

    def finish_processing(self):
        self.is_processing = False
        self.controller.show_frame(ResultPage)
        self.controller.frames[ResultPage].display_results()

# ================== RESULT PAGE (USER-FRIENDLY VERSION) ==================

class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        
        # Container utama di tengah
        self.center_frame = tk.Frame(self, bg="#f5f7fa")
        self.center_frame.place(relx=0.5, rely=0.5, anchor="center")

        # Label Judul Kecil
        self.lbl_header = tk.Label(self.center_frame, text="HASIL ANALISIS AKHIR", font=("Arial", 14), bg="#f5f7fa", fg="#5a6c7d")
        self.lbl_header.pack(pady=(0, 20))

        # Label Hasil Utama (Besar)
        self.lbl_verdict = tk.Label(self.center_frame, text="...", font=("Arial", 48, "bold"), bg="#f5f7fa", fg="#333333")
        self.lbl_verdict.pack(pady=10)

        # Label Sub-keterangan
        self.lbl_sub = tk.Label(self.center_frame, text="...", font=("Arial", 12), bg="#f5f7fa", fg="#5a6c7d")
        self.lbl_sub.pack(pady=(0, 30))

        # Container Tombol
        self.btn_frame = tk.Frame(self.center_frame, bg="#f5f7fa")
        self.btn_frame.pack()

        # Tombol Rincian
        self.btn_detail = tk.Button(self.btn_frame, text="Lihat Rincian", font=("Arial", 11), 
                                    bg="#e1e8ed", fg="#333333", padx=15, pady=10, relief="flat", 
                                    command=self.open_details)
        self.btn_detail.grid(row=0, column=0, padx=5)

        # Tombol Simpan PDF (BARU)
        self.btn_pdf = tk.Button(self.btn_frame, text="Simpan PDF", font=("Arial", 11, "bold"), 
                                 bg="#f1c40f", fg="white", padx=15, pady=10, relief="flat", 
                                 command=self.save_to_pdf)
        self.btn_pdf.grid(row=0, column=1, padx=5)

        # Tombol Ulangi
        self.btn_restart = tk.Button(self.btn_frame, text="Ulangi Tes", font=("Arial", 11, "bold"), 
                                     bg="#4a90e2", fg="white", padx=15, pady=10, relief="flat", 
                                     command=self.restart_test)
        self.btn_restart.grid(row=0, column=2, padx=5)

    def display_results(self):
        """Menentukan tampilan Simple berdasarkan logika baru"""
        ar = self.controller.analysis_results
        
        if not ar or not ar.get('ok'):
            self.lbl_verdict.config(text="ERROR", fg="red")
            self.lbl_sub.config(text="Terjadi kesalahan analisis")
            return

        an = ar['analysis']
        score = an['kriteria_terpenuhi']

        # LOGIKA BARU:
        # Hanya Indikasi KUAT (skor >= 6) yang dianggap Disleksia.
        # Rendah & Sedang (skor < 6) dianggap Tidak Disleksia.
        
        if score >= 6:
            verdict_text = "DISLEKSIA"
            verdict_color = "#e06666" # Merah soft
            sub_text = "Terdeteksi indikasi kuat pola gelombang disleksia."
        else:
            verdict_text = "TIDAK DISLEKSIA"
            verdict_color = "#6aa84f" # Hijau
            sub_text = "Pola gelombang otak dalam batas normal."

        self.lbl_verdict.config(text=verdict_text, fg=verdict_color)
        self.lbl_sub.config(text=sub_text)

    def open_details(self):
        """Membuka jendela pop-up untuk detail teknis"""
        detail_window = tk.Toplevel(self)
        detail_window.title("Rincian Data Analisis")
        detail_window.geometry("700x600")
        detail_window.configure(bg="white")

        # Header Pop-up
        tk.Label(detail_window, text="Laporan Analisis Mendalam", font=("Arial", 16, "bold"), bg="white", fg="#2c5aa0").pack(pady=15)

        # Area Teks Laporan
        report_text = scrolledtext.ScrolledText(detail_window, width=80, height=20, font=("Consolas", 10))
        report_text.pack(padx=20, pady=10)

        # Isi Laporan (Mengambil data lengkap)
        ar = self.controller.analysis_results
        if ar and ar.get('ok'):
            an = ar['analysis']
            report_text.insert(tk.END, f"DIAGNOSIS SISTEM : {an['diagnosis']}\n")
            report_text.insert(tk.END, f"SKOR KEYAKINAN   : {an['confidence_score']:.1f}% ({an['confidence']})\n")
            report_text.insert(tk.END, "-"*60 + "\n")
            report_text.insert(tk.END, "DETAIL INDIKATOR BIOMARKER EEG:\n")
            
            for k, v in an['kriteria'].items():
                status = "[v] POSITIF" if v['passed'] else "[ ] NEGATIF"
                report_text.insert(tk.END, f"{status} : {v['description']}\n")
                report_text.insert(tk.END, f"             Nilai: {v['value']:.2f} (Threshold: {v['threshold']})\n")
            
            report_text.insert(tk.END, "-"*60 + "\n")
            # report_text.insert(tk.END, f"REKOMENDASI:\n{an['rekomendasi']}\n")
            
        report_text.config(state='disabled') # Read-only

        # Tombol Grafik di dalam Pop-up
        btn_plot = tk.Button(detail_window, text="Tampilkan Grafik Gelombang", font=("Arial", 12), 
                             bg="#4a90e2", fg="white", padx=15, pady=8, command=self.show_plots)
        btn_plot.pack(pady=10)

        tk.Button(detail_window, text="Tutup", command=detail_window.destroy, bg="#ddd", padx=10).pack(pady=5)

    def show_plots(self):
        """Menampilkan grafik terpisah per gelombang dengan Scrollbar untuk layar kecil"""
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok'): return
        
        try:
            t = ar['t']
            filtered = ar['filtered']
            
            # 1. Buat Jendela Baru (Toplevel)
            plot_window = tk.Toplevel(self)
            plot_window.title("Grafik Gelombang")
            # Set ukuran default agar pas di Raspi 3.5 inch (biasanya 480x320)
            # Kita buat sedikit lebih kecil dari full screen agar window bar terlihat
            plot_window.geometry("480x300") 
            
            # 2. Buat Container Utama dengan Scrollbar
            main_frame = tk.Frame(plot_window)
            main_frame.pack(fill="both", expand=True)

            canvas = tk.Canvas(main_frame, bg="white")
            scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
            scrollable_frame = tk.Frame(canvas, bg="white")

            scrollable_frame.bind(
                "<Configure>",
                lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
            )

            canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
            canvas.configure(yscrollcommand=scrollbar.set)

            # Layout Scrollbar: Canvas di kiri, Scrollbar di kanan
            canvas.pack(side="left", fill="both", expand=True)
            scrollbar.pack(side="right", fill="y")

            # 3. Plotting Matplotlib
            # Kita buat Figure yang TINGGI (panjang ke bawah) agar muat 5 subplot terpisah
            # Rasio: Lebar 5 inch, Tinggi 10 inch (agar setiap grafik punya tinggi 2 inch)
            fig = plt.figure(figsize=(5, 10), dpi=80) 
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            bands_order = ["Delta", "Theta", "Alpha", "Beta", "Gamma"]
            
            # Loop untuk membuat 5 subplot terpisah
            for i, band_key in enumerate(filtered.keys()):
                # Cari sinyal yang sesuai
                sig = filtered[band_key]
                
                # Buat subplot (5 baris, 1 kolom, urutan ke i+1)
                ax = fig.add_subplot(5, 1, i+1)
                
                # Plot sinyal
                ax.plot(t, sig, color=colors[i%5], lw=1.2)
                
                # Formatting Minimalis untuk Layar Kecil
                ax.set_title(band_key.split()[0], fontsize=10, fontweight='bold', pad=2)
                ax.tick_params(axis='both', which='major', labelsize=7)
                ax.grid(True, alpha=0.3, linestyle='--')
                
                # Hapus label X kecuali di grafik paling bawah (hemat tempat)
                if i < 4:
                    ax.set_xticklabels([])
                else:
                    ax.set_xlabel("Waktu (s)", fontsize=8)

            fig.tight_layout()

            # 4. Masukkan Figure ke dalam Scrollable Frame Tkinter
            canvas_plot = FigureCanvasTkAgg(fig, master=scrollable_frame)
            canvas_plot.draw()
            canvas_plot.get_tk_widget().pack(fill='both', expand=True)
            
            # Tambahkan tombol tutup di bawah grafik (di dalam scroll area)
            tk.Button(scrollable_frame, text="Tutup Grafik", command=plot_window.destroy, 
                      bg="#e06666", fg="white", font=("Arial", 10)).pack(pady=10)

        except Exception as e:
            messagebox.showerror("Error Plot", f"Gagal: {e}")

    def save_to_pdf(self):
        """Fungsi Profesional Membuat Laporan PDF"""
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok'):
            messagebox.showerror("Error", "Tidak ada data untuk disimpan.")
            return
        
        try:
            # 1. Tentukan Nama File [Waktu Tes].pdf
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            filename = f"Hasil_Tes_{timestamp}.pdf"
            
            # 2. Setup Canvas PDF (Ukuran A4)
            c = canvas.Canvas(filename, pagesize=A4)
            width, height = A4
            
            # --- HEADER ---
            c.setFont("Helvetica-Bold", 16)
            c.drawString(50, height - 50, "LAPORAN ANALISIS ELEKTROENSEFALOGRAFI (EEG)")
            c.setFont("Helvetica", 10)
            c.drawString(50, height - 70, f"Tanggal/Waktu Tes: {datetime.now().strftime('%d %B %Y, %H:%M:%S')}")
            c.drawString(50, height - 85, f"ID File: {filename}")
            c.line(50, height - 95, width - 50, height - 95) # Garis pembatas
            
            # --- HASIL DIAGNOSIS ---
            an = ar['analysis']
            score = an['kriteria_terpenuhi']
            diagnosis_text = "TERINDIKASI DISLEKSIA" if score >= 6 else "TIDAK TERINDIKASI DISLEKSIA"
            color_res = colors.red if score >= 6 else colors.green
            
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, height - 130, "KESIMPULAN ANALISIS:")
            
            c.setFillColor(color_res)
            c.setFont("Helvetica-Bold", 24)
            c.drawString(50, height - 160, diagnosis_text)
            
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 11)
            c.drawString(50, height - 180, f"Confidence Score: {an['confidence_score']:.1f}% ({an['confidence']})")
            c.drawString(50, height - 195, f"Rekomendasi: {an['rekomendasi']}")

            # --- TABEL RINCIAN ---
            y_pos = height - 230
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_pos, "RINCIAN PARAMETER:")
            y_pos -= 20
            
            c.setFont("Courier", 9) # Font monospace agar rapi seperti tabel
            for k, v in an['kriteria'].items():
                mark = "[X]" if v['passed'] else "[ ]"
                line = f"{mark} {v['description']:<40} | Val: {v['value']:>6.2f} (Batasan: {v['threshold']})"
                c.drawString(60, y_pos, line)
                y_pos -= 15

            # --- MEMBUAT GAMBAR GRAFIK UNTUK PDF ---
            # Kita tidak bisa pakai canvas tkinter, harus generate plot baru ke memory
            c.setFont("Helvetica-Bold", 12)
            c.drawString(50, y_pos - 20, "VISUALISASI GELOMBANG:")
            
            # Generate Plot Matplotlib ke Memory Buffer (Bukan layar)
            fig = plt.figure(figsize=(7, 5)) # Ukuran disesuaikan agar muat di A4
            t = ar['t']
            filtered = ar['filtered']
            colors_plot = ['blue', 'orange', 'green', 'red', 'purple']
            
            # Plot 5 sinyal stacked
            for i, (key, sig) in enumerate(filtered.items()):
                ax = fig.add_subplot(5, 1, i+1)
                ax.plot(t, sig, color=colors_plot[i%5], lw=0.8)
                ax.set_ylabel(key.split()[0], fontsize=8, rotation=0, labelpad=20)
                ax.set_yticks([]) # Hilangkan angka Y axis agar bersih
                if i < 4: ax.set_xticks([]) # Hilangkan X axis kecuali yg bawah
                ax.grid(True, alpha=0.3)
                # Hapus frame atas/kanan agar clean
                ax.spines['top'].set_visible(False)
                ax.spines['right'].set_visible(False)
            
            plt.tight_layout()
            
            # Simpan plot ke buffer RAM
            img_buf = io.BytesIO()
            plt.savefig(img_buf, format='png', dpi=100)
            img_buf.seek(0)
            
            # Tempel gambar dari buffer ke PDF
            # Koordinat (x, y, width, height) - Y dihitung dari bawah kertas
            c.drawImage(reportlab.lib.utils.ImageReader(img_buf), 50, y_pos - 350, width=500, height=320)
            plt.close(fig) # Tutup plot agar memori hemat

            # --- FOOTER ---
            c.setFont("Helvetica-Oblique", 8)
            c.drawString(50, 30, "Dokumen ini dihasilkan secara otomatis oleh Sistem Deteksi Dini Disleksia Berbasis EEG.")
            
            # 3. Simpan File
            c.save()
            messagebox.showinfo("Sukses", f"Laporan berhasil disimpan:\n{filename}")
            
        except Exception as e:
            messagebox.showerror("Gagal Simpan PDF", str(e))

    def restart_test(self):
        self.controller.current_question = 1
        self.controller.frames[self.controller.frames[StartPage].__class__].load_label.config(text="File EEG: (belum dimuat)") # Reset label file (opsional)
        self.controller.show_frame(StartPage)