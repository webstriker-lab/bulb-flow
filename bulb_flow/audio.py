"""Native Windows audio capture (16kHz 16-bit mono PCM WAV) using winmm.dll.

Zero external native dependencies; provides live RMS levels for the waveform pill
and enumerates all Windows microphone input devices.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import io
import math
import struct
import threading
import time
import wave
from typing import Callable

from .constants import CHUNK_DURATION_MS, RECORDING_BITS_PER_SAMPLE, RECORDING_CHANNELS, RECORDING_SAMPLE_RATE

# Windows multimedia constants
WAVE_MAPPER = 0xFFFFFFFF
WAVE_FORMAT_PCM = 1
CALLBACK_NULL = 0x00000000
WHDR_DONE = 0x00000001


class WAVEFORMATEX(ctypes.Structure):
    _fields_ = [
        ("wFormatTag", wintypes.WORD),
        ("nChannels", wintypes.WORD),
        ("nSamplesPerSec", wintypes.DWORD),
        ("nAvgBytesPerSec", wintypes.DWORD),
        ("nBlockAlign", wintypes.WORD),
        ("wBitsPerSample", wintypes.WORD),
        ("cbSize", wintypes.WORD),
    ]


class WAVEHDR(ctypes.Structure):
    _fields_ = [
        ("lpData", ctypes.c_char_p),
        ("dwBufferLength", wintypes.DWORD),
        ("dwBytesRecorded", wintypes.DWORD),
        ("dwUser", ctypes.c_void_p),
        ("dwFlags", wintypes.DWORD),
        ("dwLoops", wintypes.DWORD),
        ("lpNext", ctypes.c_void_p),
        ("reserved", ctypes.c_void_p),
    ]


class WAVEINCAPSW(ctypes.Structure):
    _fields_ = [
        ("wMid", wintypes.WORD),
        ("wPid", wintypes.WORD),
        ("vDriverVersion", wintypes.UINT),
        ("szPname", wintypes.WCHAR * 32),
        ("dwFormats", wintypes.DWORD),
        ("wChannels", wintypes.WORD),
        ("wReserved1", wintypes.WORD),
    ]


_winmm = ctypes.windll.winmm if hasattr(ctypes, "windll") else None


def list_input_devices() -> list[tuple[int, str]]:
    """Return list of (device_id, device_name) including default (-1)."""
    devices: list[tuple[int, str]] = [(-1, "System Default Microphone")]
    if _winmm is None:
        return devices
    try:
        count = int(_winmm.waveInGetNumDevs())
        caps = WAVEINCAPSW()
        for idx in range(count):
            res = _winmm.waveInGetDevCapsW(idx, ctypes.byref(caps), ctypes.sizeof(caps))
            if res == 0:
                name = caps.szPname.strip() or f"Microphone {idx + 1}"
                devices.append((idx, name))
    except Exception:
        pass
    return devices


def play_feedback_tone(kind: str = "start") -> None:
    """Play a very subtle, short audio cue on Windows."""
    try:
        import winsound

        def _beep() -> None:
            try:
                if kind == "start":
                    winsound.Beep(660, 45)
                elif kind == "stop":
                    winsound.Beep(520, 45)
                elif kind == "done":
                    winsound.Beep(880, 55)
            except Exception:
                pass

        threading.Thread(target=_beep, daemon=True).start()
    except Exception:
        pass


def compute_rms_normalized(pcm_bytes: bytes) -> float:
    """Compute normalized 0.0..1.0 RMS energy for 16-bit signed PCM mono audio."""
    n = len(pcm_bytes) // 2
    if n <= 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", pcm_bytes[: n * 2])
    mean_sq = sum(s * s for s in samples) / n
    rms = math.sqrt(mean_sq) / 32768.0
    # Boost softly for visual responsiveness on normal speaking volumes
    return min(1.0, math.pow(rms * 5.2, 0.72))


def pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int = RECORDING_SAMPLE_RATE) -> bytes:
    """Wrap raw 16-bit mono PCM in a standard WAV container."""
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(RECORDING_CHANNELS)
        wf.setsampwidth(RECORDING_BITS_PER_SAMPLE // 8)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm_bytes)
    return buf.getvalue()


class AudioRecorder:
    """Non-blocking Windows PCM recorder capturing 16kHz mono chunks."""

    def __init__(
        self,
        device_id: int = -1,
        on_level: Callable[[float], None] | None = None,
    ):
        self.device_id = device_id
        self.on_level = on_level
        self._recording = False
        self._thread: threading.Thread | None = None
        self._chunks: list[bytes] = []
        self._start_time: float = 0.0
        self._lock = threading.Lock()
        self.last_error: str = ""

    @property
    def is_recording(self) -> bool:
        return self._recording

    def start(self, device_id: int | None = None) -> bool:
        with self._lock:
            if self._recording:
                return True
            if device_id is not None:
                self.device_id = device_id
            self._chunks = []
            self.last_error = ""
            self._recording = True
            self._start_time = time.monotonic()
            self._thread = threading.Thread(target=self._record_loop, daemon=True)
            self._thread.start()
            return True

    def stop(self) -> tuple[bytes, float]:
        """Stop capture and return (wav_bytes, duration_seconds)."""
        with self._lock:
            if not self._recording:
                return b"", 0.0
            self._recording = False
            thread = self._thread

        if thread and thread.is_alive():
            thread.join(timeout=1.5)

        duration = max(0.0, time.monotonic() - self._start_time)
        pcm = b"".join(self._chunks)
        if not pcm:
            return b"", duration
        return pcm_to_wav_bytes(pcm, RECORDING_SAMPLE_RATE), duration

    def _record_loop(self) -> None:
        if _winmm is None:
            self.last_error = "Windows audio API unavailable on this platform."
            self._recording = False
            return

        h_wave_in = ctypes.c_void_p()
        wfx = WAVEFORMATEX()
        wfx.wFormatTag = WAVE_FORMAT_PCM
        wfx.nChannels = RECORDING_CHANNELS
        wfx.nSamplesPerSec = RECORDING_SAMPLE_RATE
        wfx.wBitsPerSample = RECORDING_BITS_PER_SAMPLE
        wfx.nBlockAlign = (wfx.nChannels * wfx.wBitsPerSample) // 8
        wfx.nAvgBytesPerSec = wfx.nSamplesPerSec * wfx.nBlockAlign
        wfx.cbSize = 0

        dev = WAVE_MAPPER if self.device_id < 0 else self.device_id
        res = _winmm.waveInOpen(
            ctypes.byref(h_wave_in),
            ctypes.c_uint(dev),
            ctypes.byref(wfx),
            0,
            0,
            CALLBACK_NULL,
        )
        if res != 0:
            self.last_error = f"Could not open microphone (winmm error {res})."
            self._recording = False
            return

        # 40ms chunk size matching Wispr Flow CHUNK_DURATION_MS
        bytes_per_chunk = int(RECORDING_SAMPLE_RATE * (CHUNK_DURATION_MS / 1000.0)) * wfx.nBlockAlign
        num_buffers = 8
        buffers = [ctypes.create_string_buffer(bytes_per_chunk) for _ in range(num_buffers)]
        headers = []

        try:
            for buf in buffers:
                hdr = WAVEHDR()
                hdr.lpData = ctypes.cast(buf, ctypes.c_char_p)
                hdr.dwBufferLength = bytes_per_chunk
                hdr.dwFlags = 0
                _winmm.waveInPrepareHeader(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
                _winmm.waveInAddBuffer(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
                headers.append((hdr, buf))

            _winmm.waveInStart(h_wave_in)

            while self._recording:
                any_done = False
                for hdr, buf in headers:
                    if hdr.dwFlags & WHDR_DONE:
                        any_done = True
                        recorded = int(hdr.dwBytesRecorded)
                        if recorded > 0:
                            data = buf.raw[:recorded]
                            self._chunks.append(data)
                            if self.on_level:
                                try:
                                    self.on_level(compute_rms_normalized(data))
                                except Exception:
                                    pass
                        if self._recording:
                            hdr.dwFlags &= ~WHDR_DONE
                            hdr.dwBytesRecorded = 0
                            _winmm.waveInAddBuffer(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
                if not any_done:
                    time.sleep(0.012)
        finally:
            try:
                _winmm.waveInStop(h_wave_in)
                _winmm.waveInReset(h_wave_in)
                for hdr, buf in headers:
                    if hdr.dwBytesRecorded > 0 and (hdr.dwFlags & WHDR_DONE):
                        # Capture final partial chunk
                        pass
                    _winmm.waveInUnprepareHeader(h_wave_in, ctypes.byref(hdr), ctypes.sizeof(hdr))
                _winmm.waveInClose(h_wave_in)
            except Exception:
                pass
