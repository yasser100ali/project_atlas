# AI SDK Python Streaming Preview

This template demonstrates the usage of [Data Stream Protocol](https://sdk.vercel.ai/docs/ai-sdk-ui/stream-protocol#data-stream-protocol) to stream chat completions from a Python endpoint ([FastAPI](https://fastapi.tiangolo.com)) and display them using the [useChat](https://sdk.vercel.ai/docs/ai-sdk-ui/chatbot#chatbot) hook in your Next.js application.

## Deploy your own

[![Deploy with Vercel](https://vercel.com/button)](https://vercel.com/new/clone?repository-url=https%3A%2F%2Fgithub.com%2Fvercel-labs%2Fai-sdk-preview-python-streaming&env=OPENAI_API_KEY&envDescription=API%20keys%20needed%20for%20application&envLink=https%3A%2F%2Fgithub.com%2Fvercel-labs%2Fai-sdk-preview-python-streaming%2Fblob%2Fmain%2F.env.example)

## Running the Application

This project uses a unified script to run both the frontend and backend services concurrently for a smooth development experience.

1.  **Install dependencies:**
    ```bash
    npm install
    pip install -r requirements.txt
    ```
2.  **Set up your environment:**
    Create a `.env` file in the root directory and add your OpenAI API key:
    ```
    OPENAI_API_KEY=your_openai_key_here
    ```
3.  **Run the development server:**
    ```bash
    npm run dev
    ```
    This will start the Next.js frontend on `http://localhost:3000` and the FastAPI backend on `http://localhost:8000`.

## Project Architecture

This project is a full-stack application that seamlessly integrates a **Next.js frontend** with a **Python (FastAPI) backend**, optimized for development and deployment with Vercel.

### Frontend and Backend Integration

The magic of the local development setup is handled by two key components:

1.  **`concurrently`**: The `npm run dev` script uses this tool to run both the Next.js development server and the Python FastAPI server within a single terminal. You can find this configuration in `package.json`.

2.  **Next.js Proxy**: The frontend, running on `localhost:3000`, communicates with the backend on `localhost:8000` via a proxy. This is configured in `next.config.js`. Any request made from the frontend to a `/api/...` endpoint is automatically forwarded to the Python backend. This setup mimics the production environment and simplifies development.

### The Backend (`/api` folder)

All backend code for this project resides in the `/api` directory. This is a special convention for Vercel.

-   **Entry Point**: The main entry point for all API requests is `api/index.py`. This file contains the FastAPI application that receives requests from the frontend.
-   **Agentic Architecture**: The agentic logic, tools, and any other backend services you build should be organized within this `/api` directory. You can create subdirectories like `api/agents` or `api/services` and import them into `api/index.py` to structure your code.

### Deployment with Vercel (Serverless)

When this project is deployed to Vercel, the integration becomes even more seamless:

-   The Next.js frontend is served as a static site, optimized for global speed via Vercel's Edge Network (CDN).
-   The code within the `/api` directory is automatically deployed as **Serverless Functions**. Vercel handles all the underlying server infrastructure, scaling, and routing. This means you don't need to manage servers; you just write the Python code in the `/api` folder, and Vercel takes care of the rest.

---

This project template was created by [Vercel](https://vercel.com) and has been modified.
