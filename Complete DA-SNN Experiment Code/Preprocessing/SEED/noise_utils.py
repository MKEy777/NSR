"""Raw-EEG noise injection utilities for T3 robustness experiments.

Design notes
------------
- Input tensor shape follows the SEED slicing convention:
      ``seg_X`` has shape ``[n_seg, 4, 62, 200]`` at fs=200 Hz.
  The "4 frames of 200 samples" together form the 4 s window, so the
  contiguous single-channel time series (per session) is obtained by
  reshaping to ``[n_seg * 4 * 200]`` per channel.
- Noise strength is defined as ``NL = sigma_noise / sigma_signal``.
  ``sigma_signal`` is estimated **per channel per session** so that the
  same ``nl`` yields comparable amplitude across channels/sessions.
- No intermediate arrays are written to disk; every generator returns a
  freshly-allocated float32 tensor with the same shape as the input.
- Every generator accepts an explicit ``rng`` (``np.random.Generator``)
  so callers can seed deterministically per (subject, session, tag).
"""

from __future__ import annotations

from typing import Tuple

import numpy as np
from scipy import signal as scipy_signal


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def estimate_channel_sigma(seg_X: np.ndarray) -> np.ndarray:
    """Return per-channel std, shape ``[n_channels]``.

    ``seg_X`` is expected to have shape ``[n_seg, frames, n_channels, samples]``
    (the SEED convention: ``[N, 4, 62, 200]``).  We flatten across all axes
    except the channel axis before computing std, so the estimate reflects
    the whole session and is robust to per-segment variance.
    """
    assert seg_X.ndim == 4, f"expected 4-D seg_X, got shape {seg_X.shape}"
    # move channels to front: [C, N, F, S] -> [C, -1]
    x = np.moveaxis(seg_X, 2, 0).reshape(seg_X.shape[2], -1)
    sigma = x.std(axis=1)
    # avoid zero-std channels (very unlikely after baseline z-score)
    sigma = np.where(sigma > 1e-8, sigma, 1.0).astype(np.float32)
    return sigma


def _flatten_time(seg_X: np.ndarray) -> Tuple[np.ndarray, tuple]:
    """Reshape ``[N, F, C, S]`` -> ``[C, N*F*S]`` returning also the original shape.

    This gives every channel a contiguous session-level time series, which
    is what the drift / EMG generators need in order to be temporally
    coherent across window boundaries.
    """
    n_seg, n_frames, n_channels, n_samples = seg_X.shape
    # [N, F, C, S] -> [C, N, F, S] -> [C, N*F*S]
    t = np.moveaxis(seg_X, 2, 0).reshape(n_channels, -1)
    return t, seg_X.shape


def _unflatten_time(flat: np.ndarray, orig_shape: tuple) -> np.ndarray:
    n_seg, n_frames, n_channels, n_samples = orig_shape
    # [C, N*F*S] -> [C, N, F, S] -> [N, F, C, S]
    out = flat.reshape(n_channels, n_seg, n_frames, n_samples)
    return np.moveaxis(out, 0, 2).astype(np.float32)


# ---------------------------------------------------------------------------
# Gaussian white noise
# ---------------------------------------------------------------------------

def make_gaussian(seg_X: np.ndarray, sigma_ch: np.ndarray, nl: float,
                  rng: np.random.Generator) -> np.ndarray:
    """Additive white Gaussian noise with std ``nl * sigma_ch`` per channel."""
    scale = (nl * sigma_ch).astype(np.float32)  # [C]
    noise = rng.standard_normal(size=seg_X.shape).astype(np.float32)
    # broadcast scale over [N, F, C, S] via axis=2
    noise *= scale[None, None, :, None]
    return (seg_X + noise).astype(np.float32)


# ---------------------------------------------------------------------------
# Low-frequency drift (motion / impedance)
# ---------------------------------------------------------------------------

def make_drift(seg_X: np.ndarray, sigma_ch: np.ndarray, nl: float,
               rng: np.random.Generator, fs: int = 200,
               cutoff: float = 0.5) -> np.ndarray:
    """1st-order Butterworth low-pass filtered white noise, per channel.

    The drift trace is generated at the *session* time scale (concatenation of
    all windows) and then re-split into windows so that the low-frequency
    component stays continuous across window boundaries.
    """
    flat, orig_shape = _flatten_time(seg_X)  # [C, T]
    n_channels, T = flat.shape

    b, a = scipy_signal.butter(1, cutoff / (fs / 2.0), btype='low')

    drift = rng.standard_normal(size=(n_channels, T)).astype(np.float32)
    drift = scipy_signal.filtfilt(b, a, drift, axis=1).astype(np.float32)

    # Normalize each channel's drift trace to unit std, then scale to nl*sigma_ch.
    std_est = drift.std(axis=1, keepdims=True)
    std_est = np.where(std_est > 1e-8, std_est, 1.0)
    drift = drift / std_est * (nl * sigma_ch)[:, None]

    noisy = flat + drift
    return _unflatten_time(noisy, orig_shape)


# ---------------------------------------------------------------------------
# High-frequency transient bursts (EMG-like)
# ---------------------------------------------------------------------------

def make_emg(seg_X: np.ndarray, sigma_ch: np.ndarray, nl: float,
             rng: np.random.Generator, fs: int = 200,
             rate: float = 0.5,
             burst_ms: Tuple[float, float] = (20.0, 50.0),
             carrier_hz: Tuple[float, float] = (60.0, 90.0)) -> np.ndarray:
    """Poisson-triggered high-frequency bursts, per channel.

    - Event times: Poisson process with average ``rate`` events / second along
      the *session* time axis.
    - Each burst: Gaussian envelope with FWHM sampled uniformly in
      ``burst_ms`` (converted to samples) multiplied by a sine carrier whose
      frequency is uniformly sampled from ``carrier_hz``.
    - Bursts are summed into a per-channel session-length trace which is then
      RMS-normalized to ``nl * sigma_ch`` so that the overall energy matches
      the NL definition (identical semantic to the other two noise types).
    """
    flat, orig_shape = _flatten_time(seg_X)  # [C, T]
    n_channels, T = flat.shape
    if T <= 0:
        return seg_X.astype(np.float32)

    duration_s = T / fs
    lam = max(rate * duration_s, 0.0)

    # Precompute a time index array (samples).
    t_axis = np.arange(T, dtype=np.float32)

    burst_trace = np.zeros((n_channels, T), dtype=np.float32)

    for ch in range(n_channels):
        n_events = int(rng.poisson(lam=lam))
        if n_events == 0:
            continue
        event_times = rng.uniform(0.0, duration_s, size=n_events)  # seconds
        widths_ms = rng.uniform(burst_ms[0], burst_ms[1], size=n_events)
        carriers = rng.uniform(carrier_hz[0], carrier_hz[1], size=n_events)
        phases = rng.uniform(0.0, 2 * np.pi, size=n_events)

        for et, w_ms, cf, ph in zip(event_times, widths_ms, carriers, phases):
            center = et * fs  # sample index (float)
            # FWHM -> Gaussian sigma
            sigma_samp = (w_ms * 1e-3 * fs) / 2.3548
            if sigma_samp < 1e-3:
                continue
            envelope = np.exp(-0.5 * ((t_axis - center) / sigma_samp) ** 2)
            carrier_wave = np.sin(2 * np.pi * cf * t_axis / fs + ph)
            burst_trace[ch] += (envelope * carrier_wave).astype(np.float32)

    # RMS-normalize each channel, then scale to nl * sigma_ch.
    rms = np.sqrt((burst_trace ** 2).mean(axis=1, keepdims=True))
    rms = np.where(rms > 1e-8, rms, 1.0)
    burst_trace = burst_trace / rms * (nl * sigma_ch)[:, None]

    noisy = flat + burst_trace
    return _unflatten_time(noisy, orig_shape)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

NOISE_MAKERS = {
    "gaussian": make_gaussian,
    "drift": make_drift,
    "emg": make_emg,
}