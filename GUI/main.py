import tkinter as tk
import pygame

# ================== KONFIGURASI ==================
QUESTION_DURATION = 5      # detik per soal
TOTAL_QUESTIONS = 5
PROCESS_DURATION = 5000    # ms (3 detik proses sebelum hasil)

# ================== INIT AUDIO ==================
pygame.mixer.init()

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

    def _update(self):
        if not self.running:
            return

        minutes = self.elapsed_time // 60
        seconds = self.elapsed_time % 60
        self.label.config(text=f"{minutes:02d}:{seconds:02d}")

        self.elapsed_time += 1

        if self.on_tick:
            self.on_tick(self.elapsed_time)

        self.parent.after(1000, self._update)


# ================== MAIN APP ==================
class App(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Tes Disleksia")
        self.attributes("-fullscreen", True)
        self.bind("<Escape>", lambda e: self.destroy())

        self.current_question = 1
        self.test_result = None

        self.container = tk.Frame(self, bg="white")
        self.container.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.frames = {}
        for F in (StartPage, TestPage, ProcessPage, ResultPage):
            frame = F(self.container, self)
            self.frames[F] = frame
            frame.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.show_frame(StartPage)

    def show_frame(self, page):
        self.frames[page].tkraise()


# ================== HALAMAN 1 ==================
class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller

        tk.Label(
            self,
            text="TES DISLEKSIA",
            font=("Arial", 86, "bold"),
            bg="white"
        ).place(relx=0.5, rely=0.35, anchor="center")

        tk.Button(
            self,
            text="MULAI",
            font=("Arial", 76),
            width=15,
            height=2,
            command=self.start_with_audio
        ).place(relx=0.5, rely=0.6, anchor="center")

    def start_with_audio(self):
        pygame.mixer.music.load("audio/soal 1.mp3")
        pygame.mixer.music.play()
        self.check_audio_finished()

    def check_audio_finished(self):
        if pygame.mixer.music.get_busy():
            self.after(200, self.check_audio_finished)
        else:
            self.controller.show_frame(TestPage)
            self.controller.frames[TestPage].stopwatch.start()


# ================== HALAMAN 2 (TES) ==================
class TestPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller

        self.label_timer = tk.Label(
            self,
            text="00:00",
            font=("Arial", 350, "bold"),
            bg="white"
        )
        self.label_timer.place(relx=0.5, rely=0.45, anchor="center")

        self.label_question = tk.Label(
            self,
            text="Soal ke-1",
            font=("Arial", 100),
            bg="white"
        )
        self.label_question.place(relx=0.5, rely=0.75, anchor="center")

        self.stopwatch = Stopwatch(
            self,
            self.label_timer,
            on_tick=self.on_tick
        )

    def on_tick(self, elapsed_time):
        if elapsed_time >= QUESTION_DURATION * self.controller.current_question+1:
            self.next_question()

    def next_question(self):
        if self.controller.current_question < TOTAL_QUESTIONS:
            self.controller.current_question += 1
            self.label_question.config(
                text=f"Soal ke-{self.controller.current_question}"
            )

            pygame.mixer.music.load(
                f"audio/soal {self.controller.current_question}.mp3"
            )
            pygame.mixer.music.play()
        else:
            self.finish_test()

    def finish_test(self):
        self.stopwatch.stop()

        pygame.mixer.music.load("audio/tes selesai.mp3")
        pygame.mixer.music.play()

        # Tentukan hasil (placeholder)
        self.controller.test_result = "DISLEKSIA"

        self.controller.show_frame(ProcessPage)
        self.controller.frames[ProcessPage].start_processing()


# ================== HALAMAN PROSES ==================
class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller

        self.label = tk.Label(
            self,
            text="Memproses hasil...",
            font=("Arial", 80),
            bg="white"
        )
        self.label.place(relx=0.5, rely=0.5, anchor="center")

    def start_processing(self):
        self.after(PROCESS_DURATION, self.show_result)

    def show_result(self):
        result_page = self.controller.frames[ResultPage]
        result_page.set_result(self.controller.test_result)
        self.controller.show_frame(ResultPage)


# ================== HALAMAN HASIL ==================
class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="white")
        self.controller = controller

        self.label_result = tk.Label(
            self,
            text="",
            font=("Arial", 120, "bold"),
            bg="white"
        )
        self.label_result.place(relx=0.5, rely=0.5, anchor="center")

    def set_result(self, result_text):
        self.label_result.config(text=result_text)


# ================== RUN ==================
if __name__ == "__main__":
    app = App()
    app.mainloop()
