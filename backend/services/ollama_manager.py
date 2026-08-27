import os, sys, shutil, subprocess, time, urllib.request, urllib.error, json
from typing import Optional, List

_ollama_process: Optional[subprocess.Popen] = None

def find_ollama_executable() -> str:
    """Find absolute path to ollama.exe on Windows."""
    path = shutil.which("ollama") or shutil.which("ollama.exe")
    if path and os.path.exists(path):
        return path

    user_appdata = os.environ.get("LOCALAPPDATA", "")
    if user_appdata:
        standard_path = os.path.join(user_appdata, "Programs", "Ollama", "ollama.exe")
        if os.path.exists(standard_path):
            return standard_path

    fallback_path = r"C:\Users\siddh\AppData\Local\Programs\Ollama\ollama.exe"
    if os.path.exists(fallback_path):
        return fallback_path

    return "ollama"


def is_ollama_responding() -> bool:
    """Check if Ollama HTTP API endpoint on port 11434 is active and responding."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=1.5) as resp:
            return resp.status == 200
    except Exception:
        return False


def ensure_ollama_running(timeout_seconds: float = 30.0) -> bool:
    """
    Ensures Ollama service is running on http://127.0.0.1:11434.
    If already running, reuses existing instance.
    If not running, locates ollama.exe and launches 'ollama serve' in background.
    Polls http://127.0.0.1:11434/api/tags until active before returning.
    """
    global _ollama_process

    # 1. Check if Ollama is already active
    if is_ollama_responding():
        print("[OLLAMA] Existing Ollama service detected and active on http://127.0.0.1:11434.")
        verify_required_models()
        return True

    # 2. Service not running -> Locate executable & launch background server
    exe_path = find_ollama_executable()
    print(f"[OLLAMA] Ollama service not detected on port 11434. Auto-launching '{exe_path} serve'...")

    try:
        env = os.environ.copy()
        # Set stable CPU library env var to prevent CUDA driver kernel mismatch errors (HTTP 500)
        env["OLLAMA_LLM_LIBRARY"] = "cpu_avx2"
        env["OLLAMA_NUM_PARALLEL"] = "1"
        env["OLLAMA_MAX_LOADED_MODELS"] = "1"

        creation_flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        _ollama_process = subprocess.Popen(
            [exe_path, "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            env=env,
            creationflags=creation_flags
        )

        # 3. Poll http://127.0.0.1:11434/api/tags until server responds
        start_time = time.time()
        while time.time() - start_time < timeout_seconds:
            time.sleep(0.5)
            if is_ollama_responding():
                elapsed = time.time() - start_time
                print(f"[OLLAMA] Ollama background server started and verified active in {elapsed:.2f}s!")
                verify_required_models()
                return True

        print(f"[OLLAMA WARNING] Launched Ollama process '{exe_path}', but HTTP endpoint did not respond within {timeout_seconds}s.")
        return False
    except Exception as exc:
        print(f"[OLLAMA WARNING] Failed to launch Ollama background server: {str(exc)}")
        return False


def verify_required_models() -> List[str]:
    """Inspects installed models on Ollama server and logs availability of qwen3:8b and deepseek-r1:7b."""
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/tags")
        with urllib.request.urlopen(req, timeout=3.0) as resp:
            tags = json.loads(resp.read().decode("utf-8"))
            installed_models = [m.get("name") for m in tags.get("models", [])]
            print(f"[OLLAMA] Installed models: {installed_models}")
            has_qwen = any("qwen3:8b" in m for m in installed_models)
            has_deepseek = any("deepseek-r1:7b" in m for m in installed_models)
            print(f"[OLLAMA] Required model qwen3:8b installed: {has_qwen}")
            print(f"[OLLAMA] Required model deepseek-r1:7b installed: {has_deepseek}")
            return installed_models
    except Exception as exc:
        print(f"[OLLAMA WARNING] Could not query model list: {str(exc)}")
        return []
