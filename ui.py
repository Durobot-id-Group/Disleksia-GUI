import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import time
import os
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

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
        # Menambahkan ResultPage ke daftar
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
        self.title_label = tk.Label(self.title_frame, text="TES DISLEKSIA", font=("Arial", 28, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        self.title_label.pack(pady=(0,5))
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
        # Mulai Serial Logger jika tidak ada file load manual
        if not self.controller.eeg_filename:
            try:
                csv_name = f"eeg_live_{int(time.time())}.csv"
                self.controller.eeg_filename = csv_name
                self.controller.eeg_logger = EEGSerialLogger(COM_PORT, BAUD_RATE, csv_name)
                self.controller.eeg_logger.start()
            except Exception as e:
                print("Logger error", e)

        # Audio Intro (Optional)
        try:
            if pygame:
                if os.path.exists("audio/soal 1.mp3"):
                    pygame.mixer.music.load("audio/soal 1.mp3")
                    pygame.mixer.music.play()
        except: pass

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
        # Jika waktu soal habis -> pindah soal
        current_limit = QUESTION_DURATION * self.controller.current_question
        if elapsed_time >= current_limit:
            self.next_question()

    def next_question(self):
        if self.controller.current_question < TOTAL_QUESTIONS:
            self.controller.current_question += 1
            self.update_ui_labels()
            # Audio (Optional)
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
        # Stop Logger
        try:
            if self.controller.eeg_logger:
                self.controller.eeg_logger.stop()
        except: pass
        
        self.stopwatch.stop()
        
        # Audio Selesai
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
        
        self.title_label = tk.Label(self.content_frame, text="MEMPROSES HASIL", font=("Arial", 24, "bold"), bg="#f5f7fa", fg="#2c5aa0")
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
        # Jalankan analisis di thread agar GUI tidak freeze
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
        # Simulasi processing time
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

# ================== RESULT PAGE (DITAMBAHKAN) ==================
class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        self.title_label = tk.Label(self.content_frame, text="HASIL ANALISIS", font=("Arial", 28, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        self.title_label.pack(pady=(0,10))
        
        self.result_text = scrolledtext.ScrolledText(self.content_frame, width=70, height=15, font=("Consolas", 10), relief="flat")
        self.result_text.pack(pady=10)
        
        self.btn_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.btn_frame.pack(pady=10)
        
        self.btn_plot = tk.Button(self.btn_frame, text="LIHAT GRAFIK SINYAL", font=("Arial", 12, "bold"), bg="#4a90e2", fg="white", padx=15, pady=8, relief="flat", command=self.show_plots)
        self.btn_plot.grid(row=0, column=0, padx=10)
        
        self.btn_restart = tk.Button(self.btn_frame, text="ULANGI TES", font=("Arial", 12, "bold"), bg="#6aa84f", fg="white", padx=15, pady=8, relief="flat", command=self.restart_test)
        self.btn_restart.grid(row=0, column=1, padx=10)

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def display_results(self):
        self.result_text.delete('1.0', tk.END)
        ar = self.controller.analysis_results
        
        if not ar or not ar.get('ok'):
            self.result_text.insert(tk.END, f"Analisis Gagal: {ar.get('message', 'Unknown Error')}")
            return
            
        an = ar['analysis']
        self.result_text.insert(tk.END, f"DIAGNOSIS    : {an['diagnosis']}\n")
        self.result_text.insert(tk.END, f"KEYAKINAN    : {an['confidence_score']:.1f}% ({an['confidence']})\n")
        self.result_text.insert(tk.END, f"REKOMENDASI  : {an['rekomendasi']}\n")
        self.result_text.insert(tk.END, "="*60 + "\n")
        self.result_text.insert(tk.END, "DETAIL KRITERIA:\n")
        
        for k, v in an['kriteria'].items():
            status = "[v] TERPENUHI" if v['passed'] else "[ ] TIDAK    "
            self.result_text.insert(tk.END, f"{status} : {v['description']} (Nilai: {v['value']:.2f})\n")

    def show_plots(self):
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok'): return
        
        try:
            t = ar['t']
            raw = ar['raw_uv']
            filtered = ar['filtered']
            
            plt.figure(figsize=(10, 8))
            plt.subplot(6,1,1)
            plt.plot(t, raw, color='black', lw=0.5)
            plt.title("Sinyal EEG Mentah (uV)")
            plt.grid(alpha=0.3)
            
            colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728', '#9467bd']
            for i, (name, sig) in enumerate(filtered.items()):
                plt.subplot(6,1,i+2)
                plt.plot(t, sig, color=colors[i%5], lw=0.8)
                plt.title(name)
                plt.grid(alpha=0.3)
            
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menampilkan plot: {e}")

    def restart_test(self):
        self.controller.current_question = 1
        self.controller.frames[TestPage].stopwatch.reset()
        self.controller.show_frame(StartPage)
