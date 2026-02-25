import json
import os
import random
import threading
from urllib.parse import urlparse, unquote

ACE_ROOT_NOTES = ["C", "C#", "Db", "D", "D#", "Eb", "E", "F", "F#", "Gb", "G", "G#", "Ab", "A", "A#", "Bb", "B"]
ACE_KEYSCALE_OPTIONS = [f"{root} {quality}" for quality in ["major", "minor"] for root in ACE_ROOT_NOTES]
ACE_TIMESIGNATURE_OPTIONS = ["2", "3", "4", "6"]
ACE_LANGUAGE_OPTIONS = ["en", "ja", "zh", "es", "de", "fr", "pt", "ru", "it", "nl", "pl", "tr", "vi", "cs", "fa", "id", "ko", "uk", "hu", "ar", "sv", "ro", "el"]


class ACEDatasetPromptLoader:
    _cache_lock = threading.Lock()
    _dataset_cache = {}
    _sequence_indices = {}

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "dataset_json_path": ("STRING", {"default": "", "multiline": False}),
                "mode": (["random_fields", "random_track", "sequential_cycle", "specific_track"],),
            },
            "optional": {
                "seed": ("INT", {"default": 0, "min": 0, "max": 0xffffffffffffffff, "control_after_generate": True}),
                "track_number": ("INT", {"default": 1, "min": 1, "max": 2147483647}),
            },
        }

    RETURN_TYPES = ("STRING", "STRING", "INT", ACE_KEYSCALE_OPTIONS, ACE_TIMESIGNATURE_OPTIONS, "FLOAT", ACE_LANGUAGE_OPTIONS, "STRING", "STRING")
    RETURN_NAMES = ("caption", "lyrics", "bpm", "keyscale", "timesignature", "duration", "language", "filename", "custom_tag")
    FUNCTION = "load_dataset_values"
    CATEGORY = "ACE"

    @classmethod
    def IS_CHANGED(cls, dataset_json_path, mode, seed=None, track_number=None):
        # sequential mode should advance on every queue even with fixed seed
        if mode == "sequential_cycle":
            return float("NaN")
        safe_seed = 0 if seed is None else int(seed)
        safe_track = 1 if track_number is None else int(track_number)
        return (str(dataset_json_path), str(mode), safe_seed, safe_track)

    def load_dataset_values(self, dataset_json_path, mode, seed=0, track_number=1):
        try:
            samples = self._load_samples(dataset_json_path)
            if not samples:
                raise ValueError("No samples found in dataset JSON")

            if seed is None:
                seed = 0
            if track_number is None:
                track_number = 1

            rng = self._make_rng(seed)

            if mode == "random_fields":
                return self._select_random_fields(samples, rng)
            if mode == "random_track":
                return self._sample_to_outputs(rng.choice(samples))
            if mode == "sequential_cycle":
                return self._select_sequential(samples, dataset_json_path)
            if mode == "specific_track":
                return self._select_specific_track(samples, track_number)

            raise ValueError(f"Unknown mode: {mode}")
        except Exception as e:
            return (f"Error: {e}", "", 0, ACE_KEYSCALE_OPTIONS[0], ACE_TIMESIGNATURE_OPTIONS[0], 0.0, ACE_LANGUAGE_OPTIONS[0], "", "")

    @classmethod
    def _normalize_path(cls, raw_path):
        if raw_path is None:
            raise ValueError("dataset_json_path is empty")

        path = str(raw_path).strip().strip('"').strip("'")
        if not path:
            raise ValueError("dataset_json_path is empty")

        parsed = urlparse(path)
        if parsed.scheme == "file":
            path = unquote(parsed.path or "")
            if path.startswith("/") and len(path) > 2 and path[2] == ":":
                path = path[1:]

        path = os.path.expandvars(os.path.expanduser(path))
        return os.path.normpath(path)

    @classmethod
    def _load_samples(cls, dataset_json_path):
        path = cls._normalize_path(dataset_json_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"JSON file not found: {path}")

        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = None

        with cls._cache_lock:
            cached = cls._dataset_cache.get(path)
            if cached and cached.get("mtime") == mtime:
                return cached["samples"]

        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)

        samples = data.get("samples")
        if not isinstance(samples, list):
            raise ValueError("Dataset JSON must contain a 'samples' list")

        with cls._cache_lock:
            cls._dataset_cache[path] = {"mtime": mtime, "samples": samples}

        return samples

    @staticmethod
    def _safe_int(value):
        try:
            return int(round(float(value)))
        except Exception:
            return 0

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except Exception:
            return 0.0

    @classmethod
    def _make_rng(cls, seed):
        # ComfyUI seed widgets commonly use unsigned 64-bit range.
        normalized_seed = cls._safe_int(seed) & 0xFFFFFFFFFFFFFFFF
        return random.Random(normalized_seed)

    @staticmethod
    def _pick_lyrics(sample):
        formatted = sample.get("formatted_lyrics")
        if isinstance(formatted, str) and formatted.strip():
            return formatted
        lyrics = sample.get("lyrics")
        if isinstance(lyrics, str):
            return lyrics
        return ""

    @classmethod
    def _sample_to_outputs(cls, sample):
        keyscale = str(sample.get("keyscale", "") or "")
        timesignature = str(sample.get("timesignature", "") or "")
        language = str(sample.get("language", "") or "")

        return (
            str(sample.get("caption", "") or ""),
            cls._pick_lyrics(sample),
            cls._safe_int(sample.get("bpm", 0)),
            keyscale if keyscale in ACE_KEYSCALE_OPTIONS else (ACE_KEYSCALE_OPTIONS[0] if not keyscale else keyscale),
            timesignature if timesignature in ACE_TIMESIGNATURE_OPTIONS else (ACE_TIMESIGNATURE_OPTIONS[0] if not timesignature else timesignature),
            cls._safe_float(sample.get("duration", 0.0)),
            language if language in ACE_LANGUAGE_OPTIONS else (ACE_LANGUAGE_OPTIONS[0] if not language else language),
            str(sample.get("filename", "") or ""),
            str(sample.get("custom_tag", "") or ""),
        )

    @classmethod
    def _select_random_fields(cls, samples, rng):
        caption_sample = rng.choice(samples)
        lyrics_sample = rng.choice(samples)
        bpm_sample = rng.choice(samples)
        keyscale_sample = rng.choice(samples)
        timesig_sample = rng.choice(samples)
        duration_sample = rng.choice(samples)
        language_sample = rng.choice(samples)
        filename_sample = rng.choice(samples)
        custom_tag_sample = rng.choice(samples)

        return (
            str(caption_sample.get("caption", "") or ""),
            cls._pick_lyrics(lyrics_sample),
            cls._safe_int(bpm_sample.get("bpm", 0)),
            str(keyscale_sample.get("keyscale", "") or ""),
            str(timesig_sample.get("timesignature", "") or ""),
            cls._safe_float(duration_sample.get("duration", 0.0)),
            str(language_sample.get("language", "") or ""),
            str(filename_sample.get("filename", "") or ""),
            str(custom_tag_sample.get("custom_tag", "") or ""),
        )

    @classmethod
    def _select_specific_track(cls, samples, track_number):
        idx = cls._safe_int(track_number) - 1
        if idx < 0 or idx >= len(samples):
            raise ValueError(f"track_number out of range: {track_number}. Valid range: 1..{len(samples)}")
        return cls._sample_to_outputs(samples[idx])

    @classmethod
    def _select_sequential(cls, samples, dataset_json_path):
        path = cls._normalize_path(dataset_json_path)
        with cls._cache_lock:
            idx = cls._sequence_indices.get(path, 0)
            cls._sequence_indices[path] = (idx + 1) % len(samples)

        return cls._sample_to_outputs(samples[idx % len(samples)])


NODE_CLASS_MAPPINGS = {
    "ACEDatasetPromptLoader": ACEDatasetPromptLoader,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "ACEDatasetPromptLoader": "ACE Dataset Prompt Loader",
}
