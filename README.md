# Atlas AI Assistant

Intelligent document analysis and web research assistant powered by OpenAI Agents SDK. Atlas can analyze PDF documents, conduct comprehensive web research, and provide evidence-based insights with real-time streaming responses.

## Tech Stack

- **Frontend**: Next.js (React 18), Tailwind CSS, NDJSON streaming client
- **Backend**: FastAPI (Python), OpenAI Agents SDK (agentic orchestration)
- **AI Agents**: PDF Analysis Agent, Research Agent, Web Search capabilities
- **Deployment**: Vercel (dev/prod friendly), portable to Render/AWS

## Features

- **Document Analysis**: Upload and analyze PDF documents with intelligent question-answering
- **Web Research**: Conduct comprehensive research using web search with multiple reputable sources
- **Agentic Workflow**: Intelligent agent orchestration that chooses appropriate tools for each task
- **Real-time Streaming**: Live streaming of agent thoughts, tool calls, and responses
- **Evidence-based Responses**: Citations and sources included in research results
- **Modern UI**: Clean, responsive interface built with Next.js and Tailwind CSS

## Getting started (local dev)

1) Install deps
```bash
npm install
pip install -r requirements.txt
```

2) Configure environment variables in `.env`
```bash
OPENAI_API_KEY=sk-...
# Optional: other configuration variables as needed
```

3) Run both servers
```bash
npm run dev
```
Frontend: http://localhost:3000  |  Backend: http://localhost:8000

## API

- `POST /api/chat` – NDJSON stream of agent events and responses
  - Events: `{event:"thinking"|"tool_call"|"tool_output"|"final"|"error", ...}`
  - Handles both PDF analysis queries and web research requests
  - Returns structured JSON responses with sources and evidence

## Architecture

- **Orchestrator Agent**: Routes requests to appropriate specialized agents
- **PDF Analysis Agent**: Processes uploaded documents and answers questions about content
- **Research Agent**: Conducts web research using search tools and summarizes findings
- **Web Search Tool**: Integrated search capabilities for gathering current information

## Usage Examples

### Document Analysis
```
Upload a PDF and ask: "What are the main findings in this research paper?"
```

### Web Research
```
Ask: "What are the latest developments in artificial intelligence for 2024?"
```

### Combined Queries
```
Ask: "Compare the approaches in this PDF document with current industry standards"
```

## Scripts

- `npm run dev` – Next.js + FastAPI concurrently
- `npm run next-dev` – Next.js only
- `npm run fastapi-dev` – FastAPI only

## Project Structure

```
├── app/                    # Next.js frontend
├── backend/
│   ├── agents/            # AI agents (orchestrator, research, pdf)
│   ├── app.py            # FastAPI application
│   └── utils/            # Utilities and tools
├── components/            # React components
└── lib/                   # Shared utilities
```

## Recent Updates

- Fixed OpenAI Agents SDK schema validation issues for strict JSON compliance
- Updated function tools to use JSON string serialization for agent communication
- Improved error handling and streaming responses

## License

MIT
