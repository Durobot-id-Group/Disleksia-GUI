#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import tkinter as tk
from tkinter import scrolledtext
import threading
import time
import random
import numpy as np

# ================= ENV FIX (RASPI + SYSTEMD) =================
os.environ.setdefault("SDL_AUDIODRIVER", "alsa")
os.environ.setdefault("SDL_VIDEODRIVER", "x11")

import pygame
pygame.mixer.init()

# ================= KONFIG =================
APP_TITLE = "Aplikasi Tes Disleksia EEG"
WINDOW_SIZE = "1024x600"

# ================= ANALISIS (AMAN / DUMMY) =================
def deteksi_disleksia_riset(delta, theta, alpha, beta, gamma, fs):
    score = random.uniform(0, 100)

    return {
        "ok": True,
        "analysis": {
            "diagnosis": "DISLEKSIA" if score > 50 else "NORMAL",
            "confidence": "Tinggi" if score > 70 else "Sedang",
            "confidence_score": score,
            "kriteria_terpenuhi": int(score // 20),
            "total_kriteria": 5,
            "kriteria": {
                "Delta":  {"description": "Dominansi Delta",  "value": float(delta.mean()),  "passed": True},
                "Theta":  {"description": "Dominansi Theta",  "value": float(theta.mean()),  "passed": True},
                "Alpha":  {"description": "Penurunan Alpha",  "value": float(alpha.mean()),  "passed": False},
                "Beta":   {"description": "Stabilitas Beta",  "value": float(beta.mean()),   "passed": True},
                "Gamma":  {"description": "Noise Gamma",      "value": float(gamma.mean()), "passed": False},
            }
        }
    }

# ================= APP =================
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry(WINDOW_SIZE)
        self.configure(bg="#f5f7fa")

        self.analysis_results = None

        container = tk.Frame(self, bg="#f5f7fa")
        container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (HomePage, TestPage, ResultPage):
            frame = F(container, self)
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        self.show_frame(HomePage)

    def show_frame(self, page):
        self.frames[page].tkraise()

# ================= HOME =================
class HomePage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        tk.Label(
            self,
            text="TES DISLEKSIA BERBASIS EEG",
            font=("Arial", 24, "bold"),
            bg="#f5f7fa"
        ).pack(pady=40)

        tk.Button(
            self,
            text="Mulai Tes",
            font=("Arial", 18),
            width=20,
            command=lambda: controller.show_frame(TestPage)
        ).pack()

# ================= TEST =================
class TestPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        tk.Label(
            self,
            text="Pengambilan data EEG...",
            font=("Arial", 18),
            bg="#f5f7fa"
        ).pack(pady=30)

        tk.Button(
            self,
            text="Mulai Tes (Simulasi)",
            font=("Arial", 16),
            command=self.start_test
        ).pack()

    def start_test(self):
        threading.Thread(target=self.run_test, daemon=True).start()

    def run_test(self):
        time.sleep(3)

        fs = 256
        delta = np.random.rand(100)
        theta = np.random.rand(100)
        alpha = np.random.rand(100)
        beta  = np.random.rand(100)
        gamma = np.random.rand(100)

        self.controller.analysis_results = deteksi_disleksia_riset(
            delta, theta, alpha, beta, gamma, fs
        )

        result_page = self.controller.frames[ResultPage]
        result_page.set_result()
        self.controller.show_frame(ResultPage)

# ================= RESULT =================
class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        tk.Label(
            self,
            text="HASIL TES",
            font=("Arial", 22, "bold"),
            bg="#f5f7fa"
        ).pack(pady=10)

        self.label_result = tk.Label(
            self,
            text="",
            font=("Arial", 26, "bold"),
            bg="white",
            padx=30,
            pady=15
        )
        self.label_result.pack(pady=10)

        self.detail_text = scrolledtext.ScrolledText(
            self,
            width=90,
            height=15,
            wrap="word"
        )
        self.detail_text.pack(pady=10)

        tk.Button(
            self,
            text="Kembali ke Home",
            command=lambda: controller.show_frame(HomePage)
        ).pack(pady=10)

    # 🔥 SATU-SATUNYA TEMPAT AKSES analysis_results
    def set_result(self):
        self.detail_text.delete("1.0", tk.END)

        ar = self.controller.analysis_results
        if ar is None or not ar.get("ok"):
            self.label_result.config(text="ANALISIS GAGAL", fg="red")
            self.detail_text.insert(tk.END, "Data belum tersedia.\n")
            return

        analysis = ar["analysis"]

        self.label_result.config(
            text=analysis["diagnosis"],
            fg="red" if analysis["diagnosis"] == "DISLEKSIA" else "green"
        )

        self.detail_text.insert(
            tk.END,
            f"Confidence: {analysis['confidence']} ({analysis['confidence_score']:.1f}%)\n"
        )
        self.detail_text.insert(
            tk.END,
            f"Kriteria terpenuhi: {analysis['kriteria_terpenuhi']} / {analysis['total_kriteria']}\n\n"
        )

        self.detail_text.insert(tk.END, "=== Detail Kriteria ===\n")
        for k in analysis["kriteria"].values():
            status = "TERPENUHI" if k["passed"] else "TIDAK"
            self.detail_text.insert(
                tk.END,
                f"{k['description']} → {status} (nilai {k['value']:.2f})\n"
            )

# ================= MAIN =================
if __name__ == "__main__":
    app = App()
    app.mainloop()
