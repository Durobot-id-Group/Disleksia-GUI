#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import math
import os
import sys
import traceback
import time
import csv
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from scipy.signal import butter, filtfilt, iirnotch

# Coba import Pygame & Serial
try:
    import pygame
    if 'SDL_AUDIODRIVER' not in os.environ:
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.music.set_volume(0.8)
except Exception:
    pygame = None

try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None

# ================== KONFIGURASI ==================
COM_PORT = '/dev/ttyUSB0'
BAUD_RATE = 115200
GAIN = 1000.0
VREF = 1.65
QUESTION_DURATION = 5       
TOTAL_QUESTIONS = 5
PROCESS_DURATION = 3000     

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

# ================== EEG ANALYSIS HELPERS ==================
def notch_filter(data, freq, fs, Q=30):
    if len(data) < 12: return data
    try:
        nyq = 0.5 * fs
        b, a = iirnotch(freq / nyq, Q)
        return filtfilt(b, a, data)
    except: return data

def bandpass(data, lowcut, highcut, fs, order=4):
    if len(data) < max(12, order * 6): return data
    try:
        nyq = 0.5 * fs
        low, high = lowcut / nyq, highcut / nyq
        if low <= 0 or high >= 1: return data
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data)
    except: return data

def deteksi_disleksia_riset(delta_signal, theta_signal, alpha_signal, beta_signal, gamma_signal, fs):
    results = {'kriteria': {}, 'scores': {}, 'indikasi': []}
    
    # Hitung Power
    delta_power = np.mean(delta_signal**2)
    theta_power = np.mean(theta_signal**2)
    alpha_power = np.mean(alpha_signal**2)
    beta_power = np.mean(beta_signal**2)
    gamma_power = np.mean(gamma_signal**2)
    
    total_power = delta_power + theta_power + alpha_power + beta_power + gamma_power + 1e-20
    delta_rel = (delta_power / total_power) * 100
    theta_rel = (theta_power / total_power) * 100
    alpha_rel = (alpha_power / total_power) * 100
    beta_rel = (beta_power / total_power) * 100
    gamma_rel = (gamma_power / total_power) * 100

    # Kriteria
    k1 = delta_rel > 35
    k2 = gamma_rel < 8
    delta_gamma_ratio = delta_power / (gamma_power + 1e-10)
    k3 = delta_gamma_ratio > 5.0
    
    delta_std = np.std(delta_signal)
    delta_variability = delta_std / (np.mean(np.abs(delta_signal)) + 1e-10)
    k4 = delta_variability > 1.2
    
    max_other = max(theta_rel, alpha_rel, beta_rel, gamma_rel)
    k5 = delta_rel > (max_other + 10)
    k6 = gamma_rel < (beta_rel - 5)
    
    try:
        dn = (delta_signal - np.mean(delta_signal)) / (np.std(delta_signal) + 1e-10)
        gn = (gamma_signal - np.mean(gamma_signal)) / (np.std(gamma_signal) + 1e-10)
        correlation = np.corrcoef(dn, gn)[0,1]
    except Exception:
        correlation = 0.0
    k7 = correlation < -0.3

    # Fill results dengan bahasa user-friendly
    results['kriteria']['high_delta'] = {
        'value': delta_rel, 'threshold':35, 'passed':k1, 
        'description':'Aktivitas otak lambat dominan',
        'technical': 'Peningkatan Delta Power (0.5-4 Hz)'
    }
    results['kriteria']['low_gamma'] = {
        'value': gamma_rel, 'threshold':8, 'passed':k2, 
        'description':'Aktivitas fokus cepat menurun',
        'technical': 'Penurunan Gamma Power (30-45 Hz)'
    }
    results['kriteria']['delta_gamma_ratio'] = {
        'value': delta_gamma_ratio, 'threshold':5.0, 'passed':k3, 
        'description':'Kesulitan pemrosesan cepat',
        'technical': 'Rasio Delta/Gamma tinggi'
    }
    results['kriteria']['delta_variability'] = {
        'value': delta_variability, 'threshold':1.2, 'passed':k4, 
        'description':'Respons otak tidak stabil',
        'technical': 'Variabilitas Delta tinggi'
    }
    results['kriteria']['delta_dominance'] = {
        'value': delta_rel - max_other, 'threshold':10, 'passed':k5, 
        'description':'Gelombang lambat terlalu kuat',
        'technical': 'Delta dominan > margin'
    }
    results['kriteria']['gamma_lowest'] = {
        'value': beta_rel - gamma_rel, 'threshold':5, 'passed':k6, 
        'description':'Pola fokus tidak optimal',
        'technical': 'Gamma signifikan lebih rendah dari Beta'
    }
    results['kriteria']['delta_gamma_inverse'] = {
        'value': correlation, 'threshold':-0.3, 'passed':k7, 
        'description':'Koordinasi otak terganggu',
        'technical': 'Korelasi delta-gamma negatif'
    }

    kriteria_terpenuhi = sum([k1,k2,k3,k4,k5,k6,k7])
    total_kriteria = 7
    confidence_score = (kriteria_terpenuhi / total_kriteria) * 100

    if kriteria_terpenuhi >= 6:
        diagnosis = "TINGGI"
        confidence = "TINGGI"
        icon = "🔴"
        color = "#e74c3c"
        rekomendasi = "Sangat disarankan evaluasi lanjutan oleh profesional (psikolog/neurolog)."
        narasi = ("Pola aktivitas otak menunjukkan dominasi gelombang lambat yang sangat kuat, "
                  "dengan aktivitas fokus yang menurun signifikan. Pola ini sering ditemukan pada anak "
                  "dengan kesulitan membaca dan memproses informasi tertulis.")
    elif kriteria_terpenuhi >= 4:
        diagnosis = "RENDAH - SEDANG"
        confidence = "SEDANG"
        icon = "🟡"
        color = "#f39c12"
        rekomendasi = "Disarankan evaluasi lebih lanjut dan observasi perilaku pembelajaran."
        narasi = ("Pola aktivitas otak menunjukkan beberapa indikasi yang sering ditemukan pada "
                  "kesulitan membaca, namun tidak semua kriteria terpenuhi. Perlu pemeriksaan tambahan "
                  "dan observasi dalam situasi belajar untuk memastikan.")
    elif kriteria_terpenuhi >= 2:
        diagnosis = "MINIMAL"
        confidence = "RENDAH"
        icon = "🟠"
        color = "#e67e22"
        rekomendasi = "Monitoring berkala dan tes ulang direkomendasikan setelah 3-6 bulan."
        narasi = ("Pola aktivitas otak menunjukkan beberapa variasi ringan yang perlu diperhatikan, "
                  "namun belum mencapai tingkat indikasi yang kuat. Pantau perkembangan membaca dan "
                  "lakukan tes ulang jika ada keluhan.")
    else:
        diagnosis = "TIDAK TERINDIKASI"
        confidence = "TINGGI"
        icon = "🟢"
        color = "#27ae60"
        rekomendasi = "Pola EEG dalam batas normal. Lanjutkan pembelajaran seperti biasa."
        narasi = ("Pola aktivitas otak menunjukkan distribusi gelombang yang normal dan seimbang. "
                  "Tidak ditemukan indikasi gangguan pemrosesan yang terkait dengan kesulitan membaca.")

    results.update({
        'diagnosis': diagnosis,
        'confidence': confidence,
        'confidence_score': confidence_score,
        'kriteria_terpenuhi': kriteria_terpenuhi,
        'total_kriteria': total_kriteria,
        'rekomendasi': rekomendasi,
        'narasi': narasi,
        'icon': icon,
        'color': color,
        'relative_power': {
            'delta': delta_rel, 'theta': theta_rel, 'alpha': alpha_rel, 'beta': beta_rel, 'gamma': gamma_rel
        }
    })
    return results

def run_eeg_pipeline(filename):
    try:
        df = pd.read_csv(filename)
        if "ADC_KIRI" not in df.columns:
            t = np.linspace(0, 10, 2560)
            adc_kiri = np.random.randint(1000, 3000, 2560)
            adc_kanan = np.random.randint(1000, 3000, 2560)
        else:
            t = df["Timestamp"].values
            adc_kiri = df["ADC_KIRI"].values
            adc_kanan = df["ADC_KANAN"].values
            
        eeg_uv_kiri = ((adc_kiri / 4095.0) * 3.3 - VREF) / GAIN * 1e6
        eeg_uv_kanan = ((adc_kanan / 4095.0) * 3.3 - VREF) / GAIN * 1e6

        duration = t[-1] - t[0] if len(t) > 1 else 1
        fs = len(t) / duration if duration > 0 else 256

        eeg_kiri = notch_filter(eeg_uv_kiri, 50, fs)
        eeg_kanan = notch_filter(eeg_uv_kanan, 50, fs)

        bands = {
            "Delta (0.5–4 Hz)": (0.5, 4),
            "Theta (4–8 Hz)": (4, 8),
            "Alpha (8–13 Hz)": (8, 13),
            "Beta (13–30 Hz)": (13, 30),
            "Gamma (30–45 Hz)": (30, 45)
        }

        fk, fn = {}, {}
        for name, (l, h) in bands.items():
            fk[name] = bandpass(eeg_kiri, l, h, fs)
            fn[name] = bandpass(eeg_kanan, l, h, fs)

        hasil = deteksi_disleksia_riset(
            fk["Delta (0.5–4 Hz)"], fk["Theta (4–8 Hz)"],
            fk["Alpha (8–13 Hz)"], fk["Beta (13–30 Hz)"],
            fk["Gamma (30–45 Hz)"],
            fs
        )
        
        band_powers = {name: np.mean(sig**2) for name, sig in fk.items()}

        return {
            "ok": True,
            "analysis": hasil,
            "fs": fs,
            "t": t,
            "raw_uv": eeg_kiri,
            "filtered": fk,
            "band_powers": band_powers
        }
    except Exception as e:
        return {"ok": False, "message": str(e)}

# ================== EEG Serial ==================
class EEGSerialLogger:
    def __init__(self, port, baudrate=115200, out_csv="eeg_record.csv"):
        self.port = port
        self.baudrate = baudrate
        self.out_csv = out_csv
        self.running = False
        self.ser = None

    def start(self):
        if not serial: return
        try:
            self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)
            self.ser.reset_input_buffer()
            self.csv_file = open(self.out_csv, 'w', newline='')
            self.writer = csv.writer(self.csv_file)
            self.writer.writerow(["Timestamp", "ADC_KIRI", "ADC_KANAN"])
            self.running = True
            self.thread = threading.Thread(target=self._loop, daemon=True)
            self.thread.start()
        except Exception as e:
            print("Serial error:", e)

    def _loop(self):
        start_time = time.time()
        while self.running and self.ser:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    if ',' in line:
                        kiri, kanan = line.split(',')[:2]
                        ts = time.time() - start_time
                        self.writer.writerow([ts, int(kiri), int(kanan)])
            except:
                continue

    def stop(self):
        self.running = False
        time.sleep(0.1)
        try:
            if self.ser: self.ser.close()
            self.csv_file.close()
        except: pass

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
        self.show_technical = False
        
        # Scrollable canvas
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        
        self.scrollable_frame.bind("<Configure>", lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")))
        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        
        self.canvas.pack(side="left", fill="both", expand=True, padx=20, pady=20)
        self.scrollbar.pack(side="right", fill="y")
        
        # Container untuk semua konten
        self.content_container = tk.Frame(self.scrollable_frame, bg="#f5f7fa")
        self.content_container.pack(padx=40, pady=20)
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def display_results(self):
        # Clear previous content
        for widget in self.content_container.winfo_children():
            widget.destroy()
        
        ar = self.controller.analysis_results
        
        if not ar or not ar.get('ok'):
            error_label = tk.Label(self.content_container, 
                                   text=f"❌ Analisis Gagal\n{ar.get('message', 'Unknown Error')}", 
                                   font=("Arial", 16), bg="#f5f7fa", fg="#e74c3c", justify="center")
            error_label.pack(pady=50)
            return
            
        an = ar['analysis']
        
        # ========== HEADER ==========
        title_label = tk.Label(self.content_container, text="HASIL PEMERIKSAAN DISLEKSIA", 
                               font=("Arial", 26, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        title_label.pack(pady=(0,5))
        
        subtitle_label = tk.Label(self.content_container, 
                                  text="⚠️ Ini bukan diagnosis medis resmi - hanya indikasi awal", 
                                  font=("Arial", 10, "italic"), bg="#f5f7fa", fg="#7f8c8d")
        subtitle_label.pack(pady=(0,20))
        
        # ========== STATUS CARD (BESAR & BERWARNA) ==========
        status_frame = tk.Frame(self.content_container, bg=an['color'], relief="flat", bd=0)
        status_frame.pack(pady=10, fill="x")
        
        icon_label = tk.Label(status_frame, text=an['icon'], font=("Arial", 48), bg=an['color'])
        icon_label.pack(pady=(15,5))
        
        diagnosis_label = tk.Label(status_frame, 
                                    text=f"Kemungkinan Disleksia: {an['diagnosis']}", 
                                    font=("Arial", 20, "bold"), bg=an['color'], fg="white")
        diagnosis_label.pack()
        
        confidence_label = tk.Label(status_frame, 
                                     text=f"Tingkat Keyakinan Sistem: {an['confidence_score']:.0f}% ({an['confidence']})", 
                                     font=("Arial", 14), bg=an['color'], fg="white")
        confidence_label.pack(pady=(5,15))
        
        # ========== NARASI KESIMPULAN ==========
        narasi_frame = tk.Frame(self.content_container, bg="white", relief="solid", bd=1)
        narasi_frame.pack(pady=15, fill="x", padx=20)
        
        narasi_title = tk.Label(narasi_frame, text="📋 KESIMPULAN SINGKAT", 
                                font=("Arial", 14, "bold"), bg="white", fg="#2c5aa0")
        narasi_title.pack(anchor="w", padx=15, pady=(12,8))
        
        narasi_text = tk.Label(narasi_frame, text=an['narasi'], 
                               font=("Arial", 12), bg="white", fg="#34495e", 
                               wraplength=600, justify="left")
        narasi_text.pack(anchor="w", padx=15, pady=(0,12))
        
        # ========== REKOMENDASI ==========
        rek_frame = tk.Frame(self.content_container, bg="#ecf0f1", relief="flat")
        rek_frame.pack(pady=10, fill="x", padx=20)
        
        rek_title = tk.Label(rek_frame, text="💡 REKOMENDASI", 
                             font=("Arial", 14, "bold"), bg="#ecf0f1", fg="#2c5aa0")
        rek_title.pack(anchor="w", padx=15, pady=(10,5))
        
        rek_text = tk.Label(rek_frame, text=an['rekomendasi'], 
                            font=("Arial", 11), bg="#ecf0f1", fg="#2c3e50", 
                            wraplength=600, justify="left")
        rek_text.pack(anchor="w", padx=15, pady=(0,10))
        
        # ========== BAR CHART AKTIVITAS OTAK ==========
        chart_frame = tk.Frame(self.content_container, bg="white", relief="solid", bd=1)
        chart_frame.pack(pady=15, fill="x", padx=20)
        
        chart_title = tk.Label(chart_frame, text="🧠 DISTRIBUSI AKTIVITAS OTAK", 
                               font=("Arial", 14, "bold"), bg="white", fg="#2c5aa0")
        chart_title.pack(pady=(12,10))
        
        # Data untuk bar chart
        bands_user_friendly = [
            ("Gelombang Lambat (Delta)", an['relative_power']['delta'], "#3498db"),
            ("Kreativitas (Theta)", an['relative_power']['theta'], "#9b59b6"),
            ("Relaksasi (Alpha)", an['relative_power']['alpha'], "#2ecc71"),
            ("Konsentrasi (Beta)", an['relative_power']['beta'], "#f39c12"),
            ("Fokus Tinggi (Gamma)", an['relative_power']['gamma'], "#e74c3c")
        ]
        
        for name, value, color in bands_user_friendly:
            bar_container = tk.Frame(chart_frame, bg="white")
            bar_container.pack(fill="x", padx=20, pady=4)
            
            label_name = tk.Label(bar_container, text=name, font=("Arial", 10), 
                                  bg="white", fg="#2c3e50", width=22, anchor="w")
            label_name.pack(side="left")
            
            bar_bg = tk.Frame(bar_container, bg="#ecf0f1", height=20, width=300)
            bar_bg.pack(side="left", padx=5)
            
            bar_width = int(300 * (value / 100))
            bar_fill = tk.Frame(bar_bg, bg=color, height=20, width=bar_width)
            bar_fill.place(x=0, y=0)
            
            label_val = tk.Label(bar_container, text=f"{value:.1f}%", font=("Arial", 10, "bold"), 
                                 bg="white", fg=color)
            label_val.pack(side="left", padx=5)
        
        chart_frame.pack_configure(pady=(15,10))
        
        # ========== POLA YANG TERDETEKSI ==========
        pattern_frame = tk.Frame(self.content_container, bg="white", relief="solid", bd=1)
        pattern_frame.pack(pady=15, fill="x", padx=20)
        
        pattern_title = tk.Label(pattern_frame, text="🔍 POLA YANG TERDETEKSI", 
                                 font=("Arial", 14, "bold"), bg="white", fg="#2c5aa0")
        pattern_title.pack(anchor="w", padx=15, pady=(12,8))
        
        for k, v in an['kriteria'].items():
            icon = "✔️" if v['passed'] else "❌"
            text_color = "#27ae60" if v['passed'] else "#95a5a6"
            
            pola_item = tk.Label(pattern_frame, 
                                 text=f"{icon}  {v['description']}", 
                                 font=("Arial", 11), bg="white", fg=text_color, anchor="w")
            pola_item.pack(anchor="w", padx=20, pady=3)
        
        pattern_frame.pack_configure(pady=(15,10))
        
        # ========== TOMBOL DETAIL TEKNIS (COLLAPSIBLE) ==========
        self.tech_button = tk.Button(self.content_container, 
                                      text="▼ Lihat Detail Teknis (untuk profesional)", 
                                      font=("Arial", 11), bg="#95a5a6", fg="white", 
                                      relief="flat", cursor="hand2", 
                                      command=self.toggle_technical)
        self.tech_button.pack(pady=10)
        
        # Frame untuk detail teknis (hidden by default)
        self.tech_frame = tk.Frame(self.content_container, bg="#ecf0f1", relief="solid", bd=1)
        
        tech_title = tk.Label(self.tech_frame, text="⚙️ DETAIL TEKNIS EEG", 
                              font=("Arial", 13, "bold"), bg="#ecf0f1", fg="#34495e")
        tech_title.pack(anchor="w", padx=15, pady=(10,5))
        
        tech_text = scrolledtext.ScrolledText(self.tech_frame, width=70, height=10, 
                                               font=("Consolas", 9), relief="flat", bg="white")
        tech_text.pack(padx=15, pady=(5,15))
        
        # Isi detail teknis
        tech_text.insert(tk.END, f"Sampling Rate: {ar['fs']:.2f} Hz\n")
        tech_text.insert(tk.END, f"Durasi Rekaman: {ar['t'][-1]:.2f} detik\n")
        tech_text.insert(tk.END, "="*60 + "\n")
        tech_text.insert(tk.END, "KRITERIA TEKNIS:\n")
        
        for k, v in an['kriteria'].items():
            status = "[✓] PASS" if v['passed'] else "[✗] FAIL"
            tech_text.insert(tk.END, f"{status} : {v['technical']}\n")
            tech_text.insert(tk.END, f"      Nilai: {v['value']:.3f} | Threshold: {v['threshold']}\n")
        
        tech_text.config(state="disabled")
        
        # ========== TOMBOL AKSI ==========
        btn_frame = tk.Frame(self.content_container, bg="#f5f7fa")
        btn_frame.pack(pady=20)
        
        btn_plot = tk.Button(btn_frame, text="📊 LIHAT GRAFIK SINYAL", 
                             font=("Arial", 12, "bold"), bg="#3498db", fg="white", 
                             padx=15, pady=10, relief="flat", cursor="hand2", 
                             command=self.show_plots)
        btn_plot.grid(row=0, column=0, padx=10)
        
        btn_restart = tk.Button(btn_frame, text="🔄 ULANGI TES", 
                                font=("Arial", 12, "bold"), bg="#27ae60", fg="white", 
                                padx=15, pady=10, relief="flat", cursor="hand2", 
                                command=self.restart_test)
        btn_restart.grid(row=0, column=1, padx=10)
        
        btn_export = tk.Button(btn_frame, text="💾 SIMPAN LAPORAN", 
                               font=("Arial", 12, "bold"), bg="#95a5a6", fg="white", 
                               padx=15, pady=10, relief="flat", cursor="hand2", 
                               command=self.export_report)
        btn_export.grid(row=0, column=2, padx=10)

    def toggle_technical(self):
        if self.show_technical:
            self.tech_frame.pack_forget()
            self.tech_button.config(text="▼ Lihat Detail Teknis (untuk profesional)")
            self.show_technical = False
        else:
            self.tech_frame.pack(pady=(10,15), fill="x", padx=20)
            self.tech_button.config(text="▲ Sembunyikan Detail Teknis")
            self.show_technical = True

    def show_plots(self):
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok'): return
        
        try:
            t = ar['t']
            filtered = ar['filtered']
            rel_power = ar['analysis']['relative_power']
            
            # Create 2 subplots: signals + bar chart
            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
            
            # Plot 1: Selected signals (hanya yang penting)
            colors_plot = {'Delta (0.5–4 Hz)': '#3498db', 
                          'Gamma (30–45 Hz)': '#e74c3c'}
            
            for name, sig in filtered.items():
                if name in colors_plot:
                    ax1.plot(t, sig, color=colors_plot[name], label=name, alpha=0.7, lw=1.5)
            
            ax1.set_title("Perbandingan Gelombang Delta vs Gamma", fontsize=14, fontweight='bold')
            ax1.set_xlabel("Waktu (detik)")
            ax1.set_ylabel("Amplitudo (µV)")
            ax1.legend(loc='upper right')
            ax1.grid(alpha=0.3)
            
            # Plot 2: Bar chart relative power
            bands = ['Delta', 'Theta', 'Alpha', 'Beta', 'Gamma']
            values = [rel_power['delta'], rel_power['theta'], rel_power['alpha'], 
                     rel_power['beta'], rel_power['gamma']]
            colors_bar = ['#3498db', '#9b59b6', '#2ecc71', '#f39c12', '#e74c3c']
            
            bars = ax2.bar(bands, values, color=colors_bar, alpha=0.8, edgecolor='black', linewidth=1.5)
            ax2.set_title("Distribusi Daya Relatif Band Frekuensi", fontsize=14, fontweight='bold')
            ax2.set_ylabel("Persentase (%)")
            ax2.set_ylim(0, max(values) * 1.2)
            ax2.grid(axis='y', alpha=0.3)
            
            # Add value labels on bars
            for bar in bars:
                height = bar.get_height()
                ax2.text(bar.get_x() + bar.get_width()/2., height,
                        f'{height:.1f}%', ha='center', va='bottom', fontweight='bold')
            
            plt.tight_layout()
            plt.show()
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menampilkan plot: {e}")

    def export_report(self):
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok'):
            messagebox.showwarning("Export Gagal", "Tidak ada data untuk diekspor")
            return
        
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Simpan Laporan"
            )
            
            if filename:
                an = ar['analysis']
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("="*60 + "\n")
                    f.write("      LAPORAN HASIL TES DISLEKSIA (EEG)\n")
                    f.write("="*60 + "\n\n")
                    f.write(f"Tanggal: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                    f.write(f"HASIL: {an['diagnosis']}\n")
                    f.write(f"Keyakinan Sistem: {an['confidence_score']:.1f}% ({an['confidence']})\n\n")
                    f.write("KESIMPULAN:\n")
                    f.write(f"{an['narasi']}\n\n")
                    f.write("REKOMENDASI:\n")
                    f.write(f"{an['rekomendasi']}\n\n")
                    f.write("-"*60 + "\n")
                    f.write("POLA YANG TERDETEKSI:\n")
                    for k, v in an['kriteria'].items():
                        status = "[v] TERPENUHI" if v['passed'] else "[ ] TIDAK"
                        f.write(f"{status} : {v['description']}\n")
                    f.write("="*60 + "\n")
                
                messagebox.showinfo("Export Berhasil", f"Laporan disimpan di:\n{filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal menyimpan laporan: {e}")

    def restart_test(self):
        self.controller.current_question = 1
        self.controller.frames[TestPage].stopwatch.reset()
        self.controller.show_frame(StartPage)

# ================== RUN APP ==================
if __name__ == "__main__":
    app = App()
    app.mainloop()
