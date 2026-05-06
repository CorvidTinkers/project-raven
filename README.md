# Project Raven: AI Technical Interviewer

Project Raven is an AI-powered technical interviewer that conducts real-time voice interviews, evaluates code, and generates performance reports.

## Project Structure

```text
project-raven/
├── backend/                # FastAPI / Python
│   ├── api/                # HTTP & WebSocket endpoints
│   ├── agents/             # LangGraph orchestration logic
│   ├── tasks/              # Background LangChain tasks
│   ├── services/           # External API & utility services
│   ├── main.py             # Server entry point
│   └── requirements.txt
├── frontend/               # Next.js / TypeScript
│   ├── app/                # App Router
│   ├── components/         # UI Components
│   └── hooks/              # Custom React Hooks
├── docs/                   # Documentation & PRDs
├── .gitignore
├── .env                    # Configuration
│── README.md
```

## Technical Stack

- **Backend**: FastAPI with LangGraph for orchestration and LangChain for background tasks.
- **Frontend**: Next.js 14 with Tailwind CSS, Monaco Editor, and Recharts.
- **AI**: Gemini Multimodal Live API (v1beta).

## Getting Started

### Prerequisites

- Python 3.10+
- Node.js 18+
- Gemini API Key

### Setup

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd project-raven
    ```

2.  **Backend Setup**:
    ```bash
    cd backend
    python -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3.  **Frontend Setup**:
    ```bash
    cd ../frontend
    npm install
    ```

4.  **Environment Variables**:
    Create a `.env` file in the root directory and add your `GEMINI_API_KEY`.

## Documentation

- [Project PRD](docs/project-raven-prd.md)
