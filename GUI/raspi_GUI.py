import tkinter as tk
from tkinter import ttk
import pygame
import math

# ================== KONFIGURASI ==================
QUESTION_DURATION = 5
TOTAL_QUESTIONS = 5
PROCESS_DURATION = 3000

# ================== INIT AUDIO ==================
pygame.mixer.init()

# ================== STOPWATCH ==================
class Stopwatch:
    def __init__(self, parent, label, on_tick=None):
        self.parent = parent
        self.label = label
        self.on_tick = on_tick
        self.elapsed = 0
        self.running = False

    def start(self):
        if not self.running:
            self.running = True
            self._update()

    def stop(self):
        self.running = False

    def reset(self):
        self.elapsed = 0
        self.label.config(text="00:00")

    def _update(self):
        if not self.running:
            return
        m = self.elapsed // 60
        s = self.elapsed % 60
        self.label.config(text=f"{m:02d}:{s:02d}")
        self.elapsed += 1
        if self.on_tick:
            self.on_tick(self.elapsed)
        self.parent.after(1000, self._update)

# ================== APP ==================
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        # ===== TARGET RESOLUTION =====
        self.geometry("480x320")
        self.resizable(False, False)
        # self.attributes("-fullscreen", True)

        self.title("Tes Disleksia")

        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        # ===== SCALE SYSTEM =====
        self.BASE_W = 1920
        self.BASE_H = 1080
        self.SCALE = min(480 / self.BASE_W, 320 / self.BASE_H)

        def sf(x):
            return max(8, int(x * self.SCALE))
        self.sf = sf

        self.current_question = 1
        self.test_result = None

        self.container = tk.Frame(self, bg="#f5f7fa")
        self.container.pack(fill="both", expand=True)

        self.frames = {}
        for F in (IntroPage, StartPage, TestPage, ProcessPage, ResultPage):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.place(relwidth=1, relheight=1)

        self.show_frame(IntroPage)
        self.frames[IntroPage].start_intro()

    def show_frame(self, page):
        self.frames[page].tkraise()

# ================== INTRO ==================
class IntroPage(tk.Frame):
    def __init__(self, parent, c):
        super().__init__(parent, bg="#f5f7fa")

        self.label = tk.Label(
            self,
            text="TES DISLEKSIA",
            font=("Arial", c.sf(180), "bold"),
            fg="#2c5aa0",
            bg="#f5f7fa"
        )
        self.label.pack(expand=True)

    def start_intro(self):
        self.after(1500, lambda: self.master.master.show_frame(StartPage))

# ================== START ==================
class StartPage(tk.Frame):
    def __init__(self, parent, c):
        super().__init__(parent, bg="#f5f7fa")

        tk.Label(
            self,
            text="TES DISLEKSIA",
            font=("Arial", c.sf(95), "bold"),
            fg="#2c5aa0",
            bg="#f5f7fa"
        ).pack(pady=c.sf(15))

        tk.Label(
            self,
            text="Tekan tombol untuk memulai",
            font=("Arial", c.sf(38)),
            fg="#5a6c7d",
            bg="#f5f7fa"
        ).pack(pady=c.sf(10))

        tk.Button(
            self,
            text="MULAI TES",
            font=("Arial", c.sf(65), "bold"),
            bg="#4a90e2",
            fg="white",
            padx=c.sf(40),
            pady=c.sf(15),
            command=lambda: self.start(c)
        ).pack(pady=c.sf(20))

    def start(self, c):
        c.show_frame(TestPage)
        c.frames[TestPage].stopwatch.start()

# ================== TEST ==================
class TestPage(tk.Frame):
    def __init__(self, parent, c):
        super().__init__(parent, bg="#f5f7fa")

        self.progress = tk.Label(
            self,
            text="Soal 1 dari 5",
            font=("Arial", c.sf(48), "bold"),
            fg="#2c5aa0",
            bg="#f5f7fa"
        )
        self.progress.pack(pady=c.sf(5))

        self.timer = tk.Label(
            self,
            text="00:00",
            font=("Arial", c.sf(240), "bold"),
            fg="#2c5aa0",
            bg="white"
        )
        self.timer.pack(pady=c.sf(5))

        self.question = tk.Label(
            self,
            text="Soal ke-1",
            font=("Arial", c.sf(72), "bold"),
            fg="white",
            bg="#4a90e2",
            padx=c.sf(20),
            pady=c.sf(10)
        )
        self.question.pack(pady=c.sf(10))

        self.stopwatch = Stopwatch(self, self.timer, self.on_tick)

    def on_tick(self, t):
        if t >= QUESTION_DURATION * self.master.master.current_question:
            self.next()

    def next(self):
        c = self.master.master
        if c.current_question < TOTAL_QUESTIONS:
            c.current_question += 1
            self.progress.config(text=f"Soal {c.current_question} dari {TOTAL_QUESTIONS}")
            self.question.config(text=f"Soal ke-{c.current_question}")
        else:
            self.stopwatch.stop()
            c.test_result = "DISLEKSIA"
            c.show_frame(ProcessPage)
            c.frames[ProcessPage].start()

# ================== PROCESS ==================
class ProcessPage(tk.Frame):
    def __init__(self, parent, c):
        super().__init__(parent, bg="#f5f7fa")

        self.label = tk.Label(
            self,
            text="Memproses...",
            font=("Arial", c.sf(65), "bold"),
            fg="#2c5aa0",
            bg="#f5f7fa"
        )
        self.label.pack(expand=True)

    def start(self):
        self.after(PROCESS_DURATION, lambda: self.master.master.show_frame(ResultPage))

# ================== RESULT ==================
class ResultPage(tk.Frame):
    def __init__(self, parent, c):
        super().__init__(parent, bg="#f5f7fa")

        self.result = tk.Label(
            self,
            text="",
            font=("Arial", c.sf(95), "bold"),
            fg="#2c5aa0",
            bg="white",
            padx=c.sf(30),
            pady=c.sf(20)
        )
        self.result.pack(pady=c.sf(15))

        tk.Button(
            self,
            text="TES ULANG",
            font=("Arial", c.sf(58), "bold"),
            bg="#4a90e2",
            fg="white",
            padx=c.sf(30),
            pady=c.sf(15),
            command=self.restart
        ).pack()

    def tkraise(self, *args):
        self.result.config(text=self.master.master.test_result)
        super().tkraise(*args)

    def restart(self):
        c = self.master.master
        c.current_question = 1
        c.show_frame(StartPage)

# ================== RUN ==================
if __name__ == "__main__":
    App().mainloop()
