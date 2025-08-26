# backend/utils/tools/resume_generation.py  (aka tools/rendercv_tools.py)

import base64
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from typing import Optional, Tuple, Dict, Any

import requests  # for remote worker calls
import yaml
from agents import function_tool

DEFAULT_MAX_LOG_CHARS = 4000


# ---------- small helpers ----------

def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")


def _choose_out_root(out_root: Optional[str]) -> str:
    """
    Prefer explicit arg, then env var, else a project subdir. Fallback: /tmp.
    """
    if out_root:
        return out_root

    env_dir = os.getenv("RESUME_OUT_DIR")
    if env_dir:
        return env_dir

    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    default_dir = os.path.join(project_root, "generated_resumes")
    try:
        os.makedirs(default_dir, exist_ok=True)
        # writability check
        test_file = os.path.join(default_dir, ".writetest")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_file)
        return default_dir
    except Exception:
        return "/tmp/generated_resumes"


def _parse_name_from_yaml(yaml_str: str) -> str:
    """
    Extract a nice candidate name for the PDF filename from RenderCV YAML.
    """
    try:
        data = yaml.safe_load(yaml_str)
    except Exception:
        return "Resume"

    if isinstance(data, dict):
        cv_block = data.get("cv")
        if isinstance(cv_block, dict):
            name = cv_block.get("name")
            if isinstance(name, str) and name.strip():
                return name
    return "Resume"


def _make_run_dir(out_root: str, name: str) -> str:
    ts = time.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(out_root, f"{_slug(name)}_{ts}")
    os.makedirs(run_dir, exist_ok=True)
    return os.path.abspath(run_dir)


def _save_yaml(yaml_str: str, run_dir: str, persist_yaml: bool) -> Tuple[str, bool]:
    """
    Save YAML either inside run_dir or to a NamedTemporaryFile.
    Returns (yaml_path, should_cleanup).
    """
    if persist_yaml:
        yaml_path = os.path.join(run_dir, "resume.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
        return os.path.abspath(yaml_path), False

    tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
    tmp.write(yaml_str.encode("utf-8"))
    tmp.flush()
    tmp.close()
    return os.path.abspath(tmp.name), True


def _find_pdf(run_dir: str, expected_filename: str) -> Tuple[Optional[str], str]:
    """
    Look for the produced PDF. Prefer the conventional filename, else any .pdf in run_dir.
    Returns (pdf_path, final_filename).
    """
    candidate = os.path.join(run_dir, expected_filename)
    if os.path.exists(candidate):
        return candidate, expected_filename

    try:
        for root, _dirs, files in os.walk(run_dir):
            for f in files:
                if f.lower().endswith(".pdf"):
                    return os.path.join(root, f), os.path.basename(f)
    except Exception:
        pass
    return None, expected_filename


def _truncate(s: str, max_chars: int) -> str:
    s = (s or "").strip()
    if max_chars and len(s) > max_chars:
        return s[:max_chars] + "\n...[truncated]"
    return s


# ---------- rendering strategies ----------

def _render_via_worker(
    yaml_str: str,
    expected_filename: str,
    include_pdf_b64: bool,
    timeout_s: int = 120,
) -> Tuple[Optional[str], str, str, int, Optional[str]]:
    """
    Call the Render worker if configured.
    Returns (pdf_b64, stdout, stderr, returncode, url).
    - pdf_b64: base64 content if worker returned it
    - url: direct URL if worker returned it
    """
    worker_url = os.getenv("RENDER_WORKER_URL")
    worker_auth = os.getenv("RENDER_WORKER_AUTH")
    headers = {"Authorization": f"Bearer {worker_auth}"} if worker_auth else {}

    if not worker_url:
        return None, "", "Remote render attempted without RENDER_WORKER_URL", 1, None

    try:
        # Ensure the worker URL includes the /render endpoint
        if not worker_url.endswith('/render'):
            worker_url = worker_url.rstrip('/') + '/render'

        print(f"[DEBUG] Calling rendercv worker at: {worker_url}")
        resp = requests.post(
            worker_url,
            json={
                "yaml": yaml_str,
                "include_pdf_b64": bool(include_pdf_b64),
                "filename": expected_filename,
            },
            headers=headers,
            timeout=timeout_s,
        )
        resp.raise_for_status()
        data = resp.json() or {}
        # The worker may echo back a (possibly different) filename
        filename = data.get("filename") or expected_filename
        pdf_b64 = data.get("pdf_b64")
        url = data.get("url")
        if not (pdf_b64 or url):
            return None, "", "Worker returned neither url nor pdf_b64", 1, None
        return pdf_b64, "", "", 0, url
    except Exception as e:
        return None, "", f"Remote render error: {e}", 1, None


def _render_locally(
    yaml_path: str,
    run_dir: str,
) -> Tuple[int, str, str]:
    """
    Run 'python -m rendercv render <yaml> -o <run_dir>' locally.
    """
    proc = subprocess.run(
        [sys.executable, "-m", "rendercv", "render", yaml_path, "-o", run_dir],
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout, proc.stderr


def _maybe_b64(path: Optional[str], do_b64: bool) -> str:
    if not (do_b64 and path and os.path.exists(path)):
        return ""
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def _should_use_remote() -> bool:
    """
    Decide whether to delegate to the worker:
    - If running on Vercel (env var present) and RENDER_WORKER_URL is set, use remote.
    """
    vercel_env = os.getenv("VERCEL")
    worker_url = os.getenv("RENDER_WORKER_URL")
    print(f"[DEBUG] _should_use_remote: VERCEL={vercel_env}, RENDER_WORKER_URL={worker_url}")
    result = bool(vercel_env and worker_url)
    print(f"[DEBUG] _should_use_remote result: {result}")
    return result


# ---------- public tool (thin orchestrator) ----------

@function_tool
def rendercv_render(
    yaml_str: str,
    out_root: Optional[str] = None,
    persist_yaml: bool = True,
    include_pdf_b64: bool = False,
    max_log_chars: int = DEFAULT_MAX_LOG_CHARS,
) -> str:
    """
    Persist YAML (optional), run RenderCV (remote on Vercel, local in dev), and return JSON:
      - yaml_path: saved YAML file path (if persisted)
      - pdf_path: path to generated PDF (local mode)
      - pdf_b64: base64-encoded PDF (if requested or from worker)
      - url: direct URL from worker (if provided)
      - stdout, stderr, returncode
      - filename: expected PDF filename
      - output_folder: folder where the PDF was written (local mode)
    """
    # Prepare I/O
    out_root = _choose_out_root(out_root)
    os.makedirs(out_root, exist_ok=True)

    name = _parse_name_from_yaml(yaml_str)
    run_dir = _make_run_dir(out_root, name)
    yaml_path, cleanup_yaml = _save_yaml(yaml_str, run_dir, persist_yaml)

    expected_filename = f"{_slug(name)}_CV.pdf"

    pdf_path: Optional[str] = None
    pdf_b64: Optional[str] = None
    url: Optional[str] = None
    stdout_str = ""
    stderr_str = ""
    returncode = 0

    # Strategy choice
    if _should_use_remote():
        print(f"[DEBUG] Using remote worker for rendercv")
        pdf_b64, stdout_str, stderr_str, returncode, url = _render_via_worker(
            yaml_str=yaml_str,
            expected_filename=expected_filename,
            include_pdf_b64=True,  # Always request base64 in remote mode
        )
    else:
        print(f"[DEBUG] Using local rendercv")
        # Local branch
        returncode, out, err = _render_locally(yaml_path, run_dir)
        stdout_str, stderr_str = out, err

        if returncode == 0:
            # Find the PDF we just created
            pdf_path, final_filename = _find_pdf(run_dir, expected_filename)
            expected_filename = final_filename
            # Encode only if asked
            pdf_b64 = _maybe_b64(pdf_path, do_b64=bool(include_pdf_b64))

    # Cleanup temp YAML if requested
    if cleanup_yaml:
        try:
            os.remove(yaml_path)
        except Exception:
            pass

    # Assemble payload (stable shape for your app.py)
    payload: Dict[str, Any] = {
        "yaml_path": yaml_path if (persist_yaml and os.path.exists(yaml_path)) else None,
        "pdf_path": pdf_path if (pdf_path and os.path.exists(pdf_path)) else None,
        "pdf_b64": pdf_b64 or "",
        "output_folder": run_dir,
        "filename": expected_filename,
        "stdout": _truncate(stdout_str, max_log_chars),
        "stderr": _truncate(stderr_str, max_log_chars),
        "returncode": int(returncode),
    }
    if url:
        payload["url"] = url

    return json.dumps(payload)
