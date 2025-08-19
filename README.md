# Apex AI – Career Titan. 

Agentic resume copilot that drafts and renders tailored resumes and searches jobs, with real‑time streaming UX.

## Tech stack

- Frontend: Next.js (React 18), Tailwind, NDJSON streaming client
- Backend: FastAPI (Python), OpenAI Agents SDK (agentic orchestration)
- Tools: RenderCV renderer (PDF generation), JSearch/RapidAPI (job search)
- Deploy: Vercel (dev/prod friendly). Portable to Render/AWS (ECS) with S3 storage

## Features

- Agentic workflow: top‑level agent chooses between job search and resume build tools; automatic YAML repair/retry on render errors
- Live streaming: run‑item events (tool call/output/message) and token deltas to the UI
- Inline PDF viewer: resume is embedded above the assistant message with Open/Download actions
- Robust file delivery: local via `/api/file` (allowlisted paths), serverless via data URL, or S3 signed URLs

## Getting started (local dev)

1) Install deps
```bash
npm install
pip install -r requirements.txt
```

2) Configure environment variables in `.env`
```bash
OPENAI_API_KEY=sk-...
RAPIDAPI_KEY=...
# Optional: persistent output dir; defaults to project dir or /tmp on serverless
RESUME_OUT_DIR=generated_resumes
```

3) Run both servers
```bash
npm run dev
```
Frontend: http://localhost:3000  |  Backend: http://localhost:8000

## API

- `POST /api/chat` – NDJSON stream of agent events and final text
  - Events: `{event:"thinking"|"final"|"resume_ready"|"error", ...}`
  - `resume_ready.data` contains `{url, name, contentType}` for the rendered PDF
- `GET /api/file?path=/abs/path.pdf` – serves PDFs from allowlisted directories (project `generated_resumes/` and `/tmp/generated_resumes`)

## Storage & portability

- Local/Vercel: writes to `generated_resumes/` (local) or `/tmp/generated_resumes` (serverless)
- For Render/AWS: set `RESUME_OUT_DIR` to a mounted disk or switch to S3 and return signed URLs

## Notes

- We avoid putting large base64 blobs in model streams to stay within token limits; the UI receives a link (file route or data URL) via `resume_ready`
- The streaming channel is NDJSON; switch to SSE if your proxy buffers NDJSON in production

## Scripts

- `npm run dev` – Next.js + FastAPI concurrently
- `npm run next-dev` – Next.js only
- `npm run fastapi-dev` – FastAPI only

## License

MIT
