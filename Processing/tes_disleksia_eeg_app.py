#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import math
import os
import sys
import traceback
import pygame
import serial
import serial.tools.list_ports
import time
import csv

COM_PORT = 'COM7'
BAUD_RATE = 115200
GAIN = 1000.0
VREF = 1.65

# # ================== INIT AUDIO ==================
# pygame.mixer.init()

Audio (pygame)
try:
    import pygame
    # Try to set audio driver env before init on some Linux systems
    if 'SDL_AUDIODRIVER' not in os.environ:
        os.environ['SDL_AUDIODRIVER'] = 'alsa'
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.music.set_volume(0.8)
except Exception as e:
    pygame = None
    print("Pygame audio init failed or not available:", e)

# Signal & analysis libs
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.signal import butter, filtfilt, iirnotch, welch
from scipy.stats import skew, kurtosis

# ================== KONFIGURASI ==================
QUESTION_DURATION = 5      # detik per soal
TOTAL_QUESTIONS = 5
PROCESS_DURATION = 3000    # ms animasi sebelum cek (UI), actual analisis berjalan di thread

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
        minutes = 0
        seconds = 0
        self.label.config(text=f"{minutes:02d}:{seconds:02d}")

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
    if len(data) < 12:
        return data
    try:
        nyq = 0.5 * fs
        b, a = iirnotch(freq / nyq, Q)
        return filtfilt(b, a, data)
    except Exception:
        return data

def bandpass(data, lowcut, highcut, fs, order=4):
    if len(data) < max(12, order * 6):
        return data
    try:
        nyq = 0.5 * fs
        low = lowcut / nyq
        high = highcut / nyq
        if low <= 0 or high >= 1:
            return data
        b, a = butter(order, [low, high], btype='band')
        return filtfilt(b, a, data)
    except Exception:
        return data

def deteksi_disleksia_riset(delta_signal, theta_signal, alpha_signal, beta_signal, gamma_signal, fs):
    results = {'kriteria': {}, 'scores': {}, 'indikasi': []}
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
    # correlation delta vs gamma (normalized)
    try:
        dn = (delta_signal - np.mean(delta_signal)) / (np.std(delta_signal) + 1e-10)
        gn = (gamma_signal - np.mean(gamma_signal)) / (np.std(gamma_signal) + 1e-10)
        correlation = np.corrcoef(dn, gn)[0,1]
    except Exception:
        correlation = 0.0
    k7 = correlation < -0.3

    # Fill results
    results['kriteria']['high_delta'] = {'value': delta_rel, 'threshold':35, 'passed':k1, 'description':'Peningkatan Delta Power'}
    results['kriteria']['low_gamma'] = {'value': gamma_rel, 'threshold':8, 'passed':k2, 'description':'Penurunan Gamma Power'}
    results['kriteria']['delta_gamma_ratio'] = {'value': delta_gamma_ratio, 'threshold':5.0, 'passed':k3, 'description':'Rasio Delta/Gamma tinggi'}
    results['kriteria']['delta_variability'] = {'value': delta_variability, 'threshold':1.2, 'passed':k4, 'description':'Variabilitas Delta tinggi'}
    results['kriteria']['delta_dominance'] = {'value': delta_rel - max_other, 'threshold':10, 'passed':k5, 'description':'Delta dominan > margin'}
    results['kriteria']['gamma_lowest'] = {'value': beta_rel - gamma_rel, 'threshold':5, 'passed':k6, 'description':'Gamma signifikan lebih rendah dari Beta'}
    results['kriteria']['delta_gamma_inverse'] = {'value': correlation, 'threshold':-0.3, 'passed':k7, 'description':'Korelasi delta-gamma negatif'}

    kriteria_terpenuhi = sum([k1,k2,k3,k4,k5,k6,k7])
    total_kriteria = 7
    confidence_score = (kriteria_terpenuhi / total_kriteria) * 100

    if kriteria_terpenuhi >= 6:
        diagnosis = "INDIKASI DISLEKSIA - KUAT"
        confidence = "TINGGI"
        rekomendasi = "Sangat disarankan evaluasi lanjutan oleh profesional"
    elif kriteria_terpenuhi >= 4:
        diagnosis = "INDIKASI DISLEKSIA - RENDAH"
        confidence = "SEDANG"
        rekomendasi = "Disarankan evaluasi lebih lanjut"
    elif kriteria_terpenuhi >= 2:
        diagnosis = "TIDAK TERINDIKASI DISLEKSIA - BORDERLINE"
        confidence = "RENDAH"
        rekomendasi = "Monitoring dan tes ulang direkomendasikan"
    else:
        diagnosis = "TIDAK TERINDIKASI DISLEKSIA"
        confidence = "TINGGI"
        rekomendasi = "Pola EEG dalam batas normal"

    results.update({
        'diagnosis': diagnosis,
        'confidence': confidence,
        'confidence_score': confidence_score,
        'kriteria_terpenuhi': kriteria_terpenuhi,
        'total_kriteria': total_kriteria,
        'rekomendasi': rekomendasi,
        'relative_power': {
            'delta': delta_rel, 'theta': theta_rel, 'alpha': alpha_rel, 'beta': beta_rel, 'gamma': gamma_rel
        }
    })
    return results

def run_eeg_pipeline(filename):
    df = pd.read_csv(filename)

    t = df["Timestamp"].values
    adc_kiri = df["ADC_KIRI"].values
    adc_kanan = df["ADC_KANAN"].values

    # ADC → μV
    eeg_uv_kiri = ((adc_kiri / 4095.0) * 3.3 - VREF) / GAIN * 1e6
    eeg_uv_kanan = ((adc_kanan / 4095.0) * 3.3 - VREF) / GAIN * 1e6

    fs = len(t) / (t[-1] - t[0])

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
        fn["Delta (0.5–4 Hz)"], fn["Theta (4–8 Hz)"],
        fn["Alpha (8–13 Hz)"], fn["Beta (13–30 Hz)"],
        fn["Gamma (30–45 Hz)"],
        fs
    )

    return {
        "ok": True,
        "analysis": hasil,
        "fs": fs,
        "t": t,
        "kiri": fk,
        "kanan": fn
    }


# ================== EEG Serial ==================

class EEGSerialLogger:
    def __init__(self, port, baudrate=115200, out_csv="eeg_record.csv"):
        self.port = port
        self.baudrate = baudrate
        self.out_csv = out_csv
        self.running = False

    def start(self):
        self.ser = serial.Serial(self.port, self.baudrate, timeout=1)
        time.sleep(2)
        self.ser.reset_input_buffer()

        self.csv_file = open(self.out_csv, 'w', newline='')
        self.writer = csv.writer(self.csv_file)
        self.writer.writerow(["Timestamp", "ADC_KIRI", "ADC_KANAN"])

        self.running = True
        self.thread = threading.Thread(target=self._loop, daemon=True)
        self.thread.start()

    def _loop(self):
        start_time = time.time()
        while self.running:
            try:
                line = self.ser.readline().decode().strip()
                if ',' not in line:
                    continue

                kiri, kanan = line.split(',')[:2]
                kiri = int(kiri)
                kanan = int(kanan)

                if 0 <= kiri <= 4095 and 0 <= kanan <= 4095:
                    ts = time.time() - start_time
                    self.writer.writerow([ts, kiri, kanan])
            except:
                continue

    def stop(self):
        self.running = False
        time.sleep(0.2)
        try:
            self.ser.close()
            self.csv_file.close()
        except:
            pass


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
        logo_paths = [
            "logo.ico","logo.png","logo.jpg","logo.jpeg",
            "assets/logo.png","images/logo.png"
        ]
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
        except Exception:
            pass

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
                if progress_width > 10:
                    self.progress_canvas.create_rectangle(progress_width-10,0,progress_width,6, fill="#5ba3f5", outline="", width=0)
            self.after(30, self.animate_progress)
        else:
            self.after(500, self.go_to_start)

    def go_to_start(self):
        self.controller.show_frame(StartPage)
        self.controller.frames[StartPage].animate_entrance()

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

        # Load EEG button
        self.load_button = tk.Button(self.button_frame, text="Muat Data EEG (CSV)", font=("Arial", 12), bg="#6aa84f", fg="white", relief="flat", cursor="hand2", command=self.load_eeg)
        self.load_button.grid(row=0, column=0, padx=6)

        # Start test button
        self.start_button = tk.Button(self.button_frame, text="MULAI TES", font=("Arial", 18, "bold"), bg="#4a90e2", fg="white", relief="flat", cursor="hand2", padx=24, pady=10, command=self.start_with_audio)
        self.start_button.grid(row=0, column=1, padx=6)

        self.load_label = tk.Label(self.content_frame, text="File EEG: (belum dimuat)", font=("Arial", 10), bg="#f5f7fa", fg="#5a6c7d")
        self.load_label.pack(pady=(6,0))

        self.start_button.bind("<Enter>", lambda e: self.start_button.config(bg="#2c5aa0"))
        self.start_button.bind("<Leave>", lambda e: self.start_button.config(bg="#4a90e2"))

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def animate_entrance(self):
        pass

    def load_eeg(self):
        fname = filedialog.askopenfilename(title="Pilih file CSV EEG", filetypes=[("CSV files","*.csv"),("All files","*.*")])
        if fname:
            self.controller.eeg_filename = fname
            basename = os.path.basename(fname)
            self.load_label.config(text=f"File EEG: {basename}")

    def start_with_audio(self):
                # ===== START EEG SERIAL LOGGER =====
        try:
            csv_name = f"eeg_dual_{int(time.time())}.csv"
            self.controller.eeg_filename = csv_name

            self.controller.eeg_logger = EEGSerialLogger(
                port=COM_PORT,
                baudrate=BAUD_RATE,
                out_csv=csv_name
            )
            self.controller.eeg_logger.start()
        except Exception as e:
            messagebox.showerror("Serial Error", str(e))
            return


        if self.controller.eeg_filename is None:
            if not messagebox.askyesno("Konfirmasi", "Belum memuat file EEG. Lanjutkan tes tanpa data EEG?"):
                return

        # optional play audio 1
        try:
            if pygame:
                pygame.mixer.music.load("audio/soal 1.mp3")
                pygame.mixer.music.play()
        except Exception:
            pass

        self.check_audio_finished()

    def check_audio_finished(self):
        try:
            if pygame and pygame.mixer.music.get_busy():
                self.after(200, self.check_audio_finished)
            else:
                self.go_to_test()
        except Exception:
            self.go_to_test()

    def go_to_test(self):
        self.controller.show_frame(TestPage)
        self.controller.frames[TestPage].stopwatch.start()

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
        self.timer_shadow = tk.Frame(self.timer_container, bg="#c1d5e8")
        self.timer_shadow.pack(padx=3, pady=3)
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

    def on_tick(self, elapsed_time):
        # when elapsed time >= QUESTION_DURATION *current_question + 1 => next
        if elapsed_time >= QUESTION_DURATION * self.controller.current_question + 1:
            self.next_question()

    def next_question(self):
        if self.controller.current_question < TOTAL_QUESTIONS:
            self.controller.current_question += 1
            self.progress_label.config(text=f"Soal {self.controller.current_question} dari {TOTAL_QUESTIONS}")
            self.label_question.config(text=f"Soal ke-{self.controller.current_question}")
            try:
                if pygame:
                    pygame.mixer.music.load(f"audio/soal {self.controller.current_question}.mp3")
                    pygame.mixer.music.play()
            except Exception:
                pass
        else:
            self.finish_test()

    def finish_test(self):
                # ===== STOP EEG SERIAL LOGGER =====
        try:
            if self.controller.eeg_logger:
                self.controller.eeg_logger.stop()
        except:
            pass


        self.stopwatch.stop()
        try:
            if pygame:
                pygame.mixer.music.load("audio/tes selesai.mp3")
                pygame.mixer.music.play()
        except Exception:
            pass
        # placeholder until analysis runs
        self.controller.test_result = "MENUNGGU ANALISIS"
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
        self.dots_label = tk.Label(self.content_frame, text="", font=("Arial", 16), bg="#f5f7fa", fg="#5a6c7d")
        self.dots_label.pack(pady=8)
        self.circle_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.circle_container.pack(pady=10)
        self.progress_canvas = tk.Canvas(self.circle_container, width=120, height=120, bg="#f5f7fa", highlightthickness=0)
        self.progress_canvas.pack()
        self.angle = 0
        self.dots_count = 0
        self._processing_thread = None
        self._animate = False

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def start_processing(self):
        # Start animation
        self.angle = 0
        self.dots_count = 0
        self._animate = True
        self.animate_circle()
        self.animate_dots()
        # Start analysis in background thread (so UI stays responsive)
        def worker():
            # small delay so animation visible
            try:
                if self.controller.eeg_filename:
                    res = run_eeg_pipeline(self.controller.eeg_filename)
                else:
                    res = {'ok': False, 'message': 'Tidak ada file EEG dimuat.'}
                self.controller.analysis_results = res
            except Exception as e:
                self.controller.analysis_results = {'ok': False, 'message': str(e)}
            # stop animation and move to result page on main thread
            self.after(500, self.finish)
        self._processing_thread = threading.Thread(target=worker, daemon=True)
        self._processing_thread.start()

    def animate_circle(self):
        self.progress_canvas.delete("all")
        self.progress_canvas.create_oval(17,17,103,103, outline="#e1e8ed", width=6)
        extent = (self.angle % 360)
        self.progress_canvas.create_arc(17,17,103,103, start=-90, extent=extent, outline="#4a90e2", width=6, style="arc")
        self.progress_canvas.create_text(60,60, text=f"{int((extent/360)*100)}%", font=("Arial", 18, "bold"), fill="#2c5aa0")
        self.angle += 12
        if self._animate:
            self.after(60, self.animate_circle)

    def animate_dots(self):
        dots = "." * (self.dots_count % 4)
        self.dots_label.config(text=f"Menganalisis data{dots}")
        self.dots_count += 1
        if self._animate:
            self.after(300, self.animate_dots)

    def finish(self):
        self._animate = False
        # show result page
        result_page = self.controller.frames[ResultPage]
        ar = self.controller.analysis_results
        if ar and ar.get('ok', False) and ar.get('analysis') is not None:
            diagnosis = ar['analysis']['diagnosis']
        elif ar and ar.get('ok', False):
            diagnosis = "ANALISIS TIDAK LENGKAP"
        else:
            diagnosis = "ANALISIS GAGAL"
        self.controller.test_result = diagnosis
        result_page.set_result(diagnosis)
        self.controller.show_frame(ResultPage)

class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        ar = self.controller.analysis_results
        analysis = ar["analysis"]
        super().__init__(parent, bg="#f5f7fa")
        self.detail_text.insert(tk.END, f"Diagnosis: {analysis['diagnosis']}\n")
        self.detail_text.insert(tk.END, f"Confidence: {analysis['confidence']}\n")
        self.detail_text.insert(tk.END, f"Total kriteria: {analysis['total_kriteria']}/{analysis['max_kriteria']}\n\n")

        self.detail_text.insert(tk.END, "=== INDIKASI ===\n")
        for i in analysis["all_indikasi"]:
            self.detail_text.insert(tk.END, f"{i}\n")

        self.controller = controller
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        self.title_label = tk.Label(self.content_frame, text="HASIL TES", font=("Arial", 22, "bold"), bg="#f5f7fa", fg="#2c5aa0")
        self.title_label.pack(pady=(0,10))
        self.result_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.result_container.pack(pady=10)
        self.result_shadow = tk.Frame(self.result_container, bg="#c1d5e8")
        self.result_shadow.pack(padx=3, pady=3)
        self.result_frame = tk.Frame(self.result_container, bg="white", highlightbackground="#4a90e2", highlightthickness=3)
        self.result_frame.pack()
        self.label_result = tk.Label(self.result_frame, text="", font=("Arial", 28, "bold"), bg="white", fg="#2c5aa0", padx=28, pady=14)
        self.label_result.pack()
        self.detail_text = scrolledtext.ScrolledText(self.content_frame, width=80, height=12, wrap='word', font=("Arial", 10))
        self.detail_text.pack(pady=(10,6))
        self.button_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.button_container.pack(pady=(12,0))
        self.plot_button = tk.Button(self.button_container, text="Tampilkan Plot EEG", font=("Arial", 12), bg="#6aa84f", fg="white", relief="flat", cursor="hand2", command=self.show_plots)
        self.plot_button.grid(row=0, column=0, padx=6)
        self.restart_button = tk.Button(self.button_container, text="TES ULANG", font=("Arial", 16, "bold"), bg="#4a90e2", fg="white", relief="flat", cursor="hand2", padx=18, pady=8, command=self.restart_test)
        self.restart_button.grid(row=0, column=1, padx=6)
        self.plot_button.bind("<Enter>", lambda e: self.plot_button.config(bg="#5b8f3f"))
        self.plot_button.bind("<Leave>", lambda e: self.plot_button.config(bg="#6aa84f"))

    def on_canvas_configure(self, event):
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def set_result(self, result_text):
        self.label_result.config(text=result_text)
        # fill details
        self.detail_text.delete('1.0', tk.END)
        ar = self.controller.analysis_results
        if not ar:
            self.detail_text.insert(tk.END, "Tidak ada hasil analisis.\n")
            return
        if not ar.get('ok', False):
            self.detail_text.insert(tk.END, f"Analisis gagal: {ar.get('message','')}\n")
            return
        analysis = ar.get('analysis')
        if analysis is None:
            self.detail_text.insert(tk.END, f"Analisis tidak lengkap: {ar.get('message','')}\n")
            # still show band powers if exist
            if ar.get('band_powers'):
                self.detail_text.insert(tk.END, "\nBand powers (μV²):\n")
                for k,v in ar['band_powers'].items():
                    self.detail_text.insert(tk.END, f"  {k}: {v:.3f}\n")
            return

        self.detail_text.insert(tk.END, "=== Ringkasan Analisis ===\n")
        self.detail_text.insert(tk.END, f"Diagnosis: {analysis['diagnosis']}\n")
        self.detail_text.insert(tk.END, f"Confidence: {analysis['confidence']} ({analysis['confidence_score']:.1f}%)\n")
        self.detail_text.insert(tk.END, f"Kriteria terpenuhi: {analysis['kriteria_terpenuhi']}/{analysis['total_kriteria']}\n")
        self.detail_text.insert(tk.END, f"Rekomendasi: {analysis['rekomendasi']}\n\n")
        self.detail_text.insert(tk.END, "=== Detail Kriteria ===\n")
        for key, val in analysis['kriteria'].items():
            status = "TERPENUHI" if val['passed'] else "TIDAK"
            self.detail_text.insert(tk.END, f"{val['description']}: {val['value']:.3f} (threshold {val['threshold']}) -> {status}\n")

    def show_plots(self):
        ar = self.controller.analysis_results
        if not ar or not ar.get('ok', False):
            messagebox.showerror("Plot", "Tidak ada data plot.")
            return
        t = ar.get('t', np.arange(len(ar.get('raw_uv', []))))
        raw = ar.get('raw_uv')
        filtered = ar.get('filtered', {})
        band_powers = ar.get('band_powers', {})
        # Non-blocking plot
        try:
            plt.close('all')
            nplots = 1 + len(filtered)
            plt.figure(figsize=(12, 3*nplots))
            plt.subplot(nplots,1,1)
            plt.plot(t, raw)
            plt.title("Sinyal EEG Mentah (μV)")
            plt.ylabel("μV")
            plt.grid(True, alpha=0.3)
            idx = 2
            colors = ['blue','green','red','orange','purple']
            for (name, sig), col in zip(filtered.items(), colors):
                plt.subplot(nplots,1,idx)
                plt.plot(t, sig)
                plt.title(name)
                plt.ylabel("μV")
                plt.grid(True, alpha=0.3)
                idx += 1
            plt.tight_layout()
            # bar chart of band powers
            if band_powers:
                plt.figure(figsize=(6,4))
                bands_short = ['Delta','Theta','Alpha','Beta','Gamma']
                powers = [band_powers.get("Delta (0.5–4 Hz)",0),
                          band_powers.get("Theta (4–8 Hz)",0),
                          band_powers.get("Alpha (8–13 Hz)",0),
                          band_powers.get("Beta (13–30 Hz)",0),
                          band_powers.get("Gamma (30–45 Hz)",0)]
                total = sum(powers) + 1e-20
                powers_pct = [(p/total)*100 for p in powers]
                bars = plt.bar(bands_short, powers_pct)
                plt.ylabel("Power Relatif (%)")
                plt.title("Distribusi Power EEG Band")
                plt.grid(axis='y', alpha=0.3)
                plt.tight_layout()
            plt.show(block=False)
        except Exception as e:
            messagebox.showerror("Plot error", f"Gagal membuat plot: {e}")

    def restart_test(self):
        self.controller.current_question = 1
        self.controller.frames[TestPage].stopwatch.reset()
        self.controller.frames[TestPage].progress_label.config(text=f"Soal 1 dari {TOTAL_QUESTIONS}")
        self.controller.frames[TestPage].label_question.config(text="Soal ke-1")
        self.controller.show_frame(StartPage)

# ================== RUN APP ==================
if __name__ == "__main__":
    app = App()
    app.mainloop()

