"""
Main application entry point for Real-Time Audio Transcription & AI Assistant.
"""

import sys
import os
import json
import logging
import threading
import queue
import platform
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

# Modern Apple-style colors
APPLE_BG = "#1e1e1e"
APPLE_FG = "#ffffff"
APPLE_SECONDARY = "#2d2d2d"
APPLE_ACCENT = "#007aff"
APPLE_ACCENT_HOVER = "#0051d5"
APPLE_TEXT_SECONDARY = "#8e8e93"
APPLE_DIVIDER = "#38383a"
APPLE_RED = "#ff3b30"
APPLE_RED_HOVER = "#d70015"


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
        self.tray_icon = None  # Initialize tray_icon to None
        
        # State
        self.is_recording = False
        self.auto_answer = self.config.get("auto_answer", True)
        self.message_queue = queue.Queue()
        
        # Setup UI
        self.setup_ui()
        # Setup system tray (may fail on some systems - that's OK)
        try:
            self.setup_system_tray()
        except Exception as e:
            logger.warning(f"System tray setup failed (non-critical): {e}")
            self.tray_icon = None
        self.setup_keyboard_shortcuts()
        
        # Check Ollama on startup
        self.check_ollama_status()
        
        # Start message processing
        self.process_messages()
        
        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # Ensure window is visible on startup
        self.deiconify()
        self.lift()
        self.focus()
    
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
            "window_geometry": {"width": 1600, "height": 1000},
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
        self.title("Audio Transcription")
        
        # Set window geometry - optimized for fullscreen/large displays
        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()
        
        # Use 90% of screen size by default, or config value if set
        default_width = int(screen_width * 0.9)
        default_height = int(screen_height * 0.85)
        
        width = self.config.get("window_geometry", {}).get("width", default_width)
        height = self.config.get("window_geometry", {}).get("height", default_height)
        
        # Center window on screen
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        
        self.geometry(f"{width}x{height}+{x}+{y}")
        
        # Configure main container
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)  # Content area should expand
        
        # Header section with title and main control
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.grid(row=0, column=0, sticky="ew", padx=50, pady=(40, 30))
        header_frame.grid_columnconfigure(1, weight=1)
        
        # Left side - Title and quick stats
        left_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        left_header.grid(row=0, column=0, sticky="w")
        
        title_label = ctk.CTkLabel(
            left_header,
            text="Audio Transcription",
            font=ctk.CTkFont(size=36, weight="normal")
        )
        title_label.pack(anchor="w")
        
        # Quick stats
        stats_frame = ctk.CTkFrame(left_header, fg_color="transparent")
        stats_frame.pack(anchor="w", pady=(12, 0))
        
        self.stats_label = ctk.CTkLabel(
            stats_frame,
            text="0 transcriptions • 0 questions • 0 answers",
            font=ctk.CTkFont(size=14),
            text_color=APPLE_TEXT_SECONDARY
        )
        self.stats_label.pack(side="left", padx=(0, 20))
        
        # Recording time indicator
        self.recording_time_label = ctk.CTkLabel(
            stats_frame,
            text="",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=APPLE_ACCENT
        )
        self.recording_time_label.pack(side="left")
        
        # Right side - Main controls
        right_header = ctk.CTkFrame(header_frame, fg_color="transparent")
        right_header.grid(row=0, column=1, sticky="e")
        
        # Secondary header buttons
        header_buttons = ctk.CTkFrame(right_header, fg_color="transparent")
        header_buttons.pack(side="top", anchor="e", pady=(0, 15))
        
        ctk.CTkButton(
            header_buttons,
            text="New Session",
            command=self.new_session,
            width=140,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            header_buttons,
            text="History",
            command=self.show_history,
            width=110,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            header_buttons,
            text="Help",
            command=self.show_help,
            width=90,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left")
        
        # Main record button - large and prominent
        self.record_button = ctk.CTkButton(
            right_header,
            text="Start Recording",
            command=self.toggle_recording,
            width=220,
            height=60,
            font=ctk.CTkFont(size=18, weight="normal"),
            fg_color=APPLE_ACCENT,
            hover_color=APPLE_ACCENT_HOVER,
            corner_radius=12
        )
        self.record_button.pack(side="top", anchor="e")
        
        # Status indicator with audio level
        status_container = ctk.CTkFrame(self, fg_color="transparent")
        status_container.grid(row=1, column=0, sticky="ew", padx=50, pady=(0, 25))
        
        left_status = ctk.CTkFrame(status_container, fg_color="transparent")
        left_status.pack(side="left")
        
        self.status_label = ctk.CTkLabel(
            left_status,
            text="Ready",
            font=ctk.CTkFont(size=16),
            text_color=APPLE_TEXT_SECONDARY
        )
        self.status_label.pack(side="left", padx=(0, 20))
        
        # Audio level indicator
        audio_level_frame = ctk.CTkFrame(left_status, fg_color="transparent")
        audio_level_frame.pack(side="left")
        
        ctk.CTkLabel(
            audio_level_frame,
            text="Audio Level:",
            font=ctk.CTkFont(size=14),
            text_color=APPLE_TEXT_SECONDARY
        ).pack(side="left", padx=(0, 8))
        
        self.audio_level_label = ctk.CTkLabel(
            audio_level_frame,
            text="--",
            font=ctk.CTkFont(size=14),
            text_color=APPLE_TEXT_SECONDARY
        )
        self.audio_level_label.pack(side="left")
        
        # Audio level bar
        self.audio_level_bar = ctk.CTkProgressBar(
            left_status,
            width=150,
            height=8,
            corner_radius=4,
            progress_color=APPLE_ACCENT
        )
        self.audio_level_bar.pack(side="left", padx=(15, 0))
        self.audio_level_bar.set(0)
        
        # Right side status - device info
        right_status = ctk.CTkFrame(status_container, fg_color="transparent")
        right_status.pack(side="right")
        
        self.device_label = ctk.CTkLabel(
            right_status,
            text="Device: Auto",
            font=ctk.CTkFont(size=14),
            text_color=APPLE_TEXT_SECONDARY
        )
        self.device_label.pack(side="right")
        
        # Main content area with unified view
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=2, column=0, sticky="nsew", padx=50, pady=(0, 30))
        content_frame.grid_columnconfigure(0, weight=1)
        content_frame.grid_rowconfigure(0, weight=1)
        
        # Unified text view with sections
        self.main_text = ctk.CTkTextbox(
            content_frame,
            wrap="word",
            font=ctk.CTkFont(size=16, family="SF Pro Text"),
            corner_radius=15,
            border_width=0
        )
        self.main_text.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # Action buttons at bottom
        actions_frame = ctk.CTkFrame(self, fg_color="transparent")
        actions_frame.grid(row=3, column=0, sticky="ew", padx=50, pady=(0, 30))
        
        # Left side - Primary actions
        primary_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        primary_frame.pack(side="left")
        
        ctk.CTkButton(
            primary_frame,
            text="Answer Selected",
            command=self.answer_selected_text,
            width=170,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            primary_frame,
            text="Summarize",
            command=self.summarize_text,
            width=140,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            primary_frame,
            text="Translate",
            command=self.translate_text,
            width=130,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        # Middle - File actions
        file_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        file_frame.pack(side="left", padx=(30, 0))
        
        ctk.CTkButton(
            file_frame,
            text="Save",
            command=self.save_session,
            width=120,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            file_frame,
            text="Export",
            command=self.export_conversation,
            width=130,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            file_frame,
            text="Copy All",
            command=self.copy_all_text,
            width=130,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            file_frame,
            text="Clear",
            command=self.clear_all,
            width=110,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left")
        
        # Right side - Settings and tools
        tools_frame = ctk.CTkFrame(actions_frame, fg_color="transparent")
        tools_frame.pack(side="right")
        
        ctk.CTkButton(
            tools_frame,
            text="Audio Settings",
            command=self.open_audio_settings,
            width=160,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 12))
        
        ctk.CTkButton(
            tools_frame,
            text="Settings",
            command=self.open_settings,
            width=130,
            height=44,
            font=ctk.CTkFont(size=15),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left")
        
        # Bottom status bar - minimal
        bottom_frame = ctk.CTkFrame(self, fg_color="transparent", height=40)
        bottom_frame.grid(row=4, column=0, sticky="ew", padx=50, pady=(0, 30))
        bottom_frame.grid_columnconfigure(0, weight=1)
        
        self.ollama_status_label = ctk.CTkLabel(
            bottom_frame,
            text="Checking connection...",
            font=ctk.CTkFont(size=13),
            text_color=APPLE_TEXT_SECONDARY
        )
        self.ollama_status_label.grid(row=0, column=0, sticky="w")
        
        self.model_label = ctk.CTkLabel(
            bottom_frame,
            text="",
            font=ctk.CTkFont(size=13),
            text_color=APPLE_TEXT_SECONDARY
        )
        self.model_label.grid(row=0, column=1, sticky="e")
        
        # Store references for unified view
        self.transcription_buffer = []
        self.questions_buffer = []
        self.answers_buffer = []
        self.recording_start_time = None
        self.update_recording_timer()
    
    
    def setup_system_tray(self):
        """Setup system tray icon."""
        self.tray_icon = None
        
        # On macOS, system tray can cause crashes - disable it by default
        # Set DISABLE_SYSTEM_TRAY=0 to enable it
        if platform.system() == 'Darwin' and os.environ.get('DISABLE_SYSTEM_TRAY', '1') == '1':
            logger.debug("System tray disabled on macOS (set DISABLE_SYSTEM_TRAY=0 to enable)")
            return
        
        try:
            # On macOS, system tray can cause crashes if not properly configured
            # Make it more robust by catching all exceptions
            image = Image.new('RGB', (64, 64), color='black')
            draw = ImageDraw.Draw(image)
            draw.ellipse([16, 16, 48, 48], fill='blue', outline='white')
        
            menu = pystray.Menu(
            pystray.MenuItem("Show", self.show_window),
            pystray.MenuItem("Hide", self.hide_window),
            pystray.MenuItem("Quit", self.quit_app)
            )
        
            self.tray_icon = pystray.Icon("TranscriptionApp", image, "Audio Transcription", menu)
        
            # Start tray in separate thread with better error handling
            def run_tray_safely():
                try:
                    self.tray_icon.run()
                except Exception as e:
                    logger.debug(f"System tray thread error (non-critical): {e}")
            
            tray_thread = threading.Thread(target=run_tray_safely, daemon=True)
            tray_thread.start()
            logger.debug("System tray icon initialized")
        except Exception as e:
            # System tray is optional - app works without it
            # Don't log as warning since this is common on macOS
            logger.debug(f"System tray disabled (non-critical): {e}")
            self.tray_icon = None
    
    def setup_keyboard_shortcuts(self):
        """Setup global keyboard shortcuts."""
        # On macOS, keyboard shortcuts require admin rights (sudo)
        # The keyboard library starts a background thread that fails without admin rights
        # and prints errors to stderr. We skip keyboard shortcuts on macOS by default
        # to avoid these harmless but noisy errors.
        # Users can still use the system tray icon to show/hide the window.
        if platform.system() == 'Darwin':
            # Skip keyboard shortcuts on macOS - they require admin rights
            # The app works perfectly fine without them
            logger.debug("Keyboard shortcuts skipped on macOS (requires admin rights)")
            return
        
        # On Windows/Linux, try to enable shortcuts
        try:
            keyboard.add_hotkey('ctrl+shift+a', self.toggle_window_visibility)
            logger.info("Keyboard shortcuts enabled (Ctrl+Shift+A to show/hide)")
        except Exception as e:
            logger.debug(f"Keyboard shortcuts disabled: {e}")
    
    def check_ollama_status(self):
        """Check if Ollama is running."""
        if not self.answer_generator:
            self.answer_generator = AnswerGenerator(
                model=self.config.get("ollama_model", "llama3.2:3b"),
                base_url=self.config.get("ollama_url", "http://localhost:11434")
            )
        
        if self.answer_generator.check_ollama_running():
            if self.answer_generator.check_model_available():
                self.ollama_status_label.configure(text="Connected", text_color=APPLE_ACCENT)
                model_name = self.config.get('ollama_model', 'llama3.2:3b')
                whisper_model = self.config.get('whisper_model', 'base')
                self.model_label.configure(text=f"{whisper_model} • {model_name}")
            else:
                self.ollama_status_label.configure(
                    text=f"Model {self.config.get('ollama_model')} not found",
                    text_color="#ff9500"
                )
        else:
            self.ollama_status_label.configure(text="Not connected", text_color=APPLE_TEXT_SECONDARY)
    
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
            # Allow device selection from config (None = auto-detect)
            audio_device = self.config.get("audio_device_index", None)
            self.audio_capture = AudioCapture(
                chunk_duration=self.config.get("audio_chunk_duration_seconds", 3.0),
                callback=self.on_audio_chunk,
                silence_threshold=self.config.get("silence_detection_threshold", 0.015),
                min_silence_duration=self.config.get("min_silence_duration_seconds", 1.0),
                max_buffer_duration=self.config.get("max_buffer_duration_seconds", 10.0),
                device=audio_device
            )
            
            self.audio_capture.start()
            self.is_recording = True
            self.recording_start_time = datetime.now()
            
            # Update UI
            self.record_button.configure(
                text="Stop Recording", 
                fg_color=APPLE_RED, 
                hover_color=APPLE_RED_HOVER
            )
            self.status_label.configure(text="Recording", text_color=APPLE_ACCENT)
            
            # Update device label
            devices = sd.query_devices()
            if audio_device is not None and audio_device < len(devices):
                device_name = devices[audio_device]['name']
                self.device_label.configure(text=f"Device: {device_name[:30]}")
            else:
                self.device_label.configure(text="Device: Auto")
            
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
        self.recording_start_time = None
        
        # Update UI (use after() to ensure it happens in main thread)
        self.after(0, lambda: self.record_button.configure(
            text="Start Recording", 
            fg_color=APPLE_ACCENT, 
            hover_color=APPLE_ACCENT_HOVER
        ))
        self.after(0, lambda: self.status_label.configure(
            text="Ready", 
            text_color=APPLE_TEXT_SECONDARY
        ))
        self.after(0, lambda: self.audio_level_bar.set(0))
        self.after(0, lambda: self.audio_level_label.configure(text="--"))
        
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
        
        # Update audio level indicator
        self.after(0, lambda: self.update_audio_level(audio_level))
        
        if audio_level < 0.001:  # Very quiet, likely silence
            logger.debug(f"Skipping silent audio chunk (level: {audio_level:.6f})")
            return
        
        logger.debug(f"Processing audio chunk: {len(audio_data)} samples, level: {audio_level:.6f}")
        
        # Process in separate thread to avoid blocking
        def process():
            try:
                logger.info(f"Transcribing audio chunk: {len(audio_data)} samples, level: {audio_level:.6f}")
                text = self.transcription_engine.transcribe_chunk(audio_data)
                if text and text.strip():
                    logger.info(f"✓ Transcribed: {text[:100]}...")
                    
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
                        
                        logger.info(f"✓ Adding to UI: {final_text[:100]}...")
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
                    logger.debug(f"No text transcribed from audio chunk (text={text})")
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
        """Append text to unified view."""
        timestamp = datetime.now().strftime("%H:%M")
        self.transcription_buffer.append((timestamp, text))
        self._update_main_view()
        self._update_stats()
    
    def append_question(self, question: str, confidence: float):
        """Append question to unified view."""
        timestamp = datetime.now().strftime("%H:%M")
        self.questions_buffer.append((timestamp, question, confidence))
        self._update_main_view()
        self._update_stats()
    
    def append_answer(self, question: str, answer: str):
        """Append answer to unified view."""
        timestamp = datetime.now().strftime("%H:%M")
        self.answers_buffer.append((timestamp, question, answer))
        self._update_main_view()
        self._update_stats()
    
    def _update_main_view(self):
        """Update the unified main text view."""
        self.main_text.delete("1.0", "end")
        
        # Build unified content
        content = []
        
        # Show recent transcriptions
        if self.transcription_buffer:
            content.append("Transcription\n")
            content.append("─" * 50 + "\n\n")
            for timestamp, text in self.transcription_buffer[-10:]:
                content.append(f"{text}\n")
            content.append("\n")
        
        # Show questions
        if self.questions_buffer:
            content.append("Questions\n")
            content.append("─" * 50 + "\n\n")
            for timestamp, question, confidence in self.questions_buffer[-5:]:
                content.append(f"{question}\n")
            content.append("\n")
        
        # Show answers
        if self.answers_buffer:
            content.append("Answers\n")
            content.append("─" * 50 + "\n\n")
            for timestamp, question, answer in self.answers_buffer[-5:]:
                content.append(f"Q: {question}\n")
                content.append(f"A: {answer}\n\n")
        
        if not content:
            content.append("Start recording to see transcriptions here.\n")
        
        self.main_text.insert("1.0", "".join(content))
        self.main_text.see("end")
    
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
            selected = self.main_text.selection_get()
            if selected and self.answer_generator:
                self.generate_answer_async(selected.strip())
                self.status_label.configure(text="Generating answer...", text_color=APPLE_ACCENT)
        except:
            messagebox.showwarning("No Selection", "Please select some text first.")
    
    def clear_all(self):
        """Clear all content."""
        self.transcription_buffer.clear()
        self.questions_buffer.clear()
        self.answers_buffer.clear()
        self.main_text.delete("1.0", "end")
        if self.transcription_engine:
            self.transcription_engine.clear_buffer()
        self._update_stats()
    
    def _update_stats(self):
        """Update statistics display."""
        trans_count = len(self.transcription_buffer)
        quest_count = len(self.questions_buffer)
        ans_count = len(self.answers_buffer)
        self.stats_label.configure(
            text=f"{trans_count} transcriptions • {quest_count} questions • {ans_count} answers"
        )
    
    def update_recording_timer(self):
        """Update recording time display."""
        if self.is_recording and self.recording_start_time:
            elapsed = datetime.now() - self.recording_start_time
            minutes = int(elapsed.total_seconds() // 60)
            seconds = int(elapsed.total_seconds() % 60)
            self.recording_time_label.configure(text=f"Recording: {minutes:02d}:{seconds:02d}")
        else:
            self.recording_time_label.configure(text="")
        self.after(1000, self.update_recording_timer)
    
    def update_audio_level(self, level: float):
        """Update audio level indicator."""
        normalized_level = min(level * 10, 1.0)  # Scale for visibility
        self.audio_level_bar.set(normalized_level)
        if level > 0.001:
            self.audio_level_label.configure(text=f"{level:.3f}")
        else:
            self.audio_level_label.configure(text="--")
    
    def new_session(self):
        """Start a new session."""
        if messagebox.askyesno("New Session", "Start a new session? Current data will be cleared."):
            self.clear_all()
            self.recording_start_time = None
    
    def show_history(self):
        """Show session history."""
        messagebox.showinfo("History", "Session history feature coming soon.")
    
    def show_help(self):
        """Show help dialog."""
        help_text = """Audio Transcription Help

Keyboard Shortcuts:
• Ctrl+Shift+A: Show/Hide window
• Space: Start/Stop recording (when focused)

Features:
• Real-time audio transcription
• Automatic question detection
• AI-powered answers
• Export and save sessions

For more information, visit the documentation."""
        messagebox.showinfo("Help", help_text)
    
    def summarize_text(self):
        """Summarize selected text."""
        try:
            selected = self.main_text.selection_get()
            if selected:
                messagebox.showinfo("Summarize", "Text summarization feature coming soon.")
            else:
                messagebox.showwarning("No Selection", "Please select some text first.")
        except:
            messagebox.showwarning("No Selection", "Please select some text first.")
    
    def translate_text(self):
        """Translate selected text."""
        try:
            selected = self.main_text.selection_get()
            if selected:
                messagebox.showinfo("Translate", "Translation feature coming soon.")
            else:
                messagebox.showwarning("No Selection", "Please select some text first.")
        except:
            messagebox.showwarning("No Selection", "Please select some text first.")
    
    def save_session(self):
        """Save current session."""
        if not self.transcription_buffer and not self.questions_buffer and not self.answers_buffer:
            messagebox.showinfo("Save", "No content to save.")
            return
        messagebox.showinfo("Save", "Session save feature coming soon.")
    
    def copy_all_text(self):
        """Copy all text to clipboard."""
        content = self.main_text.get("1.0", "end-1c")
        if content:
            self.clipboard_clear()
            self.clipboard_append(content)
            messagebox.showinfo("Copied", "All text copied to clipboard.")
        else:
            messagebox.showinfo("Copy", "No content to copy.")
    
    def open_audio_settings(self):
        """Open audio settings dialog."""
        messagebox.showinfo("Audio Settings", "Audio device selection and configuration coming soon.")
    
    def export_conversation(self):
        """Export conversation to file."""
        try:
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=== TRANSCRIPTION ===\n\n")
                    for timestamp, text in self.transcription_buffer:
                        f.write(f"[{timestamp}] {text}\n")
                    
                    f.write("\n\n=== QUESTIONS ===\n\n")
                    for timestamp, question, confidence in self.questions_buffer:
                        f.write(f"[{timestamp}] {question}\n")
                    
                    f.write("\n\n=== ANSWERS ===\n\n")
                    for timestamp, question, answer in self.answers_buffer:
                        f.write(f"[{timestamp}] Q: {question}\n")
                        f.write(f"A: {answer}\n\n")
                
                messagebox.showinfo("Export", f"Conversation exported to {filename}")
        except Exception as e:
            logger.error(f"Error exporting conversation: {e}")
            messagebox.showerror("Error", f"Failed to export: {str(e)}")
    
    def open_settings(self):
        """Open settings window."""
        SettingsWindow(self, self.config, self.on_settings_saved)
    
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
        model_name = self.config.get('ollama_model', 'llama3.2:3b')
        whisper_model = self.config.get('whisper_model', 'base')
        self.model_label.configure(text=f"{whisper_model} • {model_name}")
        
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
        self.geometry("520x750")
        self.transient(parent)
        self.grab_set()
        
        # Header
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=30, pady=(30, 20))
        
        title = ctk.CTkLabel(
            header,
            text="Settings",
            font=ctk.CTkFont(size=24, weight="normal")
        )
        title.pack(anchor="w")
        
        # Main frame
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=30, pady=(0, 20))
        
        # Section: Models
        section_label = ctk.CTkLabel(
            main_frame,
            text="Models",
            font=ctk.CTkFont(size=13, weight="normal"),
            text_color=APPLE_TEXT_SECONDARY
        )
        section_label.pack(anchor="w", pady=(10, 15))
        
        # Whisper model
        ctk.CTkLabel(
            main_frame,
            text="Whisper Model",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", pady=(0, 8))
        
        self.whisper_model_var = ctk.StringVar(value=config.get("whisper_model", "base"))
        whisper_menu = ctk.CTkOptionMenu(
            main_frame,
            values=["tiny", "base", "small", "medium", "large"],
            variable=self.whisper_model_var,
            width=200,
            height=36,
            corner_radius=8,
            fg_color=APPLE_SECONDARY,
            button_color=APPLE_SECONDARY,
            button_hover_color=APPLE_DIVIDER
        )
        whisper_menu.pack(anchor="w", pady=(0, 20))
        
        # Ollama model
        ctk.CTkLabel(
            main_frame,
            text="Ollama Model",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", pady=(0, 8))
        
        self.ollama_model_var = ctk.StringVar(value=config.get("ollama_model", "llama3.2:3b"))
        ollama_entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.ollama_model_var,
            width=200,
            height=36,
            corner_radius=8,
            border_width=0,
            fg_color=APPLE_SECONDARY
        )
        ollama_entry.pack(anchor="w", pady=(0, 30))
        
        # Section: Behavior
        section_label2 = ctk.CTkLabel(
            main_frame,
            text="Behavior",
            font=ctk.CTkFont(size=13, weight="normal"),
            text_color=APPLE_TEXT_SECONDARY
        )
        section_label2.pack(anchor="w", pady=(10, 15))
        
        # Auto-answer
        self.auto_answer_var = ctk.BooleanVar(value=config.get("auto_answer", True))
        ctk.CTkCheckBox(
            main_frame,
            text="Automatically answer detected questions",
            variable=self.auto_answer_var,
            font=ctk.CTkFont(size=14),
            corner_radius=6
        ).pack(anchor="w", pady=(0, 30))
        
        # Detection sensitivity
        sensitivity_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        sensitivity_frame.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            sensitivity_frame,
            text="Question Detection Sensitivity",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w")
        
        slider_frame = ctk.CTkFrame(sensitivity_frame, fg_color="transparent")
        slider_frame.pack(fill="x", pady=(8, 0))
        
        self.sensitivity_var = ctk.DoubleVar(value=config.get("detection_sensitivity", 0.7))
        sensitivity_slider = ctk.CTkSlider(
            slider_frame,
            from_=0.0,
            to=1.0,
            variable=self.sensitivity_var,
            number_of_steps=10,
            width=200
        )
        sensitivity_slider.pack(side="left", padx=(0, 10))
        
        self.sensitivity_label = ctk.CTkLabel(
            slider_frame,
            text=f"{self.sensitivity_var.get():.1f}",
            font=ctk.CTkFont(size=13),
            text_color=APPLE_TEXT_SECONDARY,
            width=40
        )
        self.sensitivity_label.pack(side="left")
        sensitivity_slider.configure(command=lambda v: self.sensitivity_label.configure(text=f"{v:.1f}"))
        
        # Context exchanges
        context_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        context_frame.pack(fill="x", pady=(20, 0))
        
        ctk.CTkLabel(
            context_frame,
            text="Conversation Context",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w")
        
        slider_frame2 = ctk.CTkFrame(context_frame, fg_color="transparent")
        slider_frame2.pack(fill="x", pady=(8, 0))
        
        self.context_var = ctk.IntVar(value=config.get("conversation_context_exchanges", 3))
        context_slider = ctk.CTkSlider(
            slider_frame2,
            from_=1,
            to=10,
            variable=self.context_var,
            number_of_steps=9,
            width=200
        )
        context_slider.pack(side="left", padx=(0, 10))
        
        self.context_label = ctk.CTkLabel(
            slider_frame2,
            text=str(self.context_var.get()),
            font=ctk.CTkFont(size=13),
            text_color=APPLE_TEXT_SECONDARY,
            width=40
        )
        self.context_label.pack(side="left")
        context_slider.configure(command=lambda v: self.context_label.configure(text=str(int(v))))
        
        # Section: Advanced
        section_label3 = ctk.CTkLabel(
            main_frame,
            text="Advanced",
            font=ctk.CTkFont(size=13, weight="normal"),
            text_color=APPLE_TEXT_SECONDARY
        )
        section_label3.pack(anchor="w", pady=(30, 15))
        
        # Language selection
        ctk.CTkLabel(
            main_frame,
            text="Transcription Language",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w", pady=(0, 8))
        
        self.language_var = ctk.StringVar(value=config.get("transcription_language", "auto"))
        language_menu = ctk.CTkOptionMenu(
            main_frame,
            values=["auto", "en", "fr", "es", "de", "it", "pt", "ja", "zh"],
            variable=self.language_var,
            width=200,
            height=36,
            corner_radius=8,
            fg_color=APPLE_SECONDARY,
            button_color=APPLE_SECONDARY,
            button_hover_color=APPLE_DIVIDER
        )
        language_menu.pack(anchor="w", pady=(0, 20))
        
        # Audio chunk duration
        chunk_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        chunk_frame.pack(fill="x", pady=(0, 8))
        
        ctk.CTkLabel(
            chunk_frame,
            text="Audio Chunk Duration (seconds)",
            font=ctk.CTkFont(size=14)
        ).pack(anchor="w")
        
        slider_frame3 = ctk.CTkFrame(chunk_frame, fg_color="transparent")
        slider_frame3.pack(fill="x", pady=(8, 0))
        
        self.chunk_duration_var = ctk.DoubleVar(value=config.get("audio_chunk_duration_seconds", 3.0))
        chunk_slider = ctk.CTkSlider(
            slider_frame3,
            from_=1.0,
            to=10.0,
            variable=self.chunk_duration_var,
            number_of_steps=18,
            width=200
        )
        chunk_slider.pack(side="left", padx=(0, 10))
        
        self.chunk_duration_label = ctk.CTkLabel(
            slider_frame3,
            text=f"{self.chunk_duration_var.get():.1f}s",
            font=ctk.CTkFont(size=13),
            text_color=APPLE_TEXT_SECONDARY,
            width=50
        )
        self.chunk_duration_label.pack(side="left")
        chunk_slider.configure(command=lambda v: self.chunk_duration_label.configure(text=f"{v:.1f}s"))
        
        # Additional options
        options_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=(20, 0))
        
        self.show_timestamps_var = ctk.BooleanVar(value=config.get("show_timestamps", True))
        ctk.CTkCheckBox(
            options_frame,
            text="Show timestamps in transcriptions",
            variable=self.show_timestamps_var,
            font=ctk.CTkFont(size=14),
            corner_radius=6
        ).pack(anchor="w", pady=(0, 10))
        
        self.auto_save_var = ctk.BooleanVar(value=config.get("auto_save", False))
        ctk.CTkCheckBox(
            options_frame,
            text="Auto-save sessions",
            variable=self.auto_save_var,
            font=ctk.CTkFont(size=14),
            corner_radius=6
        ).pack(anchor="w", pady=(0, 10))
        
        self.notifications_var = ctk.BooleanVar(value=config.get("show_notifications", True))
        ctk.CTkCheckBox(
            options_frame,
            text="Show notifications for questions",
            variable=self.notifications_var,
            font=ctk.CTkFont(size=14),
            corner_radius=6
        ).pack(anchor="w")
        
        # Buttons
        buttons_frame = ctk.CTkFrame(self, fg_color="transparent")
        buttons_frame.pack(fill="x", padx=30, pady=(0, 30))
        
        ctk.CTkButton(
            buttons_frame,
            text="Cancel",
            command=self.destroy,
            width=120,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=APPLE_SECONDARY,
            hover_color=APPLE_DIVIDER,
            corner_radius=10
        ).pack(side="left", padx=(0, 10))
        
        ctk.CTkButton(
            buttons_frame,
            text="Save",
            command=self.save_settings,
            width=120,
            height=40,
            font=ctk.CTkFont(size=14),
            fg_color=APPLE_ACCENT,
            hover_color=APPLE_ACCENT_HOVER,
            corner_radius=10
        ).pack(side="left")
    
    def save_settings(self):
        """Save settings."""
        self.config["whisper_model"] = self.whisper_model_var.get()
        self.config["ollama_model"] = self.ollama_model_var.get()
        self.config["auto_answer"] = self.auto_answer_var.get()
        self.config["detection_sensitivity"] = self.sensitivity_var.get()
        self.config["conversation_context_exchanges"] = self.context_var.get()
        self.config["transcription_language"] = self.language_var.get()
        self.config["audio_chunk_duration_seconds"] = self.chunk_duration_var.get()
        self.config["show_timestamps"] = self.show_timestamps_var.get()
        self.config["auto_save"] = self.auto_save_var.get()
        self.config["show_notifications"] = self.notifications_var.get()
        
        self.callback(self.config)
        self.destroy()


if __name__ == "__main__":
    import traceback
    try:
        app = TranscriptionApp()
    app.mainloop()
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Application crashed: {e}")
        logger.error(traceback.format_exc())
        # Try to show error in a message box if possible
        try:
            import tkinter.messagebox as msgbox
            root = tk.Tk()
            root.withdraw()
            msgbox.showerror(
                "Application Error",
                f"The application encountered an error:\n\n{type(e).__name__}: {e}\n\n"
                "Check the console for full details."
            )
            root.destroy()
        except:
            pass
        sys.exit(1)

