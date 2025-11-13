"""
Main application entry point for Real-Time Audio Transcription & AI Assistant.
"""

import sys
import json
import logging
import threading
import queue
from datetime import datetime
from pathlib import Path
from typing import Optional
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
import pystray
from PIL import Image, ImageDraw
import keyboard
import numpy as np
import sounddevice as sd

from audio_capture import AudioCapture
from transcription import TranscriptionEngine
from question_detector import QuestionDetector
from answer_generator import AnswerGenerator

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Set CustomTkinter appearance
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class TranscriptionApp(ctk.CTk):
    """Main application window."""
    
    def __init__(self):
        super().__init__()
        
        # Load configuration
        self.config = self.load_config()
        
        # Initialize components
        self.audio_capture: Optional[AudioCapture] = None
        self.transcription_engine: Optional[TranscriptionEngine] = None
        self.question_detector: Optional[QuestionDetector] = None
        self.answer_generator: Optional[AnswerGenerator] = None
        
        # State
        self.is_recording = False
        self.auto_answer = self.config.get("auto_answer", True)
        self.message_queue = queue.Queue()
        
        # Setup UI
        self.setup_ui()
        self.setup_system_tray()
        self.setup_keyboard_shortcuts()
        
        # Check Ollama on startup
        self.check_ollama_status()
        
        # Start message processing
        self.process_messages()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def load_config(self) -> dict:
        """Load configuration from file."""
        # Handle both regular execution and PyInstaller bundled .exe
        if getattr(sys, 'frozen', False):
            # Running as compiled .exe
            base_path = Path(sys._MEIPASS)
            config_path = base_path / "config.json"
        else:
            # Running as script
            config_path = Path("config.json")
        
        # Also check current directory (for user-modified config)
        user_config_path = Path("config.json")
        
        # Try user config first, then bundled config
        for path in [user_config_path, config_path]:
            if path.exists():
                try:
                    with open(path, 'r') as f:
                        config = json.load(f)
                        logger.info(f"Loaded config from: {path}")
                        return config
                except Exception as e:
                    logger.error(f"Failed to load config from {path}: {e}")
        
        # Default config
        logger.info("Using default configuration")
        return {
            "whisper_model": "base",
            "ollama_model": "llama3.2:3b",
            "ollama_url": "http://localhost:11434",
            "auto_answer": True,
            "detection_sensitivity": 0.7,
            "conversation_context_exchanges": 3,
            "transcription_buffer_minutes": 5,
            "audio_chunk_duration_seconds": 3,
            "window_geometry": {"width": 1000, "height": 700},
            "theme": "dark"
        }
    
    def save_config(self):
        """Save configuration to file."""
        try:
            # Always save to current directory (user's config)
            config_path = Path("config.json")
            with open(config_path, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Config saved to: {config_path}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def setup_ui(self):
        """Setup the user interface."""
        self.title("Real-Time Audio Transcription & AI Assistant")
        
        # Set window geometry
        width = self.config.get("window_geometry", {}).get("width", 1000)
        height = self.config.get("window_geometry", {}).get("height", 700)
        self.geometry(f"{width}x{height}")
        
        # Main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        
        # Top bar with controls
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        self.top_frame.grid_columnconfigure(1, weight=1)
        
        # Record button
        self.record_button = ctk.CTkButton(
            self.top_frame,
            text="Start Recording",
            command=self.toggle_recording,
            width=150,
            height=40,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        self.record_button.grid(row=0, column=0, padx=10, pady=10)
        
        # Status label
        self.status_label = ctk.CTkLabel(
            self.top_frame,
            text="Status: Idle",
            font=ctk.CTkFont(size=12)
        )
        self.status_label.grid(row=0, column=1, padx=10, pady=10, sticky="w")
        
        # Settings button
        self.settings_button = ctk.CTkButton(
            self.top_frame,
            text="⚙️ Settings",
            command=self.open_settings,
            width=100,
            height=40
        )
        self.settings_button.grid(row=0, column=2, padx=10, pady=10)
        
        # Diagnose button
        self.diagnose_button = ctk.CTkButton(
            self.top_frame,
            text="🔍 Diagnose",
            command=self.run_diagnostic,
            width=100,
            height=40,
            fg_color="gray",
            hover_color="darkgray"
        )
        self.diagnose_button.grid(row=0, column=3, padx=10, pady=10)
        
        # Klaxon button (for Windows Sound Mixer detection)
        self.klaxon_button = ctk.CTkButton(
            self.top_frame,
            text="🔊 Test Audio",
            command=self.play_klaxon,
            width=100,
            height=40,
            fg_color="orange",
            hover_color="darkorange"
        )
        self.klaxon_button.grid(row=0, column=4, padx=10, pady=10)
        
        # Main content area (tabbed)
        self.tabview = ctk.CTkTabview(self)
        self.tabview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        
        # Transcription tab
        self.transcription_tab = self.tabview.add("Transcription")
        self.setup_transcription_tab()
        
        # Questions tab
        self.questions_tab = self.tabview.add("Questions")
        self.setup_questions_tab()
        
        # Answers tab
        self.answers_tab = self.tabview.add("Answers")
        self.setup_answers_tab()
        
        # Bottom status bar
        self.bottom_frame = ctk.CTkFrame(self)
        self.bottom_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        self.ollama_status_label = ctk.CTkLabel(
            self.bottom_frame,
            text="Ollama: Checking...",
            font=ctk.CTkFont(size=10)
        )
        self.ollama_status_label.pack(side="left", padx=10, pady=5)
        
        self.model_label = ctk.CTkLabel(
            self.bottom_frame,
            text=f"Models: Whisper {self.config.get('whisper_model', 'base')}, Ollama {self.config.get('ollama_model', 'llama3.2:3b')}",
            font=ctk.CTkFont(size=10)
        )
        self.model_label.pack(side="right", padx=10, pady=5)
    
    def setup_transcription_tab(self):
        """Setup transcription tab."""
        self.transcription_tab.grid_columnconfigure(0, weight=1)
        self.transcription_tab.grid_rowconfigure(0, weight=1)
        
        # Scrollable text area
        self.transcription_text = ctk.CTkTextbox(
            self.transcription_tab,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.transcription_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Buttons frame
        buttons_frame = ctk.CTkFrame(self.transcription_tab)
        buttons_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            buttons_frame,
            text="Clear",
            command=self.clear_transcription,
            width=100
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="Answer Selected",
            command=self.answer_selected_text,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="Export",
            command=self.export_conversation,
            width=100
        ).pack(side="left", padx=5)
    
    def setup_questions_tab(self):
        """Setup questions tab."""
        self.questions_tab.grid_columnconfigure(0, weight=1)
        self.questions_tab.grid_rowconfigure(0, weight=1)
        
        self.questions_text = ctk.CTkTextbox(
            self.questions_tab,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.questions_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        buttons_frame = ctk.CTkFrame(self.questions_tab)
        buttons_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            buttons_frame,
            text="Clear",
            command=self.clear_questions,
            width=100
        ).pack(side="left", padx=5)
    
    def setup_answers_tab(self):
        """Setup answers tab."""
        self.answers_tab.grid_columnconfigure(0, weight=1)
        self.answers_tab.grid_rowconfigure(0, weight=1)
        
        self.answers_text = ctk.CTkTextbox(
            self.answers_tab,
            wrap="word",
            font=ctk.CTkFont(size=12)
        )
        self.answers_text.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        buttons_frame = ctk.CTkFrame(self.answers_tab)
        buttons_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        
        ctk.CTkButton(
            buttons_frame,
            text="Copy Last Answer",
            command=self.copy_last_answer,
            width=150
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            buttons_frame,
            text="Clear",
            command=self.clear_answers,
            width=100
        ).pack(side="left", padx=5)
    
    def setup_system_tray(self):
        """Setup system tray icon."""
        # Create icon
        image = Image.new('RGB', (64, 64), color='black')
        draw = ImageDraw.Draw(image)
        draw.ellipse([16, 16, 48, 48], fill='blue', outline='white')
        
        menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Hide", self.hide_window),
            pystray.MenuItem("Quit", self.quit_app)
        )
        
        self.tray_icon = pystray.Icon("TranscriptionApp", image, "Audio Transcription", menu)
        
        # Start tray in separate thread
        tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        tray_thread.start()
    
    def setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts."""
        try:
            keyboard.add_hotkey('ctrl+shift+a', self.toggle_window_visibility)
            logger.info("Keyboard shortcuts enabled (Ctrl+Shift+A to show/hide)")
        except Exception as e:
            logger.warning(f"Failed to setup keyboard shortcut (may require admin rights): {e}")
            logger.info("Keyboard shortcuts disabled. You can still use the system tray icon.")
    
    def check_ollama_status(self):
        """Check if Ollama is running."""
        if not self.answer_generator:
            self.answer_generator = AnswerGenerator(
                model=self.config.get("ollama_model", "llama3.2:3b"),
                base_url=self.config.get("ollama_url", "http://localhost:11434")
            )
        
        if self.answer_generator.check_ollama_running():
            if self.answer_generator.check_model_available():
                self.ollama_status_label.configure(text="Ollama: Running ✓", text_color="green")
            else:
                self.ollama_status_label.configure(
                    text=f"Ollama: Running (Model {self.config.get('ollama_model')} not found)",
                    text_color="orange"
                )
        else:
            self.ollama_status_label.configure(text="Ollama: Not Running ✗", text_color="red")
    
    def toggle_recording(self):
        """Start or stop recording."""
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()
    
    def start_recording(self):
        """Start audio capture and transcription."""
        try:
            # Initialize components
            if not self.transcription_engine:
                self.transcription_engine = TranscriptionEngine(
                    model_size=self.config.get("whisper_model", "base")
                )
            
            if not self.question_detector:
                self.question_detector = QuestionDetector(
                    sensitivity=self.config.get("detection_sensitivity", 0.7)
                )
            
            # Initialize audio capture with phrase-aware settings
            self.audio_capture = AudioCapture(
                chunk_duration=self.config.get("audio_chunk_duration_seconds", 3.0),
                callback=self.on_audio_chunk,
                silence_threshold=self.config.get("silence_detection_threshold", 0.015),
                min_silence_duration=self.config.get("min_silence_duration_seconds", 1.0),
                max_buffer_duration=self.config.get("max_buffer_duration_seconds", 10.0)
            )
            
            self.audio_capture.start()
            self.is_recording = True
            
            # Update UI
            self.record_button.configure(text="Stop Recording", fg_color="red", hover_color="darkred")
            self.status_label.configure(text="Status: Recording...", text_color="green")
            
            logger.info("Recording started")
            
        except RuntimeError as e:
            error_msg = str(e)
            logger.error(f"Failed to start recording: {e}")
            
            # Provide helpful error messages
            if "No loopback audio device found" in error_msg:
                help_text = (
                    "No loopback audio device was found.\n\n"
                    "To capture system audio, you need:\n\n"
                    "Windows:\n"
                    "• Enable 'Stereo Mix' in Sound settings, OR\n"
                    "• Install VB-Audio Virtual Cable\n\n"
                    "macOS:\n"
                    "• Install BlackHole virtual audio driver\n\n"
                    "Run 'python diagnose_audio.py' for detailed diagnosis."
                )
                messagebox.showerror("No Loopback Device Found", help_text)
            else:
                messagebox.showerror("Error", f"Failed to start recording:\n{str(e)}")
            self.is_recording = False
        except Exception as e:
            logger.error(f"Failed to start recording: {e}")
            error_details = (
                f"Error: {str(e)}\n\n"
                "Troubleshooting:\n"
                "1. Run 'python diagnose_audio.py' to check your audio setup\n"
                "2. Make sure your virtual cable/loopback device is installed\n"
                "3. Restart the application after installing audio devices\n"
                "4. Check the console logs for more details"
            )
            messagebox.showerror("Recording Error", error_details)
            self.is_recording = False
    
    def stop_recording(self):
        """Stop audio capture."""
        logger.info("Stop recording requested")
        
        if self.audio_capture:
            try:
                self.audio_capture.stop()
            except Exception as e:
                logger.error(f"Error stopping audio capture: {e}")
            finally:
                self.audio_capture = None
        
        self.is_recording = False
        
        # Update UI (use after() to ensure it happens in main thread)
        self.after(0, lambda: self.record_button.configure(
            text="Start Recording", 
            fg_color=None, 
            hover_color=None
        ))
        self.after(0, lambda: self.status_label.configure(
            text="Status: Idle", 
            text_color="gray"
        ))
        
        logger.info("Recording stopped")
    
    def on_audio_chunk(self, audio_data):
        """Handle audio chunk from capture."""
        if not self.is_recording:
            return
            
        if not self.transcription_engine:
            logger.warning("Transcription engine not initialized")
            return
        
        # Check if audio has actual content (not silence)
        audio_level = np.abs(audio_data).mean() if hasattr(audio_data, 'mean') else 0
        if audio_level < 0.001:  # Very quiet, likely silence
            logger.debug("Skipping silent audio chunk")
            return
        
        # Process in separate thread to avoid blocking
        def process():
            try:
                logger.debug(f"Processing audio chunk, level: {audio_level:.4f}")
                text = self.transcription_engine.transcribe_chunk(audio_data)
                if text and text.strip():
                    logger.info(f"Transcribed: {text[:50]}...")
                    
                    # Check if text ends with sentence-ending punctuation
                    text_ends_with_sentence = self._ends_with_sentence(text)
                    
                    # Accumulate text until we have a complete sentence
                    if not hasattr(self, '_pending_transcription'):
                        self._pending_transcription = ""
                    
                    self._pending_transcription += " " + text if self._pending_transcription else text
                    self._pending_transcription = self._pending_transcription.strip()
                    
                    # Only process if we have a complete sentence or the buffer is getting long
                    if text_ends_with_sentence or len(self._pending_transcription) > 200:
                        final_text = self._pending_transcription
                        self._pending_transcription = ""  # Clear buffer
                        
                        self.message_queue.put(("transcription", final_text))
                        
                        # Check for questions
                        if self.question_detector:
                            is_question, confidence = self.question_detector.is_question(final_text)
                            if is_question:
                                logger.info(f"Question detected: {final_text[:50]}...")
                                self.message_queue.put(("question", (final_text, confidence)))
                                
                                # Auto-answer if enabled
                                if self.auto_answer and self.answer_generator:
                                    self.message_queue.put(("answer_request", final_text))
                    else:
                        # Partial sentence - wait for more
                        logger.debug(f"Accumulating sentence: {self._pending_transcription[:50]}...")
                else:
                    logger.debug("No text transcribed from audio chunk")
            except Exception as e:
                logger.error(f"Error processing audio chunk: {e}")
        
        threading.Thread(target=process, daemon=True).start()
    
    def _ends_with_sentence(self, text: str) -> bool:
        """Check if text ends with sentence-ending punctuation."""
        if not text:
            return False
        
        text = text.strip()
        # Check for sentence endings: period, question mark, exclamation mark
        # Also check for common sentence-ending patterns
        sentence_endings = ['.', '!', '?']
        
        # Check if ends with punctuation
        if text and text[-1] in sentence_endings:
            # Make sure it's not an abbreviation (basic check)
            if len(text) > 2 and text[-2] not in sentence_endings:
                return True
        
        # Also check for common sentence-ending words followed by punctuation
        sentence_end_words = ['thanks', 'thank you', 'please', 'okay', 'ok', 'sure', 'yes', 'no', 
                              'alright', 'got it', 'understood', 'perfect', 'great', 'fine']
        text_lower = text.lower()
        for word in sentence_end_words:
            if text_lower.endswith(word) and len(text) > len(word) + 1:
                return True
        
        return False
    
    def process_messages(self):
        """Process messages from queue (runs in main thread)."""
        try:
            while True:
                msg_type, data = self.message_queue.get_nowait()
                
                if msg_type == "transcription":
                    self.append_transcription(data)
                elif msg_type == "question":
                    question, confidence = data
                    self.append_question(question, confidence)
                elif msg_type == "answer_request":
                    self.generate_answer_async(data)
                elif msg_type == "answer":
                    question, answer = data
                    self.append_answer(question, answer)
                    
        except queue.Empty:
            pass
        
        # Schedule next check
        self.after(100, self.process_messages)
    
    def append_transcription(self, text: str):
        """Append text to transcription view."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.transcription_text.insert("end", f"[{timestamp}] {text}\n")
        self.transcription_text.see("end")
    
    def append_question(self, question: str, confidence: float):
        """Append question to questions view."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        conf_text = f"({confidence:.0%})" if confidence < 1.0 else ""
        self.questions_text.insert("end", f"[{timestamp}] {conf_text} {question}\n")
        self.questions_text.see("end")
        
        # Show notification
        self.show_notification("Question detected!")
    
    def append_answer(self, question: str, answer: str):
        """Append answer to answers view."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.answers_text.insert("end", f"[{timestamp}] Q: {question}\n")
        self.answers_text.insert("end", f"A: {answer}\n\n")
        self.answers_text.see("end")
    
    def generate_answer_async(self, question: str):
        """Generate answer asynchronously."""
        def generate():
            try:
                context = None
                if self.transcription_engine:
                    context = self.transcription_engine.get_recent_context(
                        self.config.get("conversation_context_exchanges", 3)
                    )
                
                answer = self.answer_generator.generate_answer(question, context)
                if answer:
                    self.message_queue.put(("answer", (question, answer)))
            except Exception as e:
                logger.error(f"Error generating answer: {e}")
        
        threading.Thread(target=generate, daemon=True).start()
    
    def answer_selected_text(self):
        """Answer selected text manually."""
        try:
            selected = self.transcription_text.selection_get()
            if selected and self.answer_generator:
                self.generate_answer_async(selected.strip())
                self.status_label.configure(text="Status: Generating answer...", text_color="blue")
        except:
            messagebox.showwarning("No Selection", "Please select some text first.")
    
    def copy_last_answer(self):
        """Copy last answer to clipboard."""
        try:
            content = self.answers_text.get("1.0", "end-1c")
            if content:
                # Get last answer block
                lines = content.strip().split("\n")
                last_answer = ""
                for line in reversed(lines):
                    if line.startswith("A: "):
                        last_answer = line[3:]
                        break
                
                if last_answer:
                    self.clipboard_clear()
                    self.clipboard_append(last_answer)
                    self.show_notification("Answer copied to clipboard!")
                else:
                    messagebox.showinfo("No Answer", "No answer found to copy.")
        except Exception as e:
            logger.error(f"Error copying answer: {e}")
    
    def clear_transcription(self):
        """Clear transcription view."""
        self.transcription_text.delete("1.0", "end")
        if self.transcription_engine:
            self.transcription_engine.clear_buffer()
    
    def clear_questions(self):
        """Clear questions view."""
        self.questions_text.delete("1.0", "end")
    
    def clear_answers(self):
        """Clear answers view."""
        self.answers_text.delete("1.0", "end")
    
    def export_conversation(self):
        """Export conversation to file."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=== TRANSCRIPTION ===\n")
                    f.write(self.transcription_text.get("1.0", "end-1c"))
                    f.write("\n\n=== QUESTIONS ===\n")
                    f.write(self.questions_text.get("1.0", "end-1c"))
                    f.write("\n\n=== ANSWERS ===\n")
                    f.write(self.answers_text.get("1.0", "end-1c"))
                
                messagebox.showinfo("Export", f"Conversation exported to {filename}")
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def open_settings(self):
        """Open settings window."""
        SettingsWindow(self, self.config, self.on_settings_saved)
    
    def run_diagnostic(self):
        """Run audio diagnostic tool."""
        import subprocess
        import sys
        
        try:
            # Run the diagnostic script
            result = subprocess.run(
                [sys.executable, "diagnose_audio.py"],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Show results in a dialog
            output = result.stdout
            if result.stderr:
                output += f"\n\nErrors:\n{result.stderr}"
            
            # Create a scrollable text window
            dialog = ctk.CTkToplevel(self)
            dialog.title("Audio Diagnostic Results")
            dialog.geometry("700x500")
            dialog.transient(self)
            
            text_widget = ctk.CTkTextbox(dialog, wrap="word", font=ctk.CTkFont(family="Courier", size=10))
            text_widget.pack(fill="both", expand=True, padx=10, pady=10)
            text_widget.insert("1.0", output)
            text_widget.configure(state="disabled")
            
            ctk.CTkButton(
                dialog,
                text="Close",
                command=dialog.destroy,
                width=100
            ).pack(pady=10)
            
        except subprocess.TimeoutExpired:
            messagebox.showerror("Error", "Diagnostic tool timed out.")
        except FileNotFoundError:
            messagebox.showerror("Error", "diagnose_audio.py not found. Please run it manually from the command line.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to run diagnostic:\n{str(e)}")
    
    def play_klaxon(self):
        """Play a goofy klaxon sound to register with Windows Sound Mixer."""
        def generate_klaxon_sound():
            """Generate a goofy klaxon sound."""
            import time
            sample_rate = 44100
            duration = 0.5  # seconds per beep
            
            try:
                # Play a series of goofy klaxon beeps
                for i in range(3):
                    # Varying frequencies for goofy effect
                    if i == 0:
                        freq1, freq2 = 400, 600  # Low to mid
                    elif i == 1:
                        freq1, freq2 = 300, 800  # Wide range
                    else:
                        freq1, freq2 = 500, 700  # Mid range
                    
                    # Generate a warbling klaxon sound
                    t = np.linspace(0, duration, int(sample_rate * duration))
                    
                    # Create a warbling effect (frequency modulation)
                    modulation = np.sin(2 * np.pi * 5 * t)  # 5 Hz modulation
                    frequency = freq1 + (freq2 - freq1) * (modulation + 1) / 2
                    
                    # Generate the tone with some harmonics for a harsher sound
                    wave = np.sin(2 * np.pi * frequency * t)
                    # Add harmonics for klaxon-like sound
                    wave += 0.3 * np.sin(2 * np.pi * frequency * 2 * t)
                    wave += 0.2 * np.sin(2 * np.pi * frequency * 3 * t)
                    
                    # Apply envelope (fade in/out)
                    envelope = np.ones_like(t)
                    fade_samples = int(sample_rate * 0.05)  # 50ms fade
                    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
                    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
                    wave *= envelope
                    
                    # Normalize
                    wave = wave / np.max(np.abs(wave)) * 0.5
                    
                    # Play the sound
                    sd.play(wave, sample_rate)
                    sd.wait()  # Wait for playback to finish
                    
                    # Small pause between beeps
                    if i < 2:
                        time.sleep(0.1)
                
                logger.info("Klaxon sound played - app should now appear in Windows Sound Mixer")
                
            except Exception as e:
                logger.error(f"Error playing klaxon: {e}")
                # Fallback: try using winsound on Windows
                try:
                    import winsound
                    for _ in range(3):
                        winsound.Beep(500, 200)
                        time.sleep(0.1)
                except:
                    messagebox.showwarning("Audio Error", f"Could not play sound:\n{str(e)}")
        
        # Play in a separate thread to avoid blocking UI
        threading.Thread(target=generate_klaxon_sound, daemon=True).start()
        
        # Update button text temporarily
        original_text = self.klaxon_button.cget("text")
        self.klaxon_button.configure(text="🔊 Playing...", state="disabled")
        self.after(2000, lambda: self.klaxon_button.configure(text=original_text, state="normal"))
    
    def on_settings_saved(self, new_config: dict):
        """Handle settings save."""
        self.config.update(new_config)
        self.save_config()
        
        # Update components
        if self.question_detector:
            self.question_detector.set_sensitivity(self.config.get("detection_sensitivity", 0.7))
        
        if self.answer_generator:
            self.answer_generator.set_model(self.config.get("ollama_model", "llama3.2:3b"))
        
        self.auto_answer = self.config.get("auto_answer", True)
        self.model_label.configure(
            text=f"Models: Whisper {self.config.get('whisper_model', 'base')}, Ollama {self.config.get('ollama_model', 'llama3.2:3b')}"
        )
        
        self.check_ollama_status()
    
    def show_notification(self, message: str):
        """Show a notification (simple for now)."""
        # Could be enhanced with a toast notification
        logger.info(f"Notification: {message}")
    
    def toggle_window_visibility(self):
        """Toggle window visibility."""
        if self.winfo_viewable():
            self.hide_window()
        else:
            self.show_window()
    
    def show_window(self, icon=None, item=None):
        """Show the window."""
        self.deiconify()
        self.lift()
        self.focus()
    
    def hide_window(self, icon=None, item=None):
        """Hide the window."""
        self.withdraw()
    
    def quit_app(self, icon=None, item=None):
        """Quit the application."""
        self.stop_recording()
        self.destroy()
        if self.tray_icon:
            self.tray_icon.stop()
        sys.exit(0)
    
    def on_closing(self):
        """Handle window close event."""
        self.hide_window()
    
    def destroy(self):
        """Cleanup on destroy."""
        self.stop_recording()
        super().destroy()


class SettingsWindow(ctk.CTkToplevel):
    """Settings window."""
    
    def __init__(self, parent, config: dict, callback):
        super().__init__(parent)
        
        self.config = config.copy()
        self.callback = callback
        
        self.title("Settings")
        self.geometry("500x600")
        self.transient(parent)
        self.grab_set()
        
        # Main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Whisper model
        ctk.CTkLabel(main_frame, text="Whisper Model:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        self.whisper_model_var = ctk.StringVar(value=config.get("whisper_model", "base"))
        ctk.CTkOptionMenu(
            main_frame,
            values=["tiny", "base", "small", "medium", "large"],
            variable=self.whisper_model_var
        ).pack(fill="x", pady=5)
        
        # Ollama model
        ctk.CTkLabel(main_frame, text="Ollama Model:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        self.ollama_model_var = ctk.StringVar(value=config.get("ollama_model", "llama3.2:3b"))
        ollama_entry = ctk.CTkEntry(main_frame, textvariable=self.ollama_model_var)
        ollama_entry.pack(fill="x", pady=5)
        
        # Auto-answer
        self.auto_answer_var = ctk.BooleanVar(value=config.get("auto_answer", True))
        ctk.CTkCheckBox(
            main_frame,
            text="Auto-answer detected questions",
            variable=self.auto_answer_var
        ).pack(anchor="w", pady=10)
        
        # Detection sensitivity
        ctk.CTkLabel(main_frame, text="Question Detection Sensitivity:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        self.sensitivity_var = ctk.DoubleVar(value=config.get("detection_sensitivity", 0.7))
        sensitivity_slider = ctk.CTkSlider(
            main_frame,
            from_=0.0,
            to=1.0,
            variable=self.sensitivity_var,
            number_of_steps=10
        )
        sensitivity_slider.pack(fill="x", pady=5)
        self.sensitivity_label = ctk.CTkLabel(main_frame, text=f"{self.sensitivity_var.get():.1f}")
        self.sensitivity_label.pack(anchor="w")
        sensitivity_slider.configure(command=lambda v: self.sensitivity_label.configure(text=f"{v:.1f}"))
        
        # Context exchanges
        ctk.CTkLabel(main_frame, text="Conversation Context (exchanges):", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        self.context_var = ctk.IntVar(value=config.get("conversation_context_exchanges", 3))
        context_slider = ctk.CTkSlider(
            main_frame,
            from_=1,
            to=10,
            variable=self.context_var,
            number_of_steps=9
        )
        context_slider.pack(fill="x", pady=5)
        self.context_label = ctk.CTkLabel(main_frame, text=str(self.context_var.get()))
        self.context_label.pack(anchor="w")
        context_slider.configure(command=lambda v: self.context_label.configure(text=str(int(v))))
        
        # Buttons
        buttons_frame = ctk.CTkFrame(main_frame)
        buttons_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(
            buttons_frame,
            text="Save",
            command=self.save_settings,
            width=120
        ).pack(side="left", padx=5, expand=True)
        
        ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self.destroy,
            width=120
        ).pack(side="left", padx=5, expand=True)
    
    def save_settings(self):
        """Save settings."""
        self.config["whisper_model"] = self.whisper_model_var.get()
        self.config["ollama_model"] = self.ollama_model_var.get()
        self.config["auto_answer"] = self.auto_answer_var.get()
        self.config["detection_sensitivity"] = self.sensitivity_var.get()
        self.config["conversation_context_exchanges"] = self.context_var.get()
        
        self.callback(self.config)
        self.destroy()


if __name__ == "__main__":
    app = TranscriptionApp()
    app.mainloop()

