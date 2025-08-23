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

@app.get("/healthz")
def healthz():
    return {"ok": True}

@app.post("/render")
def render(req: RenderRequest, authorization: str | None = Header(default=None)):
    if AUTH and authorization != f"Bearer {AUTH}":
        raise HTTPException(status_code=401, detail="Unauthorized")

    with tempfile.TemporaryDirectory() as td:
        yaml_path = os.path.join(td, "resume.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            f.write(req.yaml)

        # RenderCV -> PDF (requires TeX + latexmk in the container)
        proc = subprocess.run(
            ["python", "-m", "rendercv", "render", yaml_path, "-o", td],
            capture_output=True, text=True
        )
        if proc.returncode != 0:
            raise HTTPException(status_code=500, detail=f"rendercv failed: {proc.stderr[:800]}")

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
