# 🚀 Nexus MCP Chat — Modular Full-Stack AI Chat Application

[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688?style=flat&logo=fastapi)](https://fastapi.tiangolo.com)
[![Model Context Protocol](https://img.shields.io/badge/Protocol-MCP%20v1.0-6366f1?style=flat)](https://modelcontextprotocol.io)
[![TailwindCSS](https://img.shields.io/badge/Frontend-TailwindCSS-38bdf8?style=flat&logo=tailwindcss)](https://tailwindcss.com)
[![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A strictly modular, full-stack conversational AI application that demonstrates **agentic software architectures** by integrating Large Language Models (LLMs) with external tools using the **Model Context Protocol (MCP)**.

---

## 📌 Architectural Overview

```
project-root/
├── backend/
│   ├── main.py              # FastAPI application, CORS middleware, REST endpoints (/api/chat, /api/health)
│   ├── llm_service.py       # LLM orchestrator & MCP function-calling bridge
│   ├── mcp_client.py        # Asynchronous MCP Client with timeout resilience & fallback
│   ├── requirements.txt     # Python backend dependencies
│   ├── .env.example         # Environment template for API keys
│   └── .env                 # Local environment (excluded from Git)
├── frontend/
│   ├── index.html           # Semantic HTML layout (fixed header, scrollable chat, sticky input)
│   ├── css/
│   │   └── styles.css       # Tailwind CSS styling, animations, glassmorphism & typography
│   └── js/
│       └── chat_logic.js    # Asynchronous fetch logic, DOM manipulation & tool rendering
├── mcp_server/
│   └── server.py            # Standard I/O MCP Tool Server (Time, Math, Database, Diagnostics)
├── .gitignore               # Enforces security by excluding .env and cache
└── README.md                # Comprehensive documentation & setup manual
```

---

## 🌟 Key Features

1. **Model Context Protocol (MCP) Integration**:
   - Backend acts as an **MCP Client** over standard I/O (stdio) to dynamically discover and call registered tools on an MCP Server.
   - Includes tools for **System Time & Date**, **Mathematical Calculations**, **Database Queries**, and **Hardware Diagnostics**.
   - Live visual cards for tool invocation steps and execution parameters directly in the chat interface.

2. **Modular Python FastAPI Backend**:
   - Clean separation between API routes (`main.py`), agent orchestration (`llm_service.py`), and MCP protocol drivers (`mcp_client.py`).
   - CORS middleware enabled for cross-origin client integration.
   - Graceful edge-case handling: If the MCP server is down or unresponsive, the backend enforces timeouts and recovers gracefully.

3. **Modern Responsive Client UI**:
   - Built with Tailwind CSS and modern CSS glassmorphism.
   - User messages aligned on the right with vibrant gradients; AI responses aligned on the left with interactive tool call accordions.
   - Markdown rendering (tables, code blocks, bullet points) via `marked.js`.
   - Real-time backend & MCP health status badge.
   - Quick-action suggestion chips and keyboard shortcuts (`Enter` to send, `Shift+Enter` for newlines).

4. **Security Best Practices**:
   - API keys and sensitive tokens are strictly managed via environment variables (`.env`) and excluded from source control via `.gitignore`.

---

## 🛠️ Prerequisites

- **Python**: Version 3.10 or higher
- **Web Browser**: Modern browser (Chrome, Edge, Firefox, Safari)
- **Google Gemini API Key** (optional for live model generation, free at [Google AI Studio](https://aistudio.google.com/))

---

## ⚡ Quick Start Guide

### 1. Clone or Open the Repository

```bash
cd modular-mcp-chat
```

### 2. Configure Environment Variables

Create a `.env` file in the `backend/` directory from the template:

```bash
# On Windows (PowerShell)
Copy-Item backend/.env.example backend/.env

# On Linux/macOS
cp backend/.env.example backend/.env
```

Edit `backend/.env` to supply your API key:
```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
LLM_MODEL=gemini-2.5-flash
PORT=8000
HOST=0.0.0.0
MCP_TIMEOUT=6.0
```
*(Note: If no API key is provided, the application runs in a smart local agent mode that connects directly to the MCP server for testing!)*

---

### 3. Install Backend Dependencies

```bash
# Create a virtual environment (recommended)
python -m venv venv

# Activate virtual environment
# Windows:
.\venv\Scripts\Activate.ps1
# Linux/macOS:
source venv/bin/activate

# Install requirements
pip install -r backend/requirements.txt
```

---

### 4. Running the Application

You can run the full-stack system in either of the following two modes:

#### Option A: Unified Full-Stack Server (Recommended)

The FastAPI backend is configured to automatically manage the MCP server subprocess and serve the frontend client:

```bash
python backend/main.py
```

Then open your browser and navigate to:
👉 **[http://localhost:8000](http://localhost:8000)**

#### Option B: Standalone MCP Server & Separate Frontend

1. **Start the MCP Server in Stdio / Background mode**:
   ```bash
   python mcp_server/server.py
   ```

2. **Start the FastAPI Backend**:
   ```bash
   uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload
   ```

3. **Serve the Frontend**:
   You can serve the `frontend/` directory with any static server:
   ```bash
   # Using Python's built-in HTTP server:
   cd frontend
   python -m http.server 3000
   ```
   Then navigate to **[http://localhost:3000](http://localhost:3000)**.

---

## 🧪 API Endpoints & Testing

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `POST` | `/api/chat` | Main conversational endpoint (accepts `{ message, history }`) |
| `GET` | `/api/health` | Live health diagnostics and MCP server status |
| `GET` | `/api/tools` | Discovers registered Model Context Protocol tools |
| `GET` | `/docs` | Interactive Swagger API documentation |

### Example cURL Request

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "What is the current time in UTC and calculate 45 * 120?"}'
```

---

## 🛡️ Edge Case Resilience

- **MCP Server Timeout**: The MCP client enforces a 6-second timeout per tool call. If an external server hangs or drops connection, the client catches the timeout and falls back to a graceful error payload without crashing the API.
- **Missing API Keys**: The service detects unconfigured API keys and transitions into developer testing mode with full tool capability.
- **Cross-Origin Requests**: Handled via FastAPI's `CORSMiddleware`.

---

## 📦 Pushing to GitHub

To publish this project to your GitHub account:

```bash
# 1. Initialize Git repository
git init

# 2. Stage all files (.env is automatically ignored)
git add .

# 3. Commit your changes
git commit -m "feat: complete modular full-stack MCP chat application"

# 4. Link your remote GitHub repository
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo-name>.git

# 5. Push to GitHub
git push -u origin main
```

---

## 📄 License

This project is open source and available under the [MIT License](LICENSE).
