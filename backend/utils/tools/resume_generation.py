# tools/rendercv_tools.py
import base64, json, os, re, subprocess, tempfile, time, yaml
from typing import Optional
from agents import function_tool

def _slug(s: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_")

@function_tool
def rendercv_render(
    yaml_str: str,
    out_root: str = "rendercv_output",
    persist_yaml: bool = True
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
    os.makedirs(out_root, exist_ok=True)

    # Name & folder
    loaded_yaml = None
    try:
        loaded_yaml = yaml.safe_load(yaml_str)
        print(f"Safely looaded yaml string: \n{yaml_str}\n")

    except Exception:
        loaded_yaml = None
        print("Loaded yaml failed.")

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

    # Render to run_dir
    cmd = f'rendercv render "{yaml_path}" -o "{run_dir}"'
    proc = subprocess.run(["bash", "-c", cmd], capture_output=True, text=True)

    # filename = f"{_slug(name)}_CV.pdf"
    # pdf_path = os.path.join(run_dir, filename)

    # Try the common default name first, then fall back to any PDF in the folder
    expected_filename = f"{_slug(name)}_CV.pdf"
    pdf_path = os.path.join(run_dir, expected_filename)
    if not os.path.exists(pdf_path):
        # Discover any pdf produced in the run_dir
        try:
            pdf_candidates = [f for f in os.listdir(run_dir) if f.lower().endswith(".pdf")]
            if pdf_candidates:
                expected_filename = pdf_candidates[0]
                pdf_path = os.path.join(run_dir, expected_filename)
        except Exception:
            pass

    pdf_b64 = ""
    if proc.returncode == 0 and os.path.exists(pdf_path):
        with open(pdf_path, "rb") as f:
            pdf_b64 = base64.b64encode(f.read()).decode("utf-8")

    # Clean up temp YAML if not persisted
    if not persist_yaml:
        try: os.remove(yaml_path)
        except Exception: pass

    return json.dumps({
        "yaml_path": yaml_path if persist_yaml else None,
        "pdf_path": pdf_path if os.path.exists(pdf_path) else None,
        "pdf_b64": pdf_b64,
        "output_folder": run_dir,
        # "filename": filename,
        "filename": expected_filename,
        "stdout": proc.stdout.strip(),
        "stderr": proc.stderr.strip(),
        "returncode": proc.returncode,
    })
