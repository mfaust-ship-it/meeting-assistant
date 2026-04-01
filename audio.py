"""
Cross-platform audio capture.

Provides a unified streaming interface for capturing audio from microphone
or system speakers (loopback).

Backends:
- Linux loopback: pw-record targeting a PipeWire monitor source
- Linux mic / macOS / Windows: sounddevice (PortAudio)
- Windows loopback: sounddevice with WASAPI loopback
- macOS loopback: sounddevice with virtual audio device (BlackHole, etc.)
"""

import platform
import queue
import shutil
import subprocess
import sys
import threading
from abc import ABC, abstractmethod
from pathlib import Path

import numpy as np


class AudioStream(ABC):
    """Base class for audio streams. Delivers float32 numpy arrays."""

    @abstractmethod
    def start(self):
        """Start capturing audio."""

    @abstractmethod
    def stop(self):
        """Stop capturing audio."""

    @abstractmethod
    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        """Read the next audio chunk. Returns None on timeout."""

    @classmethod
    def open_loopback(cls, sample_rate: int = 16000, channels: int = 1,
                      chunk_ms: int = 500) -> "AudioStream":
        """Open a stream capturing system audio (speakers/loopback)."""
        system = platform.system()
        if system == "Linux":
            return PipeWireLoopbackStream(sample_rate, channels, chunk_ms)
        elif system == "Darwin":
            return SounddeviceStream.for_loopback(sample_rate, channels, chunk_ms)
        elif system == "Windows":
            return SounddeviceStream.for_wasapi_loopback(sample_rate, channels, chunk_ms)
        else:
            raise RuntimeError(f"Unsupported platform: {system}")

    @classmethod
    def open_microphone(cls, sample_rate: int = 16000, channels: int = 1,
                        chunk_ms: int = 500) -> "AudioStream":
        """Open a stream capturing from the default microphone."""
        return SounddeviceStream.for_microphone(sample_rate, channels, chunk_ms)


# ---------------------------------------------------------------------------
# Linux: pw-record based loopback capture
# ---------------------------------------------------------------------------

class PipeWireLoopbackStream(AudioStream):
    """Captures system audio on Linux via pw-record targeting a monitor source."""

    def __init__(self, sample_rate: int, channels: int, chunk_ms: int):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_samples = int(sample_rate * chunk_ms / 1000)
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=100)
        self._process = None
        self._reader_thread = None
        self._running = False

        if not shutil.which("pw-record"):
            raise RuntimeError(
                "pw-record not found. Install PipeWire: "
                "sudo apt install pipewire pipewire-pulse"
            )

        self._monitor_source = self._find_monitor_source()
        print(f"Loopback device: {self._monitor_source} (pw-record)")

    @staticmethod
    def _find_monitor_source() -> str:
        """Find a PipeWire/PulseAudio monitor source for loopback capture."""
        # Try pw-cli first
        try:
            result = subprocess.run(
                ["pw-cli", "list-objects", "Node"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "alsa_output" in line and "analog-stereo" in line:
                    node_name = line.split('"')[1]
                    return f"{node_name}.monitor"
        except Exception:
            pass

        # Try pactl (PulseAudio / PipeWire-Pulse)
        try:
            result = subprocess.run(
                ["pactl", "list", "short", "sources"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if ".monitor" in line:
                    # Format: ID  name  driver  format  state
                    parts = line.split("\t")
                    if len(parts) >= 2:
                        return parts[1]
        except Exception:
            pass

        # Hardcoded fallback
        return "alsa_output.pci-0000_c1_00.6.analog-stereo.monitor"

    def start(self):
        cmd = [
            "pw-record",
            "--rate", str(self.sample_rate),
            "--channels", str(self.channels),
            "--format", "s16",
            "--target", self._monitor_source,
            "-",  # write to stdout
        ]
        self._process = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_loop, daemon=True)
        self._reader_thread.start()

    def _read_loop(self):
        """Read raw PCM from pw-record stdout and enqueue as float32 chunks."""
        bytes_per_chunk = self.chunk_samples * 2  # 16-bit = 2 bytes per sample
        while self._running and self._process and self._process.poll() is None:
            raw = self._process.stdout.read(bytes_per_chunk)
            if not raw:
                break
            samples = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
            try:
                self._queue.put_nowait(samples)
            except queue.Full:
                pass

    def stop(self):
        self._running = False
        if self._process:
            self._process.terminate()
            try:
                self._process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None


# ---------------------------------------------------------------------------
# sounddevice-based streams (mic on all platforms, loopback on macOS/Windows)
# ---------------------------------------------------------------------------

class SounddeviceStream(AudioStream):
    """Streams audio via sounddevice (PortAudio)."""

    def __init__(self, device_idx, sample_rate: int, channels: int,
                 chunk_ms: int, extra_settings=None):
        import sounddevice as sd

        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_samples = int(sample_rate * chunk_ms / 1000)
        self._queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=100)

        self._stream = sd.InputStream(
            device=device_idx,
            samplerate=sample_rate,
            channels=channels,
            dtype="float32",
            blocksize=self.chunk_samples,
            callback=self._callback,
            extra_settings=extra_settings,
        )

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"Audio stream status: {status}", file=sys.stderr)
        audio = indata[:, 0].copy() if indata.shape[1] > 0 else indata.flatten().copy()
        try:
            self._queue.put_nowait(audio)
        except queue.Full:
            pass

    def start(self):
        self._stream.start()

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def read(self, timeout: float = 1.0) -> np.ndarray | None:
        try:
            return self._queue.get(timeout=timeout)
        except queue.Empty:
            return None

    @classmethod
    def for_microphone(cls, sample_rate: int, channels: int,
                       chunk_ms: int) -> "SounddeviceStream":
        """Open the default microphone."""
        import sounddevice as sd
        idx = sd.default.device[0]
        dev = sd.query_devices(idx)
        print(f"Microphone device: {dev['name']}")
        return cls(idx, sample_rate, channels, chunk_ms)

    @classmethod
    def for_loopback(cls, sample_rate: int, channels: int,
                     chunk_ms: int) -> "SounddeviceStream":
        """Open a virtual loopback device (macOS: BlackHole/Soundflower)."""
        import sounddevice as sd
        virtual_names = ["blackhole", "soundflower", "loopback"]
        devices = sd.query_devices()
        for i, dev in enumerate(devices):
            name_lower = dev["name"].lower()
            if dev["max_input_channels"] > 0:
                for vd in virtual_names:
                    if vd in name_lower:
                        print(f"Loopback device: {dev['name']}")
                        return cls(i, sample_rate, channels, chunk_ms)
        raise RuntimeError(
            "No loopback audio device found. On macOS, install BlackHole "
            "(https://github.com/ExistentialAudio/BlackHole) and set it "
            "as your system output."
        )

    @classmethod
    def for_wasapi_loopback(cls, sample_rate: int, channels: int,
                            chunk_ms: int) -> "SounddeviceStream":
        """Open WASAPI loopback on Windows (captures default output)."""
        import sounddevice as sd
        idx = sd.default.device[1]  # default output
        dev = sd.query_devices(idx)
        print(f"Loopback device: {dev['name']} (WASAPI loopback)")
        extra = sd.WasapiSettings(loopback=True)
        return cls(idx, sample_rate, channels, chunk_ms, extra_settings=extra)


def list_devices():
    """Print all available audio devices (useful for debugging)."""
    import sounddevice as sd
    print(sd.query_devices())
