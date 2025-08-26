import os, base64, tempfile, subprocess
from fastapi import FastAPI, HTTPException, Header
from pydantic import BaseModel

app = FastAPI()

# Optional simple auth so only your backend can call this worker
AUTH = os.getenv("RENDER_WORKER_AUTH")  # set a long random token in Render

class RenderRequest(BaseModel):
    yaml: str
    include_pdf_b64: bool = True  # return base64 by default
    filename: str | None = None   # suggested filename for display

@app.get("/health")
async def health():
    return {"ok": True, "status": "healthy"}

@app.post("/render")
def render(req: RenderRequest, authorization: str | None = Header(default=None)):
    if AUTH and authorization != f"Bearer {AUTH}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    # Check if rendercv is available
    try:
        check_proc = subprocess.run(
            ["python", "-m", "rendercv", "--version"],
            capture_output=True, text=True, timeout=10
        )
        if check_proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"rendercv not available: {check_proc.stderr}")
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=500, detail="rendercv check timed out")
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="rendercv module not found")

    with tempfile.TemporaryDirectory() as td:
        yaml_path = os.path.join(td, "resume.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(req.yaml)

        # Debug: Check what's in the YAML file
        print(f"YAML content: {req.yaml}", file=open(os.path.join(td, "debug.log"), "w"))

        # RenderCV -> PDF (requires TeX + latexmk in the container)
        # Try the render command with different syntax
        proc = subprocess.run(
            ["python", "-m", "rendercv", "render", yaml_path, "--output-folder", td],
            capture_output=True, text=True
        )

        # If that fails, try alternative syntax
        if proc.returncode != 0:
            proc = subprocess.run(
                ["python", "-m", "rendercv", "render", yaml_path, "-o", td],
                capture_output=True, text=True
            )
        if proc.returncode != 0:
            error_msg = f"rendercv failed with return code {proc.returncode}"
            if proc.stderr:
                error_msg += f" | stderr: {proc.stderr[:800]}"
            if proc.stdout:
                error_msg += f" | stdout: {proc.stdout[:800]}"
            raise HTTPException(status_code=500, detail=error_msg)

        # Find the produced PDF
        pdf_path = None
        for root, _, files in os.walk(td):
            for name in files:
                if name.lower().endswith(".pdf"):
                    pdf_path = os.path.join(root, name)
                    break
            if pdf_path:
                break
        if not pdf_path:
            raise HTTPException(status_code=500, detail="PDF not produced")

        filename = req.filename or os.path.basename(pdf_path)

        # Return base64 (simple for v1)
        if req.include_pdf_b64:
            with open(pdf_path, "rb") as fh:
                b64 = base64.b64encode(fh.read()).decode("utf-8")
            return {"pdf_b64": b64, "filename": filename}

        # Fallback to base64 even if include_pdf_b64=False (keeps API simple)
        with open(pdf_path, "rb") as fh:
            b64 = base64.b64encode(fh.read()).decode("utf-8")
        return {"pdf_b64": b64, "filename": filename}
