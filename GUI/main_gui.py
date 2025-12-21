import tkinter as tk
from tkinter import ttk
import pygame
import math

# ================== KONFIGURASI ==================
QUESTION_DURATION = 5      # detik per soal
TOTAL_QUESTIONS = 5
PROCESS_DURATION = 3000    # ms (3 detik proses sebelum hasil)

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
        
        # Get screen dimensions
        self.screen_width = self.winfo_screenwidth()
        self.screen_height = self.winfo_screenheight()

        self.current_question = 1
        self.test_result = None

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


# ================== INTRO PAGE (LOGO STYLE) ==================
class IntroPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller
        
        # Main container dengan scrollable canvas untuk responsive
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Content frame
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="nw")
        
        # Bind resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)
        
        # Logo container - mengisi sebagian besar layar
        self.logo_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.logo_frame.pack(expand=True, fill="both", pady=(50, 30))
        
        # Try to load company logo
        self.logo_label = None
        self.load_company_logo()
        
        # Jika logo tidak ada, tampilkan text fallback besar
        if self.logo_label is None:
            # Logo text besar - hampir fullscreen
            self.logo_text = tk.Label(
                self.logo_frame,
                text="TES DISLEKSIA",
                font=("Arial", 180, "bold"),
                bg="#f5f7fa",
                fg="#2c5aa0"
            )
            self.logo_text.pack(expand=True)
        
        # Loading bar section - di bagian bawah layar
        self.loading_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.loading_frame.pack(side="bottom", pady=60)
        
        # Progress bar canvas - lebih besar dan clean
        self.progress_canvas = tk.Canvas(
            self.loading_frame,
            width=800,
            height=15,
            bg="#f5f7fa",
            highlightthickness=0
        )
        self.progress_canvas.pack()
        
        self.alpha = 0
        self.progress_value = 0
        self.progress_t = 0.0

    def load_company_logo(self):
        """Load logo perusahaan dari file .ico, .jpg, .png, atau .jpeg - FULLSCREEN SIZE"""
        logo_paths = [
            "logo.ico",
            "logo.png", 
            "logo.jpg",
            "logo.jpeg",
            "assets/logo.ico",
            "assets/logo.png",
            "assets/logo.jpg",
            "assets/logo.jpeg",
            "images/logo.ico",
            "images/logo.png",
            "images/logo.jpg",
            "images/logo.jpeg"
        ]
        
        for logo_path in logo_paths:
            try:
                from PIL import Image, ImageTk
                import os
                
                if os.path.exists(logo_path):
                    # Load image
                    img = Image.open(logo_path)
                    
                    # Get screen dimensions
                    screen_width = self.controller.screen_width
                    screen_height = self.controller.screen_height
                    
                    # Calculate max size - 80% of screen height, or 90% of width
                    # Use the smaller dimension to ensure it fits
                    max_height = int(screen_height * 0.75)  # 75% tinggi layar
                    max_width = int(screen_width * 0.85)    # 85% lebar layar

                    ratio = min(
                        max_width / img.width,
                        max_height / img.height
                    )

                    new_size = (
                        int(img.width * ratio *0.9),
                        int(img.height * ratio *0.9)
                    )

                    img = img.resize(new_size, Image.Resampling.LANCZOS)
                    
                    # Resize logo - maintain aspect ratio, fill most of screen
                    # img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
                    
                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(img)
                    
                    # Create label with logo
                    self.logo_label = tk.Label(
                        self.logo_frame,
                        image=photo,
                        bg="#f5f7fa"
                    )
                    self.logo_label.image = photo  # Keep reference
                    self.logo_label.pack()
                    
                    print(f"Logo loaded successfully from: {logo_path}")
                    print(f"Logo size: {img.size[0]}x{img.size[1]} pixels")
                    return
            except ImportError:
                print("PIL/Pillow not installed. Install with: pip install Pillow")
                break
            except Exception as e:
                print(f"Could not load logo from {logo_path}: {e}")
                continue
        
        print("No logo found. Using text fallback.")

    def on_canvas_configure(self, event):
        # Center the content
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
        # if self.progress_value < 100:
        if self.progress_t < 1.0:
            # self.progress_value += 0.8

            # Kecepatan animasi (semakin kecil = lebih halus)
            self.progress_t += 0.008

            # EASING SINUS (ease-in-out)
            # eased = 0.5 - 0.5 * math.cos(math.pi * self.progress_t)
            eased = 1 - pow(2, -10 * self.progress_t)
            # eased = self.progress_t * self.progress_t * (3 - 2 * self.progress_t)

            # Convert ke persen
            self.progress_value = eased * 100
            
            
            # Draw minimalist progress bar
            self.progress_canvas.delete("all")
            
            # Background track - rounded
            self.progress_canvas.create_rectangle(
                0, 0, 800, 15,
                fill="#e1e8ed",
                outline="",
                width=0
            )
            
            # Progress fill - smooth gradient-like dengan rounded ends
            progress_width = int(800 * (self.progress_value / 100))
            if progress_width > 0:
                # Main progress bar dengan warna gradient
                self.progress_canvas.create_rectangle(
                    0, 0, progress_width, 15,
                    fill="#4a90e2",
                    outline="",
                    width=0
                )
                
                # Highlight effect di ujung untuk efek "glow"
                if progress_width > 25:
                    self.progress_canvas.create_rectangle(
                        progress_width - 25, 0, progress_width, 15,
                        fill="#5ba3f5",
                        outline="",
                        width=0
                    )
            
            self.after(35, self.animate_progress)
        else:
            self.after(500, self.go_to_start)

    def go_to_start(self):
        self.controller.show_frame(StartPage)
        self.controller.frames[StartPage].animate_entrance()


# ================== HALAMAN START ==================
class StartPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        # Canvas untuk centering
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Content frame
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        
        # Bind resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Title section dengan spacing
        self.title_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.title_frame.pack(pady=(0, 20))

        # Main title
        self.title_label = tk.Label(
            self.title_frame,
            text="TES DISLEKSIA",
            font=("Arial", 95, "bold"),
            bg="#f5f7fa",
            fg="#2c5aa0"
        )
        self.title_label.pack(pady=(0, 15))
        
        # Title underline
        self.title_line = tk.Frame(self.title_frame, bg="#4a90e2", height=6)
        self.title_line.pack(fill="x", padx=80)

        # Description dengan padding
        self.desc_label = tk.Label(
            self.content_frame,
            text="Tekan tombol di bawah untuk memulai tes",
            font=("Arial", 38),
            bg="#f5f7fa",
            fg="#5a6c7d",
            wraplength=900
        )
        self.desc_label.pack(pady=35)

        # Button frame untuk spacing
        self.button_frame = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.button_frame.pack(pady=30)

        # Start Button dengan shadow effect
        self.button_shadow = tk.Frame(
            self.button_frame,
            bg="#b8c9e0",
            height=8
        )
        self.button_shadow.pack(pady=(0, 0))

        self.start_button = tk.Button(
            self.button_frame,
            text="MULAI TES",
            font=("Arial", 65, "bold"),
            bg="#4a90e2",
            fg="white",
            activebackground="#2c5aa0",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=70,
            pady=30,
            command=self.start_with_audio
        )
        self.start_button.pack()
        
        # Bind hover effects
        self.start_button.bind("<Enter>", self.on_hover)
        self.start_button.bind("<Leave>", self.on_leave)

    def on_canvas_configure(self, event):
        # Center the content
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def on_hover(self, event):
        self.start_button.config(bg="#2c5aa0")

    def on_leave(self, event):
        self.start_button.config(bg="#4a90e2")

    def animate_entrance(self):
        # Content already centered
        pass

    def start_with_audio(self):
        try:
            pygame.mixer.music.load("audio/soal 1.mp3")
            pygame.mixer.music.play()
        except:
            pass
        
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
        self.controller.frames[TestPage].stopwatch.start()


# ================== HALAMAN TEST ==================
class TestPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        # Canvas untuk layout
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Content frame
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        
        # Bind resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Progress indicator di atas dengan spacing
        self.progress_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.progress_container.pack(pady=(0, 40))
        
        self.progress_label = tk.Label(
            self.progress_container,
            text="Soal 1 dari 5",
            font=("Arial", 48, "bold"),
            bg="#f5f7fa",
            fg="#2c5aa0"
        )
        self.progress_label.pack()

        # Timer section dengan spacing
        self.timer_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.timer_container.pack(pady=35)

        # Timer dengan border dan shadow
        self.timer_shadow = tk.Frame(
            self.timer_container,
            bg="#c1d5e8"
        )
        self.timer_shadow.pack(padx=8, pady=8)

        self.timer_frame = tk.Frame(
            self.timer_container,
            bg="white",
            highlightbackground="#4a90e2",
            highlightthickness=6
        )
        self.timer_frame.pack()

        self.label_timer = tk.Label(
            self.timer_frame,
            text="00:00",
            font=("Arial", 240, "bold"),
            bg="white",
            fg="#2c5aa0",
            padx=70,
            pady=35
        )
        self.label_timer.pack()

        # Question section dengan spacing
        self.question_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.question_container.pack(pady=(40, 0))

        # Question dengan background
        self.question_frame = tk.Frame(
            self.question_container,
            bg="#4a90e2"
        )
        self.question_frame.pack()

        self.label_question = tk.Label(
            self.question_frame,
            text="Soal ke-1",
            font=("Arial", 72, "bold"),
            bg="#4a90e2",
            fg="white",
            padx=55,
            pady=25
        )
        self.label_question.pack()

        self.stopwatch = Stopwatch(
            self,
            self.label_timer,
            on_tick=self.on_tick
        )

    def on_canvas_configure(self, event):
        # Center the content
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def on_tick(self, elapsed_time):
        if elapsed_time >= QUESTION_DURATION * self.controller.current_question + 1:
            self.next_question()

    def next_question(self):
        if self.controller.current_question < TOTAL_QUESTIONS:
            self.controller.current_question += 1
            
            # Update progress
            self.progress_label.config(
                text=f"Soal {self.controller.current_question} dari {TOTAL_QUESTIONS}"
            )
            
            self.label_question.config(
                text=f"Soal ke-{self.controller.current_question}"
            )

            try:
                pygame.mixer.music.load(
                    f"audio/soal {self.controller.current_question}.mp3"
                )
                pygame.mixer.music.play()
            except:
                pass
        else:
            self.finish_test()

    def finish_test(self):
        self.stopwatch.stop()

        try:
            pygame.mixer.music.load("audio/tes selesai.mp3")
            pygame.mixer.music.play()
        except:
            pass

        # Tentukan hasil (placeholder)
        self.controller.test_result = "DISLEKSIA"

        self.controller.show_frame(ProcessPage)
        self.controller.frames[ProcessPage].start_processing()


# ================== HALAMAN PROSES ==================
class ProcessPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        # Canvas untuk centering
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Content frame
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        
        # Bind resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Title dengan spacing
        self.title_label = tk.Label(
            self.content_frame,
            text="MEMPROSES HASIL",
            font=("Arial", 85, "bold"),
            bg="#f5f7fa",
            fg="#2c5aa0"
        )
        self.title_label.pack(pady=(0, 20))

        # Animated dots
        self.dots_label = tk.Label(
            self.content_frame,
            text="",
            font=("Arial", 55),
            bg="#f5f7fa",
            fg="#5a6c7d"
        )
        self.dots_label.pack(pady=25)

        # Progress circle container dengan spacing
        self.circle_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.circle_container.pack(pady=30)

        # Canvas untuk circular progress
        self.progress_canvas = tk.Canvas(
            self.circle_container,
            width=420,
            height=420,
            bg="#f5f7fa",
            highlightthickness=0
        )
        self.progress_canvas.pack()

        self.angle = 0
        self.dots_count = 0

    def on_canvas_configure(self, event):
        # Center the content
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def start_processing(self):
        self.animate_circle()
        self.animate_dots()
        self.after(PROCESS_DURATION, self.show_result)

    def animate_circle(self):
        self.progress_canvas.delete("all")
        
        # Background circle
        self.progress_canvas.create_oval(
            60, 60, 360, 360,
            outline="#e1e8ed",
            width=18
        )
        
        # Animated arc
        extent = (self.angle % 360)
        self.progress_canvas.create_arc(
            60, 60, 360, 360,
            start=-90, extent=extent,
            outline="#4a90e2", width=18,
            style="arc"
        )
        
        # Center percentage
        self.progress_canvas.create_text(
            210, 210,
            text=f"{int((extent/360)*100)}%",
            font=("Arial", 65, "bold"),
            fill="#2c5aa0"
        )
        
        self.angle += 8
        
        if self.angle < 360:
            self.after(30, self.animate_circle)

    def animate_dots(self):
        dots = "." * (self.dots_count % 4)
        self.dots_label.config(text=f"Menganalisis data{dots}")
        self.dots_count += 1
        
        if self.angle < 360:
            self.after(300, self.animate_dots)

    def show_result(self):
        result_page = self.controller.frames[ResultPage]
        result_page.set_result(self.controller.test_result)
        self.controller.show_frame(ResultPage)


# ================== HALAMAN HASIL ==================
class ResultPage(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent, bg="#f5f7fa")
        self.controller = controller

        # Canvas untuk centering
        self.canvas = tk.Canvas(self, bg="#f5f7fa", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        
        # Content frame
        self.content_frame = tk.Frame(self.canvas, bg="#f5f7fa")
        self.canvas_window = self.canvas.create_window(0, 0, window=self.content_frame, anchor="center")
        
        # Bind resize
        self.canvas.bind('<Configure>', self.on_canvas_configure)

        # Title dengan spacing
        self.title_label = tk.Label(
            self.content_frame,
            text="HASIL TES",
            font=("Arial", 75, "bold"),
            bg="#f5f7fa",
            fg="#2c5aa0"
        )
        self.title_label.pack(pady=(0, 35))

        # Result container dengan spacing
        self.result_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.result_container.pack(pady=30)

        # Result dengan border dan shadow
        self.result_shadow = tk.Frame(
            self.result_container,
            bg="#c1d5e8"
        )
        self.result_shadow.pack(padx=8, pady=8)

        self.result_frame = tk.Frame(
            self.result_container,
            bg="white",
            highlightbackground="#4a90e2",
            highlightthickness=6
        )
        self.result_frame.pack()

        self.label_result = tk.Label(
            self.result_frame,
            text="",
            font=("Arial", 95, "bold"),
            bg="white",
            fg="#2c5aa0",
            padx=90,
            pady=50
        )
        self.label_result.pack()

        # Button container dengan spacing
        self.button_container = tk.Frame(self.content_frame, bg="#f5f7fa")
        self.button_container.pack(pady=(40, 0))

        # Restart button
        self.restart_button = tk.Button(
            self.button_container,
            text="TES ULANG",
            font=("Arial", 58, "bold"),
            bg="#4a90e2",
            fg="white",
            activebackground="#2c5aa0",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=60,
            pady=25,
            command=self.restart_test
        )
        self.restart_button.pack()
        
        # Bind hover
        self.restart_button.bind("<Enter>", self.on_hover)
        self.restart_button.bind("<Leave>", self.on_leave)

    def on_canvas_configure(self, event):
        # Center the content
        self.canvas.coords(self.canvas_window, event.width // 2, event.height // 2)

    def on_hover(self, event):
        self.restart_button.config(bg="#2c5aa0")

    def on_leave(self, event):
        self.restart_button.config(bg="#4a90e2")

    def set_result(self, result_text):
        self.label_result.config(text=result_text)

    def restart_test(self):
        # Reset state
        self.controller.current_question = 1
        self.controller.frames[TestPage].stopwatch.reset()
        self.controller.frames[TestPage].progress_label.config(text="Soal 1 dari 5")
        self.controller.frames[TestPage].label_question.config(text="Soal ke-1")
        
        # Kembali ke halaman start
        self.controller.show_frame(StartPage)


# ================== RUN ==================
if __name__ == "__main__":
    app = App()
    app.mainloop()