# Project Raven: AI Technical Interviewer

Project Raven is a high-fidelity AI-powered technical interviewer that conducts real-time voice interviews, evaluates code, and generates performance reports using the Gemini 2.5 Multimodal Live API.

## Project Structure

```text
project-raven/
├── backend/                # FastAPI / Python (uv managed)
│   ├── api/                # HTTP & WebSocket endpoints
│   ├── agents/             # LangGraph orchestration logic
│   ├── tasks/              # Background LangChain tasks
│   ├── services/           # External API & utility services
│   ├── main.py             # Server entry point
│   └── pyproject.toml      # Dependency management
├── frontend/               # Next.js / TypeScript
│   ├── src/                # Source code
│   │   ├── app/            # App Router
│   │   ├── components/     # UI Components
│   │   └── hooks/          # Custom React Hooks
│   └── package.json
├── docs/                   # Documentation & PRDs
├── .gitignore
├── .env                    # Configuration
│── README.md
```

## Technical Stack

- **Backend**: FastAPI with LangGraph for orchestration.
- **Frontend**: Next.js 15+ with Tailwind CSS, Monaco Editor, and Framer Motion.
- **AI Engine**: Gemini 2.5 Flash (Multimodal Live API) via Vertex AI or AI Studio.
- **Environment**: Python 3.12 managed by `uv`.

## Getting Started

### Prerequisites

- [uv](https://github.com/astral-sh/uv) (for Python package management)
- Node.js 18+
- Google Cloud Project (for Vertex AI) or a Gemini API Key (AI Studio)

### Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd project-raven
    ```

2.  **Backend Setup**:
    ```bash
    cd backend
    uv sync
    ```

3.  **Frontend Setup**:
    ```bash
    cd ../frontend
    npm install
    ```

4.  **Environment Variables**:
    Create a `.env` file in the root directory:
    ```env
    GEMINI_API_KEY=your_api_key
    GOOGLE_CLOUD_PROJECT=your_project_id
    PORT=8000
    ```

## Running the Application

1.  **Start the Backend**:
    ```bash
    cd backend
    uv run main.py
    ```

2.  **Start the Frontend**:
    ```bash
    cd frontend
    npm run dev
    ```

## Documentation

- [Project PRD](docs/project-raven-prd.md)
- [MVP Implementation Plan](docs/plan_mvp.md)
