"""
Clicker Engine Module
Runs concurrent background clicking loops for MULTIPLE keys with INDEPENDENT timers,
ANTI-COLLISION SEQUENCING (configured pause if keys trigger together),
plus global hotkey listener (F6/F7).
Thread-safe and optimized for responsiveness and low CPU usage.
"""
import threading
import time
import random
import ctypes
from key_sender import send_key_background, send_key_foreground, resolve_key
from window_manager import is_window_alive, activate_window

user32 = ctypes.windll.user32

class ClickerEngine:
    def __init__(self, on_tick=None, on_state_change=None, on_hotkey_start=None, on_hotkey_stop=None, on_hotkey_toggle=None):
        self.on_tick = on_tick  # callback(clicks_count, elapsed_seconds)
        self.on_state_change = on_state_change  # callback(is_running, message)
        self.on_hotkey_start = on_hotkey_start
        self.on_hotkey_stop = on_hotkey_stop
        self.on_hotkey_toggle = on_hotkey_toggle
        
        self.is_running = False
        self._stop_event = threading.Event()
        self._threads = []
        self._stats_lock = threading.Lock()
        self._input_lock = threading.Lock()
        self._cycle_lock = threading.Lock()
        self._collision_lock = threading.Lock()
        
        # State tracking for each key card
        self._key_cycles = {}  # {card_index: {'start_time': float, 'duration': float, 'waiting_collision': bool, 'last_click_time': float}}
        self._reload_events = {}  # {card_index: threading.Event()}
        
        # Anti-collision state: prevents two different keys from pressing simultaneously
        self._last_click_time = 0.0
        self._last_key_clicked = None
        self.collision_pause_sec = 3.0  # seconds pause between colliding keys
        self._startup_turn = 0
        
        # Configuration
        self.target_hwnd = None
        self.target_title = ""
        self.keys_list = []  # list of dicts: [{'key': 'F1', 'interval_ms': 19000, 'enabled': True}, ...]
        self.jitter_enabled = True
        self.jitter_range = 25  # +/- 25ms random jitter
        self.mode = "background"  # 'background' or 'foreground'
        self.hotkey_toggle_vk = 0x75  # F6 (single key for toggle start/stop)
        self.hotkey_start_vk = 0x75  # F6 (fallback)
        self.hotkey_stop_vk = None   # None (unified single toggle key)

        # Stats
        self.clicks_count = 0
        self.start_time = 0.0

        # Global hotkey thread
        self._hotkey_running = True
        self._hotkey_thread = threading.Thread(target=self._hotkey_loop, daemon=True)
        self._hotkey_thread.start()

    def set_config(self, target_hwnd, target_title, keys_list, mode="background", jitter_enabled=True, collision_pause=3.0):
        self.target_hwnd = target_hwnd
        self.target_title = target_title
        self.keys_list = keys_list
        self.mode = mode
        self.jitter_enabled = jitter_enabled
        self.collision_pause_sec = max(0.1, float(collision_pause))

    def set_hotkey_toggle(self, vk):
        self.hotkey_toggle_vk = vk

    def set_hotkeys(self, start_vk, stop_vk=None):
        self.hotkey_toggle_vk = start_vk
        self.hotkey_start_vk = start_vk
        self.hotkey_stop_vk = stop_vk

    def start(self):
        if self.is_running:
            return
        if not self.target_hwnd or not is_window_alive(self.target_hwnd):
            if self.on_state_change:
                self.on_state_change(False, "Erro: Selecione uma janela/jogo válido antes de iniciar!")
            return

        # Filter enabled keys with valid intervals
        active_keys = [
            k for k in self.keys_list 
            if k.get('enabled', True) and k.get('key') and k.get('interval_ms', 0) >= 1
        ]

        if not active_keys:
            if self.on_state_change:
                self.on_state_change(False, "Erro: Configure pelo menos uma tecla com tempo válido!")
            return

        self.is_running = True
        self._stop_event.clear()
        self.clicks_count = 0
        self.start_time = time.time()
        self._last_click_time = 0.0
        self._last_key_clicked = None
        self._startup_turn = 0

        # On start: ALL keys start available in full YELLOW (waiting to be executed in sequence)
        with self._cycle_lock:
            self._key_cycles.clear()
            for key_cfg in active_keys:
                c_idx = key_cfg.get('card_index', 0)
                dur = max(0.005, key_cfg.get('interval_ms', 1000) / 1000.0)
                self._key_cycles[c_idx] = {
                    'start_time': self.start_time,
                    'duration': dur,
                    'waiting_collision': True,  # Starts YELLOW
                    'last_click_time': 0.0
                }

        keys_summary = ", ".join([f"{k['key']} ({k['interval_ms']}ms)" for k in active_keys[:3]])
        if len(active_keys) > 3:
            keys_summary += f" +{len(active_keys)-3}"

        if self.on_state_change:
            self.on_state_change(True, f"Executando {len(active_keys)} teclas: {keys_summary}")

        self._reload_events = {k.get('card_index', index): threading.Event() for index, k in enumerate(active_keys)}
        self._threads = []
        for index, key_cfg in enumerate(active_keys):
            t = threading.Thread(
                target=self._run_single_key_loop,
                args=(key_cfg, index),
                daemon=True,
                name=f"KeyClicker-{key_cfg['key']}-{index}"
            )
            t.start()
            self._threads.append(t)

    def trigger_card_reload(self, card_index):
        """Forces immediate reload & execution for a specific key card."""
        if self.is_running:
            ev = self._reload_events.get(card_index)
            if ev:
                ev.set()
        else:
            threading.Thread(
                target=self._manual_card_trigger,
                args=(card_index,),
                daemon=True,
                name=f"ManualReload-{card_index}"
            ).start()

    def _manual_card_trigger(self, card_index):
        """Handles manual reload click when clicker is not actively running."""
        if not self.target_hwnd or not is_window_alive(self.target_hwnd):
            if self.on_state_change:
                self.on_state_change(False, "Erro: Selecione uma janela/jogo antes de recarregar!")
            return

        key_cfg = next((k for k in self.keys_list if k.get('card_index') == card_index), None)
        if not key_cfg:
            if 0 <= card_index < len(self.keys_list):
                key_cfg = self.keys_list[card_index]
            else:
                return

        key_str = key_cfg.get('key')
        if not key_str:
            return

        base_interval_ms = max(1, int(key_cfg.get('interval_ms', 1000)))
        delay_sec = max(0.005, base_interval_ms / 1000.0)

        # Mark yellow as it enters collision wait/queue
        now = time.time()
        with self._cycle_lock:
            self._key_cycles[card_index] = {
                'start_time': now,
                'duration': 0.001,
                'waiting_collision': True,
                'last_click_time': self._last_click_time
            }

        self._execute_click_with_collision(key_str, card_index, delay_sec, force=True)

    def stop(self, reason="Parado pelo usuário"):
        if not self.is_running:
            return
        self.is_running = False
        self._stop_event.set()
        with self._cycle_lock:
            self._key_cycles.clear()
        if self.on_state_change:
            self.on_state_change(False, reason)

    def get_progress_for_all(self):
        """
        Returns a dict: {card_index: {'progress': float (0.0-1.0), 'waiting_collision': bool, 'last_click_time': float}}
        Used by GUI to smoothly animate the cooldown tube ('tubinho') under each key card:
          - Blue: reloading progress (0.0 -> 1.0)
          - Yellow: waiting for anti-collision delay (progress 1.0, waiting_collision=True)
          - Green flash: 200ms right after a click (via last_click_time)
        """
        now = time.time()
        result = {}
        with self._cycle_lock:
            if not self._key_cycles:
                return {}
            for card_idx, info in self._key_cycles.items():
                dur = info.get('duration', 1.0)
                elapsed = now - info.get('start_time', now)
                is_waiting = info.get('waiting_collision', False)
                if is_waiting:
                    prog = 1.0
                elif dur <= 0:
                    prog = 1.0
                else:
                    prog = min(1.0, max(0.0, elapsed / dur))
                result[card_idx] = {
                    'progress': prog,
                    'waiting_collision': is_waiting,
                    'last_click_time': info.get('last_click_time', 0.0)
                }
        return result

    def _execute_click_with_collision(self, key_str, card_index, base_delay_sec, force=False):
        """
        Executes a click strictly enforcing the anti-collision rule:
        If two or more keys would trigger together, a pause is enforced.
        'Primeiro clica esse, depois clica esse. Você não pode clicar os dois juntos.'
        During the anti-collision wait, waiting_collision=True (tubinho AMARELO).
        Immediately after the click, waiting_collision=False and start_time resets to now (tubinho AZUL).
        """
        if not force and (not self.is_running or self._stop_event.is_set()):
            return False

        with self._collision_lock:
            if not force and (not self.is_running or self._stop_event.is_set()):
                return False

            now = time.time()

            # Anti-collision check: if another key was clicked less than collision_pause_sec ago
            if self._last_key_clicked is not None and self._last_key_clicked != key_str:
                time_since_last = now - self._last_click_time
                wait_needed = self.collision_pause_sec - time_since_last
                if wait_needed > 0.01:
                    # Key is waiting for collision delay: turn tubinho AMARELO
                    with self._cycle_lock:
                        if card_index in self._key_cycles:
                            self._key_cycles[card_index]['waiting_collision'] = True

                    # Sleep in small slices so stopping is instantaneous
                    wake_time = now + wait_needed
                    while time.time() < wake_time and (force or (self.is_running and not self._stop_event.is_set())):
                        time.sleep(0.015)

                    if not force and (not self.is_running or self._stop_event.is_set()):
                        return False

            # Check if target window is still alive
            if not is_window_alive(self.target_hwnd):
                if not force:
                    self.stop("A janela do jogo foi fechada!")
                return False

            # Perform the physical keystroke
            if self.mode == "background":
                send_key_background(self.target_hwnd, key_str)
            else:
                with self._input_lock:
                    activate_window(self.target_hwnd)
                    time.sleep(0.015)
                    send_key_foreground(key_str)

            click_time = time.time()
            self._last_click_time = click_time
            self._last_key_clicked = key_str

            # Update key cycle: mark click time and IMMEDIATELY reset to reloading (AZUL)
            with self._cycle_lock:
                if card_index in self._key_cycles:
                    self._key_cycles[card_index]['last_click_time'] = click_time
                    self._key_cycles[card_index]['waiting_collision'] = False
                    self._key_cycles[card_index]['start_time'] = click_time
                    self._key_cycles[card_index]['duration'] = base_delay_sec

            with self._stats_lock:
                self.clicks_count += 1
                current_clicks = self.clicks_count

            if self.on_tick:
                elapsed = time.time() - self.start_time if self.start_time > 0 else 0
                self.on_tick(current_clicks, elapsed)

            return True

    def _run_single_key_loop(self, key_cfg, index):
        card_index = key_cfg.get('card_index', index)
        key_str = key_cfg['key']
        base_interval_ms = max(1, int(key_cfg['interval_ms']))
        delay_sec = max(0.005, base_interval_ms / 1000.0)
        reload_ev = self._reload_events.get(card_index)

        # 1. INITIAL SEQUENCED CAST ON START:
        # All keys start available in YELLOW.
        # They execute in strict index order (Tecla #1 first, then Tecla #2, etc.),
        # with anti-collision pause enforced between them.
        time.sleep(0.08)  # brief 80ms beat so user sees all yellow tubes on start
        while self.is_running and not self._stop_event.is_set() and self._startup_turn < index:
            if reload_ev and reload_ev.is_set():
                reload_ev.clear()
                break
            time.sleep(0.015)

        if not self.is_running or self._stop_event.is_set():
            return

        if not self._execute_click_with_collision(key_str, card_index, delay_sec):
            return

        # Advance startup turn so the next key in line can execute
        self._startup_turn = index + 1

        # 2. SUBSEQUENT CYCLES:
        # Reload (Tubinho Azul charging 0% -> 100%) -> Click (Tubinho flash verde / yellow if collision)
        while self.is_running and not self._stop_event.is_set():
            cycle_duration = delay_sec
            if self.jitter_enabled and base_interval_ms > 50:
                jitter = random.randint(-self.jitter_range, self.jitter_range)
                cycle_duration = max(0.01, (base_interval_ms + jitter) / 1000.0)

            cycle_start = time.time()
            with self._cycle_lock:
                prev_click = self._key_cycles.get(card_index, {}).get('last_click_time', 0.0)
                self._key_cycles[card_index] = {
                    'start_time': cycle_start,
                    'duration': cycle_duration,
                    'waiting_collision': False,  # AZUL!
                    'last_click_time': prev_click
                }

            # Wait while the tube charges in vibrant blue
            cycle_end = cycle_start + cycle_duration
            while time.time() < cycle_end and self.is_running and not self._stop_event.is_set():
                if reload_ev and reload_ev.is_set():
                    reload_ev.clear()
                    break
                time.sleep(0.015)

            if not self.is_running or self._stop_event.is_set():
                break

            # Reload complete (100% full): mark yellow as it enters collision wait/queue
            with self._cycle_lock:
                if card_index in self._key_cycles:
                    self._key_cycles[card_index]['waiting_collision'] = True
                    self._key_cycles[card_index]['duration'] = 0.001

            # Fire keystroke (wait in yellow ONLY if waiting collision pause)
            if not self._execute_click_with_collision(key_str, card_index, delay_sec):
                break

    def _hotkey_loop(self):
        """Watches for global single toggle hotkey across all screens/games using GetAsyncKeyState."""
        was_toggle_pressed = False
        was_stop_pressed = False

        while self._hotkey_running:
            try:
                # Unified Toggle Hotkey Check (Single button for start/stop)
                if self.hotkey_toggle_vk:
                    toggle_state = bool(user32.GetAsyncKeyState(self.hotkey_toggle_vk) & 0x8000)
                    if toggle_state and not was_toggle_pressed:
                        # Rising edge
                        if self.on_hotkey_toggle:
                            self.on_hotkey_toggle()
                        else:
                            if self.is_running:
                                self.stop("Parado via tecla de atalho")
                            else:
                                self.start()
                    was_toggle_pressed = toggle_state

                # Optional secondary stop hotkey check (if separately configured)
                if self.hotkey_stop_vk and self.hotkey_stop_vk != self.hotkey_toggle_vk:
                    stop_state = bool(user32.GetAsyncKeyState(self.hotkey_stop_vk) & 0x8000)
                    if stop_state and not was_stop_pressed:
                        if self.on_hotkey_stop:
                            self.on_hotkey_stop()
                        else:
                            self.stop("Parado via tecla de atalho")
                    was_stop_pressed = stop_state

            except Exception:
                pass
            time.sleep(0.03)

    def shutdown(self):
        self.stop()
        self._hotkey_running = False
