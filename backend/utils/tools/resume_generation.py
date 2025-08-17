# tools/rendercv_tools.py
import base64, json, os, re, subprocess, tempfile, time, yaml, sys
from typing import Optional
from agents import function_tool

def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")

def _choose_out_root(out_root: Optional[str]) -> str:
    # Prefer explicit arg, then env var, else writable default
    if out_root:
        return out_root
    env_dir = os.getenv("RESUME_OUT_DIR")
    if env_dir:
        return env_dir
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../"))
    default_dir = os.path.join(project_root, "generated_resumes")
    try:
        os.makedirs(default_dir, exist_ok=True)
        test_file = os.path.join(default_dir, ".writetest")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(test_file)
        return default_dir
    except Exception:
        return "/tmp/generated_resumes"


@function_tool
def rendercv_render(
	yaml_str: str,
	out_root: Optional[str] = None,
	persist_yaml: bool = True,
	include_pdf_b64: bool = False,
	max_log_chars: int = 4000,
) -> str:
    """
    Persist YAML (optional), run `rendercv render`, and return JSON:
      - yaml_path: saved YAML file path (if persisted)
      - pdf_path: path to generated PDF (if success)
      - pdf_b64: base64-encoded PDF (if success)
      - stdout, stderr, returncode
      - filename: expected PDF filename
      - output_folder: folder where the PDF was written
    """
    # Resolve writable output directory
    out_root = _choose_out_root(out_root)

    os.makedirs(out_root, exist_ok=True)

    # Name & folder
    loaded_yaml = None
    try:
        loaded_yaml = yaml.safe_load(yaml_str)


    except Exception:
        loaded_yaml = None
       

    name = "Resume"
    if isinstance(loaded_yaml, dict):
        cv_block = loaded_yaml.get("cv")
        if isinstance(cv_block, dict):
            candidate_name = cv_block.get("name")
            if isinstance(candidate_name, str) and candidate_name.strip():
                name = candidate_name
    ts = time.strftime("%Y%m%d_%H%M%S")
    run_dir = os.path.join(out_root, f"{_slug(name)}_{ts}")
    os.makedirs(run_dir, exist_ok=True)

    # Save YAML (or temp)
    if persist_yaml:
        yaml_path = os.path.join(run_dir, "resume.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(yaml_str)
    else:
        tmp = tempfile.NamedTemporaryFile(suffix=".yaml", delete=False)
        tmp.write(yaml_str.encode("utf-8"))
        tmp.flush()
        tmp.close()
        yaml_path = tmp.name

    # Use absolute paths for CLI call
    yaml_path = os.path.abspath(yaml_path)
    run_dir = os.path.abspath(run_dir)

    # Render to run_dir using module invocation to avoid PATH issues
    proc = subprocess.run([sys.executable, "-m", "rendercv", "render", yaml_path, "-o", run_dir], capture_output=True, text=True)

    # filename = f"{_slug(name)}_CV.pdf"
    # pdf_path = os.path.join(run_dir, filename)

    # Try the common default name first, then fall back to any PDF in the folder
    expected_filename = f"{_slug(name)}_CV.pdf"
    pdf_path = os.path.join(run_dir, expected_filename)
    if not os.path.exists(pdf_path):
        # Discover any PDF produced in run_dir (search recursively)
        try:
            found_pdf = None
            for root, _dirs, files in os.walk(run_dir):
                for f in files:
                    if f.lower().endswith(".pdf"):
                        found_pdf = os.path.join(root, f)
                        break
                if found_pdf:
                    break
            if found_pdf:
                pdf_path = found_pdf
                expected_filename = os.path.basename(found_pdf)
        except Exception:
            pass

    # Avoid returning giant base64 by default; caller may opt-in via include_pdf_b64
    do_b64 = bool(include_pdf_b64) and not os.getenv("VERCEL")
    pdf_b64 = ""
    if do_b64 and proc.returncode == 0 and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Clean up temp YAML if not persisted
    if not persist_yaml:
        try: os.remove(yaml_path)
        except Exception: pass

    def _truncate(s: str) -> str:
        s = (s or "").strip()
        if max_log_chars and len(s) > max_log_chars:
            return s[:max_log_chars] + "\n...[truncated]"
        return s

    return json.dumps({
        "yaml_path": yaml_path if persist_yaml else None,
        "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
        "pdf_b64": pdf_b64,
        "output_folder": run_dir,
        "filename": expected_filename,
        "stdout": _truncate(proc.stdout),
        "stderr": _truncate(proc.stderr),
        "returncode": proc.returncode,
    })
