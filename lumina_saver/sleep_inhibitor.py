import os
import sys
import atexit
import shutil
import subprocess
from typing import List, Optional

class SleepInhibitor:
    """Cross-platform display sleep and screen timeout inhibitor.
    
    Prevents the operating system from dimming the screen, turning off the monitor
    via DPMS, or locking the session due to user inactivity while slideshow playback is active.
    
    Supports:
    - Linux: GNOME (Wayland/X11 via gnome-session-inhibit), systemd (systemd-inhibit), X11 (xset/xdg-screensaver)
    - Windows: SetThreadExecutionState (ES_CONTINUOUS | ES_DISPLAY_REQUIRED | ES_SYSTEM_REQUIRED)
    - macOS: caffeinate (-d -w <pid>)
    """

    def __init__(self, app_name: str = "LuminaSaver", reason: str = "Slideshow playback active"):
        self.app_name = app_name
        self.reason = reason
        self.is_inhibited: bool = False
        self._child_processes: List[subprocess.Popen] = []
        
        # Ensure cleanup on process exit
        atexit.register(self.release)

    def inhibit(self) -> bool:
        """Activates OS-level screen timeout and sleep inhibition."""
        if self.is_inhibited:
            return True

        success = False

        if sys.platform.startswith("win"):
            success = self._inhibit_windows()
        elif sys.platform == "darwin":
            success = self._inhibit_macos()
        elif sys.platform.startswith("linux"):
            success = self._inhibit_linux()
        else:
            print(f"[SleepInhibitor] Unsupported OS platform: {sys.platform}")

        self.is_inhibited = success
        if success:
            print(f"[SleepInhibitor] Screen timeout and display sleep disabled ({sys.platform}).")
        return success

    def release(self):
        """Releases all active screen timeout inhibitors and restores normal OS power management."""
        if not self.is_inhibited and not self._child_processes:
            return

        if sys.platform.startswith("win"):
            self._release_windows()
        
        # Terminate any spawned inhibitor child processes (Linux / macOS)
        for proc in self._child_processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception:
                pass
        self._child_processes.clear()

        # On Linux X11, re-enable DPMS if xset exists
        if sys.platform.startswith("linux") and os.environ.get("DISPLAY") and shutil.which("xset"):
            try:
                subprocess.run(["xset", "s", "on", "+dpms"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0)
            except Exception:
                pass

        self.is_inhibited = False
        print("[SleepInhibitor] Screen timeout inhibitor released. Normal display power management restored.")

    def _inhibit_windows(self) -> bool:
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ES_SYSTEM_REQUIRED = 0x00000001
            ES_DISPLAY_REQUIRED = 0x00000002
            
            res = ctypes.windll.kernel32.SetThreadExecutionState(
                ES_CONTINUOUS | ES_SYSTEM_REQUIRED | ES_DISPLAY_REQUIRED
            )
            return res != 0
        except Exception as e:
            print(f"[SleepInhibitor] Windows SetThreadExecutionState error: {e}")
            return False

    def _release_windows(self):
        try:
            import ctypes
            ES_CONTINUOUS = 0x80000000
            ctypes.windll.kernel32.SetThreadExecutionState(ES_CONTINUOUS)
        except Exception:
            pass

    def _inhibit_macos(self) -> bool:
        try:
            if shutil.which("caffeinate"):
                # Run caffeinate waiting for our PID to exit
                p = subprocess.Popen(
                    ["caffeinate", "-d", "-w", str(os.getpid())],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._child_processes.append(p)
                return True
        except Exception as e:
            print(f"[SleepInhibitor] macOS caffeinate error: {e}")
        return False

    def _inhibit_linux(self) -> bool:
        inhibited = False

        # 1. GNOME Session Inhibit (Primary for Ubuntu GNOME Wayland & X11)
        if shutil.which("gnome-session-inhibit"):
            try:
                p = subprocess.Popen(
                    [
                        "gnome-session-inhibit",
                        f"--app-id={self.app_name.lower()}",
                        f"--reason={self.reason}",
                        "--inhibit=idle",
                        "--inhibit=suspend",
                        "--inhibit-only"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._child_processes.append(p)
                inhibited = True
            except Exception as e:
                print(f"[SleepInhibitor] gnome-session-inhibit failed: {e}")

        # 2. systemd-inhibit (Works across systemd Linux distributions)
        if shutil.which("systemd-inhibit"):
            try:
                p = subprocess.Popen(
                    [
                        "systemd-inhibit",
                        "--what=idle:sleep",
                        f"--who={self.app_name}",
                        f"--why={self.reason}",
                        "sleep", "infinity"
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
                self._child_processes.append(p)
                inhibited = True
            except Exception as e:
                print(f"[SleepInhibitor] systemd-inhibit failed: {e}")

        # 3. X11 DPMS & screensaver disable fallback
        if os.environ.get("DISPLAY") and shutil.which("xset"):
            try:
                subprocess.run(["xset", "s", "off", "-dpms"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1.0)
                inhibited = True
            except Exception:
                pass

        return inhibited

    def heartbeat_ping(self):
        """Periodic keep-awake ping (e.g. called on slide transition) for legacy X11/screensaver servers."""
        if not self.is_inhibited:
            return

        if sys.platform.startswith("linux") and os.environ.get("DISPLAY"):
            if shutil.which("xdg-screensaver"):
                try:
                    subprocess.run(["xdg-screensaver", "reset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5)
                except Exception:
                    pass
            elif shutil.which("xset"):
                try:
                    subprocess.run(["xset", "s", "reset"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=0.5)
                except Exception:
                    pass
