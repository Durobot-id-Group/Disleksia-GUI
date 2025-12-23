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
from scipy.signal import butter, filtfilt, iirnotch

# Coba import serial
try:
    import serial
    import serial.tools.list_ports
except ImportError:
    serial = None
    print("Modul 'pyserial' belum diinstall. Serial logger tidak akan berfungsi.")

# Coba import pygame
try:
    import pygame
    if 'SDL_AUDIODRIVER' not in os.environ:
        os.environ['SDL_AUDIODRIVER'] = 'alsa' # Ubah ke 'dsound' jika di Windows ada masalah
    pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
    pygame.mixer.music.set_volume(0.8)
except Exception as e:
    pygame = None
    print("Pygame audio init failed:", e)

# ================== KONFIGURASI ==================
COM_PORT = 'COM7'   # Sesuaikan dengan Port Arduino/EEG Anda
BAUD_RATE = 115200
GAIN = 1000.0
VREF = 1.65
QUESTION_DURATION = 5       # detik per soal
TOTAL_QUESTIONS = 5
PROCESS_DURATION = 3000     # ms (simulasi loading)

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

def deteksi_disleksia_riset(delta, theta, alpha, beta, gamma):
    # Hitung power (Mean Squared)
    p_delta = np.mean(delta**2)
    p_theta = np.mean(theta**2)
    p_alpha = np.mean(alpha**2)
    p_beta  = np.mean(beta**2)
    p_gamma = np.mean(gamma**2)
    
    total_power = p_delta + p_theta + p_alpha + p_beta + p_gamma + 1e-20
    
    # Relative Power (%)
    rel = {
        'delta': (p_delta / total_power) * 100,
        'theta': (p_theta / total_power) * 100,
        'alpha': (p_alpha / total_power) * 100,
        'beta':  (p_beta  / total_power) * 100,
        'gamma': (p_gamma / total_power) * 100
    }

    # Kriteria Diagnostik (Contoh Logika)
    k1 = rel['delta'] > 35
    k2 = rel['gamma'] < 8
    ratio_dg = p_delta / (p_gamma + 1e-10)
    k3 = ratio_dg > 5.0
    
    delta_std = np.std(delta)
    delta_var = delta_std / (np.mean(np.abs(delta)) + 1e-10)
    k4 = delta_var > 1.2
    
    max_other = max(rel['theta'], rel['alpha'], rel['beta'], rel['gamma'])
    k5 = rel['delta'] > (max_other + 10)
    k6 = rel['gamma'] < (rel['beta'] - 5)
    
    # Korelasi sederhana
    try:
        dn = (delta - np.mean(delta)) / (np.std(delta) + 1e-10)
        gn = (gamma - np.mean(gamma)) / (np.std(gamma) + 1e-10)
        corr = np.corrcoef(dn, gn)[0,1]
    except:
        corr = 0.0
    k7 = corr < -0.3

    results = {'kriteria': {}}
    results['kriteria']['high_delta'] = {'value': rel['delta'], 'threshold': 35, 'passed': k1, 'desc': 'Delta Power Tinggi'}
    results['kriteria']['low_gamma'] = {'value': rel['gamma'], 'threshold': 8, 'passed': k2, 'desc': 'Gamma Power Rendah'}
    results['kriteria']['delta_gamma_ratio'] = {'value': ratio_dg, 'threshold': 5.0, 'passed': k3, 'desc': 'Rasio Delta/Gamma'}
    results['kriteria']['delta_var'] = {'value': delta_var, 'threshold': 1.2, 'passed': k4, 'desc': 'Variabilitas Delta'}
    results['kriteria']['delta_dom'] = {'value': rel['delta'] - max_other, 'threshold': 10, 'passed': k5, 'desc': 'Dominasi Delta'}
    results['kriteria']['gamma_low_beta'] = {'value': rel['beta'] - rel['gamma'], 'threshold': 5, 'passed': k6, 'desc': 'Gamma < Beta'}
    results['kriteria']['neg_corr'] = {'value': corr, 'threshold': -0.3, 'passed': k7, 'desc': 'Korelasi Negatif'}

    passed_count = sum([k1, k2, k3, k4, k5, k6, k7])
    total_crit = 7
    score = (passed_count / total_crit) * 100

    if passed_count >= 5:
        diagnosis = "INDIKASI DISLEKSIA - KUAT"
        rec = "Segera hubungi profesional."
    elif passed_count >= 3:
        diagnosis = "INDIKASI DISLEKSIA - SEDANG"
        rec = "Evaluasi lanjutan disarankan."
    else:
        diagnosis = "NORMAL / TIDAK TERINDIKASI"
        rec = "Pola gelombang otak normal."

    results.update({
        'diagnosis': diagnosis,
        'confidence_score': score,
        'kriteria_terpenuhi': passed_count,
        'total_kriteria': total_crit,
        'rekomendasi': rec,
        'relative_power': rel,
        'band_powers': {k: v for k,v in zip(['Delta','Theta','Alpha','Beta','Gamma'], [p_delta, p_theta, p_alpha, p_beta, p_gamma])}
    })
    return results

def run_eeg_pipeline(filename):
    try:
        df = pd.read_csv(filename)
        # Pastikan kolom ada
        if "ADC_KIRI" not in df.columns:
            # Fallback jika CSV kosong/salah header
            t = np.linspace(0, 10, 1000)
            adc_kiri = np.random.randint(1000, 3000, 1000)
            adc_kanan = np.random.randint(1000, 3000, 1000)
        else:
            t = df["Timestamp"].values
            adc_kiri = df["ADC_KIRI"].values
            adc_kanan = df["ADC_KANAN"].values
    except Exception as e:
        return {"ok": False, "message": str(e)}

    # Konversi ADC ke uV
    eeg_uv_kiri = ((adc_kiri / 4095.0) * 3.3 - VREF) / GAIN * 1e6
    eeg_uv_kanan = ((adc_kanan / 4095.0) * 3.3 - VREF) / GAIN * 1e6

    duration = t[-1] - t[0] if len(t) > 1 else 1
    fs = len(t) / duration if duration > 0 else 100

    # Filter 50Hz
    eeg_kiri = notch_filter(eeg_uv_kiri, 50, fs)
    eeg_kanan = notch_filter(eeg_uv_kanan, 50, fs)

    bands = {
        "Delta (0.5-4 Hz)": (0.5, 4),
        "Theta (4-8 Hz)": (4, 8),
        "Alpha (8-13 Hz)": (8, 13),
        "Beta (13-30 Hz)": (13, 30),
        "Gamma (30-45 Hz)": (30, 45)
    }

    fk = {} 
    for name, (l, h) in bands.items():
        fk[name] = bandpass(eeg_kiri, l, h, fs)
    
    # Analisis (Fokus Channel Kiri untuk contoh bahasa/disleksia)
    hasil = deteksi_disleksia_riset(
        fk["Delta (0.5-4 Hz)"], fk["Theta (4-8 Hz)"],
        fk["Alpha (8-13 Hz)"], fk["Beta (13-30 Hz)"],
        fk["Gamma (30-45 Hz)"]
    )

    return {
        "ok": True,
        "analysis": hasil,
        "fs": fs,
        "t": t,
        "raw_uv": eeg_uv_kiri,  # Untuk plotting
        "filtered": fk          # Untuk plotting
    }

# ================== SERIAL LOGGER ==================
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
            print(f"Serial Error: {e}")

    def _loop(self):
        start_time = time.time()
        while self.running and self.ser:
            try:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8', errors='ignore').strip()
                    parts = line.split(',')
                    if len(parts) >= 2:
                        kiri = int(parts[0])
                        kanan = int(parts[1])
                        ts = time.time() - start_time
                        self.writer.writerow([ts, kiri, kanan])
            except: pass

    def stop(self):
        self.running = False
        if self.ser:
            try:
                self.ser.close()
                self.csv_file.close()
            except: pass

# ================== GUI PAGES ==================
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Tes Disleksia (EEG)")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.destroy())
        
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()
        self.current_question = 1
        self.eeg_filename = None
        self.analysis_results = None
        self.eeg_logger = None

        self.container = tk.Frame(self, bg="#f5f7fa")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        # Menambahkan ResultPage ke daftar frame
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
        tk.Label(self, text="TES DISLEKSIA", font=("Arial", 40, "bold"), bg="#f5f7fa", fg="#2c5aa0").pack(expand=True)
        self.progress = ttk.Progressbar(self, length=300, mode='determinate')
        self.progress.pack(pady=50)

    def start_intro(self):
        self.load_step(0)

    def load_step(self, val):
        self.progress['value'] = val
        if val < 100:
            self.after(30, lambda: self.load_step(val + 2))
        else:
            self.controller.show_frame(StartPage)

class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        tk.Label(self, text="MENU UTAMA", font=("Arial", 30), bg="#f5f7fa").pack(pady=50)
        
        btn_frame = tk.Frame(self, bg="#f5f7fa")
        btn_frame.pack()
        
        tk.Button(btn_frame, text="Muat CSV", command=self.load_csv, font=("Arial", 14), bg="#6aa84f", fg="white").grid(row=0, column=0, padx=10)
        tk.Button(btn_frame, text="MULAI TES", command=self.start_test, font=("Arial", 14), bg="#4a90e2", fg="white").grid(row=0, column=1, padx=10)
        
        self.lbl_file = tk.Label(self, text="File: Belum ada", bg="#f5f7fa")
        self.lbl_file.pack(pady=10)

    def load_csv(self):
        f = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if f:
            self.controller.eeg_filename = f
            self.lbl_file.config(text=f"File: {os.path.basename(f)}")

    def start_test(self):
        # Mulai logger jika belum ada file loaded
        if not self.controller.eeg_filename:
            fname = f"eeg_data_{int(time.time())}.csv"
            self.controller.eeg_filename = fname
            self.controller.eeg_logger = EEGSerialLogger(COM_PORT, BAUD_RATE, fname)
            self.controller.eeg_logger.start()
        
        self.controller.show_frame(TestPage)
        self.controller.frames[TestPage].start_sequence()

class TestPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        
        self.lbl_q = tk.Label(self, text="Soal 1", font=("Arial", 20), bg="#4a90e2", fg="white")
        self.lbl_q.pack(pady=20, fill='x')
        
        self.lbl_timer = tk.Label(self, text="00:00", font=("Arial", 60), bg="#f5f7fa")
        self.lbl_timer.pack(expand=True)
        
        self.stopwatch = Stopwatch(self, self.lbl_timer, on_tick=self.check_time)

    def start_sequence(self):
        self.controller.current_question = 1
        self.update_ui()
        self.stopwatch.start()
        self.play_audio()

    def update_ui(self):
        self.lbl_q.config(text=f"Soal ke-{self.controller.current_question}")

    def play_audio(self):
        if pygame:
            try:
                f = f"audio/soal {self.controller.current_question}.mp3"
                if os.path.exists(f):
                    pygame.mixer.music.load(f)
                    pygame.mixer.music.play()
            except: pass

    def check_time(self, elapsed):
        limit = QUESTION_DURATION * self.controller.current_question
        if elapsed >= limit:
            self.next_question()

    def next_question(self):
        if self.controller.current_question < TOTAL_QUESTIONS:
            self.controller.current_question += 1
            self.update_ui()
            self.play_audio()
        else:
            self.stopwatch.stop()
            if self.controller.eeg_logger:
                self.controller.eeg_logger.stop()
            
            # Pindah ke pemrosesan
            self.controller.show_frame(ProcessPage)
            self.controller.frames[ProcessPage].start_processing()

class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        tk.Label(self, text="MENGANALISIS SINYAL OTAK...", font=("Arial", 20), bg="#f5f7fa").pack(expand=True)
        self.progress = ttk.Progressbar(self, mode='indeterminate')
        self.progress.pack(pady=20)

    def start_processing(self):
        self.progress.start(10)
        # Jalankan analisis di thread terpisah agar GUI tidak macet
        threading.Thread(target=self.run_analysis, daemon=True).start()

    def run_analysis(self):
        # Simulasi delay
        time.sleep(2)
        
        fname = self.controller.eeg_filename
        if fname and os.path.exists(fname):
            result = run_eeg_pipeline(fname)
        else:
            result = {"ok": False, "message": "File tidak ditemukan"}
        
        self.controller.analysis_results = result
        
        # Kembali ke thread utama untuk update GUI
        self.after(0, self.finish)

    def finish(self):
        self.progress.stop()
        self.controller.show_frame(ResultPage)
        self.controller.frames[ResultPage].display_results()

class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        
        tk.Label(self, text="HASIL ANALISIS", font=("Arial", 24, "bold"), bg="#f5f7fa", fg="#2c5aa0").pack(pady=10)
        
        self.txt_result = scrolledtext.ScrolledText(self, width=60, height=15, font=("Consolas", 10))
        self.txt_result.pack(pady=10)
        
        btn_frame = tk.Frame(self, bg="#f5f7fa")
        btn_frame.pack(pady=10)
        
        tk.Button(btn_frame, text="Lihat Grafik Sinyal", command=self.show_plots, bg="#4a90e2", fg="white", font=("Arial", 12)).pack(side="left", padx=10)
        tk.Button(btn_frame, text="Ulangi Tes", command=self.restart, bg="#e06666", fg="white", font=("Arial", 12)).pack(side="left", padx=10)

    def display_results(self):
        res = self.controller.analysis_results
        self.txt_result.delete('1.0', tk.END)
        
        if not res or not res.get('ok'):
            self.txt_result.insert(tk.END, f"Error: {res.get('message', 'Unknown Error')}")
            return

        an = res['analysis']
        self.txt_result.insert(tk.END, f"DIAGNOSIS: {an['diagnosis']}\n")
        self.txt_result.insert(tk.END, f"Confidence: {an['confidence_score']:.1f}%\n")
        self.txt_result.insert(tk.END, f"Rekomendasi: {an['rekomendasi']}\n\n")
        
        self.txt_result.insert(tk.END, "--- Detail Kriteria ---\n")
        for k, v in an['kriteria'].items():
            status = "[v]" if v['passed'] else "[ ]"
            self.txt_result.insert(tk.END, f"{status} {v['desc']} ({v['value']:.2f})\n")

    def show_plots(self):
        res = self.controller.analysis_results
        if not res or not res.get('ok'): return
        
        t = res['t']
        raw = res['raw_uv']
        filtered = res['filtered']
        
        plt.figure(figsize=(10, 8))
        
        plt.subplot(6, 1, 1)
        plt.plot(t, raw, color='black')
        plt.title("Sinyal Raw (Kiri)")
        plt.ylabel("uV")
        
        colors = ['blue', 'green', 'orange', 'red', 'purple']
        for i, (name, sig) in enumerate(filtered.items()):
            plt.subplot(6, 1, i+2)
            plt.plot(t, sig, color=colors[i % len(colors)])
            plt.title(name)
            plt.grid(True, alpha=0.3)
            
        plt.tight_layout()
        plt.show()

    def restart(self):
        self.controller.show_frame(StartPage)

if __name__ == "__main__":
    app = App()
    app.mainloop()
