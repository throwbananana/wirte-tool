import pyttsx3
import threading
import queue

class TTSManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(TTSManager, cls).__new__(cls)
            cls._instance._init_engine()
        return cls._instance

    def _init_engine(self):
        try:
            self.engine = pyttsx3.init()
            self.queue = queue.Queue()
            self.is_speaking = False
            self.worker_thread = None
            self._lock = threading.Lock()
        except Exception as e:
            print(f"Failed to initialize TTS engine: {e}")
            self.engine = None

    def speak(self, text, on_finish=None):
        if not self.engine:
            return
            
        self.stop() # Stop any current speech
        
        with self._lock:
            self.is_speaking = True
            
        def _run():
            try:
                self.engine.say(text)
                self.engine.runAndWait()
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                with self._lock:
                    self.is_speaking = False
                if on_finish:
                    on_finish()

        self.worker_thread = threading.Thread(target=_run, daemon=True)
        self.worker_thread.start()

    def stop(self):
        if not self.engine: return
        
        if self.is_speaking:
            try:
                self.engine.stop()
            except Exception as e:
                print(f"Error stopping TTS: {e}")
            self.is_speaking = False

    def get_voices(self):
        if not self.engine: return []
        try:
            return self.engine.getProperty('voices')
        except Exception:
            return []

    def set_voice(self, voice_id):
        if not self.engine: return
        try:
            self.engine.setProperty('voice', voice_id)
        except Exception as e:
            print(f"Error setting voice: {e}")

    def get_rate(self):
        if not self.engine: return 200
        return self.engine.getProperty('rate')

    def set_rate(self, rate):
        if not self.engine: return
        try:
            self.engine.setProperty('rate', rate)
        except Exception as e:
            print(f"Error setting rate: {e}")
