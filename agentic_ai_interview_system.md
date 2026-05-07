# 🤖 Agentic AI Technical Interview System — Full Assessment

---

## 1. Problem Statement

### The Real-World Problem

Technical interviews are broken — not because the questions are bad, but because the **process is inconsistent, unscalable, and often disconnected from a candidate's actual profile**.

- **For Candidates**: Mock interviews are generic. Platforms like LeetCode assess code, but no platform truly simulates a **real, adaptive, voice-driven interview** that mirrors the actual experience — where a human interviewer reads your resume, asks follow-ups on your internships, probes your projects, and shifts difficulty based on your answers.

- **For Recruiters / Companies**: Screening 100+ candidates manually is expensive and slow. Human bias, inconsistency across interviewers, and lack of structured reporting make it hard to compare candidates fairly. There is no unified system that reads a candidate's resume, conducts a voice interview, tests their technical depth, and produces an objective report.

- **The Gap**: Existing tools (HireVue, Pramp, Interviewing.io) are either too scripted, non-adaptive, not voice-first, or not end-to-end. None of them do **resume-aware, dynamically generated, multi-phase, agentic interviews** in real time.

---

## 2. The Solution

An **Agentic AI Technical Interview System** powered by a **persistent voice agent (Google Gemini Realtime)** that conducts a full structured technical interview — from introduction to DSA/SQL — while a fleet of **background agents** parse the resume, validate claims, generate context-aware questions, assess answers, and compile a detailed performance report.

The system behaves like a **smart human interviewer who has already read your resume, done their homework on your projects, and has a rubric in mind** — all before the interview starts.

---

## 3. Core Features Overview

| Feature | Description |
|---|---|
| Resume Upload & Parsing | PDF resume uploaded pre-interview; parsed by a background agent |
| Voice-First Interview | Gemini Realtime drives the conversation via speech |
| Resume-Aware Questions | Questions generated from actual resume content |
| Dynamic Generative UI | UI updates in real time based on interview phase |
| Project/Skill Selection | Candidate selects projects/skills via UI; agent adjusts questions |
| Parallel Question Generation | Background LLM flows generate questions while user is speaking |
| Live Answer Logging | Transcripts + quality scores logged in real time |
| DSA Code Input | Side-by-side code editor + voice explanation |
| SQL Assessment | Sandboxed SQL runtime or LLM-validated query evaluation |
| Detailed Report | Phase-by-phase performance report with spider/radar graph |
| Company Profile Fit (Phase 3) | Match candidate against a JD/company profile |
| Avatar (Phase 3) | Pre-rendered Blender avatar in the interview panel |

---

## 4. System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js / React)                   │
│                                                                     │
│  ┌──────────────┐  ┌──────────────────┐  ┌──────────────────────┐  │
│  │  Resume      │  │  Dynamic UI      │  │  Interview Panel     │  │
│  │  Upload Page │  │  (Generative UI) │  │  (Voice + Avatar)    │  │
│  └──────┬───────┘  └────────┬─────────┘  └──────────┬───────────┘  │
│         │                   │                        │              │
└─────────┼───────────────────┼────────────────────────┼─────────────┘
          │                   │                        │
          ▼                   ▼                        ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI / Node)                     │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    MAIN AGENT (Gemini Realtime)              │   │
│  │                                                              │   │
│  │   [Node: Intro] → [Node: Experience] → [Node: Projects]     │   │
│  │       → [Node: Skills] → [Node: DSA] → [Node: SQL]          │   │
│  │                                                              │   │
│  │   • Holds conversation context                               │   │
│  │   • Receives question injections from background agents      │   │
│  │   • Pushes transcripts to Logger                             │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌────────────────────────┐   │
│  │  RESUME      │  │  QUESTION     │  │  ASSESSMENT AGENT      │   │
│  │  PARSER      │  │  GENERATOR    │  │                        │   │
│  │  AGENT       │  │  AGENT        │  │  • DSA correctness     │   │
│  │              │  │               │  │  • SQL validation      │   │
│  │  • PDF parse │  │  • Experience │  │  • Answer scoring      │   │
│  │  • Entity    │  │    questions  │  │  • Resume claim check  │   │
│  │    extract   │  │  • Project Qs │  │                        │   │
│  │  • Validate  │  │  • Skill Qs   │  │                        │   │
│  │    claims    │  │  • DSA Qs     │  │                        │   │
│  └──────┬───────┘  └───────┬───────┘  └──────────┬─────────── ┘   │
│         │                  │                      │                 │
│         └──────────────────▼──────────────────────┘                │
│                      ┌───────────────┐                              │
│                      │  QUESTION     │                              │
│                      │  STORE        │                              │
│                      │  (Redis /     │                              │
│                      │   In-memory)  │                              │
│                      └───────┬───────┘                              │
│                              │ inject at right node                 │
│                              ▼                                      │
│                      MAIN AGENT CONTEXT                             │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │                    LOGGER / REPORTER AGENT                   │   │
│  │                                                              │   │
│  │   • Transcripts per phase                                    │   │
│  │   • Answer quality scores                                    │   │
│  │   • Resume match scores                                      │   │
│  │   • Final report generation (PDF + radar chart)              │   │
│  └──────────────────────────────────────────────────────────────┘   │
│                                                                     │
│  ┌──────────────────┐   ┌─────────────────────────────────────┐    │
│  │  SQL RUNTIME     │   │  CODE EXECUTION SANDBOX              │    │
│  │  (Docker / DuckDB│   │  (Pseudo-code LLM eval or           │    │
│  │   / in-memory)   │   │   Judge0 / Piston API)              │    │
│  └──────────────────┘   └─────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 5. User Flow (ASCII)

```
USER OPENS APP
     │
     ▼
┌─────────────────────────────┐
│  STEP 1: Resume Upload       │
│  • Upload PDF resume         │
│  • System starts parsing     │
│    (background, non-blocking)│
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  STEP 2: Pre-Interview Setup │     │  BACKGROUND (parallel):      │
│  • Interview briefing screen │────▶│  • Resume Parser Agent runs  │
│  • "Start Interview" button  │     │  • Extracts: skills,         │
│                              │     │    internships, projects      │
└─────────────┬───────────────┘     │  • Generates Experience Qs   │
              │                     │  • Stores in Question Store   │
              ▼                     └──────────────────────────────┘
┌─────────────────────────────┐
│  STEP 3: Voice Connect       │
│  • Gemini Realtime connects  │
│  • Microphone access granted │
│  • Interview begins          │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  NODE 1: Introduction        │
│  Agent: "Tell me about       │
│  yourself"                   │
│  User: speaks                │
│  [Transcript logged]         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐     ┌──────────────────────────────┐
│  NODE 2: Experience Deep     │     │  BACKGROUND:                 │
│  Dive                        │     │  • Resume claim vs spoken    │
│  Agent: "Tell me about your  │────▶│    claim matching            │
│  internship at X"            │     │  • Flag discrepancies        │
│  [Injected from Q-Store]     │     │  • Score answer quality      │
│  Follow-up Qs on internship  │     └──────────────────────────────┘
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  NODE 3: Project Selection   │◀─── GENERATIVE UI RENDERS:
│  UI shows cards:             │     • Project cards from resume
│  [Project A] [Project B]     │     • Skill badges
│  [Project C]                 │     (dynamically generated)
│  User clicks one             │
└─────────────┬───────────────┘
              │                      ┌──────────────────────────────┐
              │                      │  BACKGROUND:                 │
              ▼                      │  • LLM generates project-    │
┌─────────────────────────────┐      │    specific questions        │
│  NODE 4: Project Deep Dive   │◀────│  • Pushes to Q-Store         │
│  Agent asks 4-6 Qs about     │     │  • Tech stack probing        │
│  selected project            │     └──────────────────────────────┘
│  [Q injected from Q-Store]   │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  NODE 5: Skills Assessment   │◀─── UI renders skill tags
│  User selects skill          │     (e.g. React, Python, SQL)
│  Agent asks depth questions  │
└─────────────┬───────────────┘
              │
              ▼  ── ── ── ── ── [PHASE 2 BELOW] ── ── ── ── ──
              │
              ▼
┌─────────────────────────────┐
│  NODE 6: DSA Round           │
│  UI: Code editor appears     │
│  Agent explains problem      │
│  User: types code +          │
│        explains approach     │
│  [LLM assesses code]         │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  NODE 7: SQL Round           │
│  UI: Table schema shown      │
│  Agent reads question aloud  │
│  User types SQL query        │
│  [Runtime / LLM validates]   │
└─────────────┬───────────────┘
              │
              ▼
┌─────────────────────────────┐
│  END: Report Generated       │
│  • Phase-wise scores         │
│  • Spider/radar graph        │
│  • Improvement suggestions   │
│  • Downloadable PDF          │
└─────────────────────────────┘
```

---

## 6. Feature List by Phase

### 🔵 Phase 1 — MVP

| # | Feature | Notes |
|---|---|---|
| 1 | PDF Resume Upload | Upload before interview starts |
| 2 | Resume Parsing Agent | Extracts skills, internships, projects, tech stack |
| 3 | Gemini Realtime Voice Agent | Main interview driver via speech |
| 4 | Node-based Agent Traversal | Introduction → Experience → Projects → Skills |
| 5 | Parallel Question Generation | Background LLM generates Qs while user speaks |
| 6 | Question Store (Redis/in-memory) | Holds per-node question queues |
| 7 | Question Injection to Main Agent | Push Qs into main agent context at right node |
| 8 | Resume Claim Validation | Match spoken experience vs resume data |
| 9 | Dynamic Generative UI — Projects | Cards for projects shown dynamically |
| 10 | Dynamic Generative UI — Skills | Skill badges rendered from resume parse |
| 11 | Project-specific Q Generation | LLM generates Qs per chosen project |
| 12 | Live Transcript Logger | Record all spoken answers per phase |
| 13 | Answer Quality Scorer | LLM-based rubric scoring per answer |
| 14 | End-of-Interview Report | Phase-wise summary with scores |

---

### 🟡 Phase 2 — Technical Depth

| # | Feature | Notes |
|---|---|---|
| 15 | DSA Round Node | Code editor + voice explanation panel |
| 16 | Pseudo-code Submission | User types approach; LLM assesses logic |
| 17 | Code Execution Sandbox | Optional: Judge0 / Piston API for live run |
| 18 | SQL Round Node | Schema display + query input UI |
| 19 | SQL Runtime (Docker/DuckDB) | Execute user queries against pre-seeded tables |
| 20 | SQL LLM Validator | Alternative: LLM assesses query correctness |
| 21 | DSA Background Assessment Agent | Parallel LLM flow to score code quality |
| 22 | Dynamic UI State Machine | UI transforms per interview node |
| 23 | Spider / Radar Graph in Report | Visual performance breakdown |
| 24 | Downloadable PDF Report | Full formatted post-interview report |

---

### 🔴 Phase 3 — Enterprise & Immersion

| # | Feature | Notes |
|---|---|---|
| 25 | Company Profile / JD Upload | Attach a JD before interview |
| 26 | JD-Aware Question Generation | Qs tailored to role requirements |
| 27 | Candidate-Role Fit Score | Match report against JD criteria |
| 28 | Blender Avatar Integration | Pre-rendered lip-synced avatar in interview panel |
| 29 | Multi-candidate Comparison Dashboard | For recruiter use |
| 30 | Feedback Loop / Retry Mode | Re-attempt specific sections |

---

## 7. Technology Stack (Recommended)

| Layer | Technology |
|---|---|
| Frontend | Next.js 14 (App Router), TailwindCSS, Shadcn/UI |
| Voice Agent | Google Gemini Realtime API (Live API) |
| Background LLM Flows | LangChain / LangGraph (Python) |
| Resume Parsing | PyMuPDF + LLM extraction (Gemini Flash) |
| Question Store | Redis (with TTL per session) |
| Code Execution | Judge0 API or Piston (self-hosted) |
| SQL Runtime | DuckDB (in-process) or Docker + PostgreSQL |
| Report Generation | ReportLab (PDF) + Recharts (Spider graph) |
| Backend API | FastAPI (Python) |
| Realtime Transport | WebSockets (for voice + UI state sync) |
| Avatar (Phase 3) | Blender + Three.js (GLTF model + lipsync) |
| Auth + Sessions | Supabase / Firebase |

---

## 8. Problems in the Idea & Solutions

### 🔴 Problem 1: Main Agent Context Bloat
**Issue**: As the interview progresses through nodes (intro → experience → projects → DSA), the main Gemini agent's context window grows with transcripts, injected questions, and prior turns. This can cause degraded performance, hallucinations, or the agent forgetting earlier instructions.

**Solution**:
- Implement **sliding context windows** — at each node transition, trim historical turns and keep only a **structured summary** (generated by a background LLM call) instead of raw transcript.
- Use a **system-level node instruction swap** — each node gets a focused system prompt instead of accumulating a mega-prompt.
- Store full history in a DB; only pass the last N turns + node summary to the Realtime agent.

---

### 🔴 Problem 2: Question Injection Timing
**Issue**: The background Q-generation agent may not finish before the main agent reaches that node in the interview. Injecting questions too late (or too early) can break the conversation flow.

**Solution**:
- Generate questions **during the resume upload phase** (before interview starts) for Introduction and Experience nodes — these are always predictable.
- For Project/Skill nodes, start generation **as soon as the user selects a project/skill** — there's a 5–10 second buffer before the agent starts that section.
- Add a **readiness flag per node** in the Question Store — the main agent only proceeds to a question if the flag is `READY`; otherwise it asks a generic bridge question like "Any other aspect you'd like to highlight?" to buy time.

---

### 🔴 Problem 3: Resume Claim vs. Spoken Answer Mismatch Logic
**Issue**: Determining whether a candidate's spoken answer "matches" their resume requires semantic understanding across both a structured document and unstructured speech. False positives (flagging valid expansions of resume points) and false negatives (missing outright fabrications) are both costly.

**Solution**:
- Don't do binary match/no-match. Instead, run a **semantic similarity score** (e.g., cosine similarity of embeddings) between resume sections and spoken content.
- Use an LLM prompt like: *"Given resume bullet [X], rate how consistent and well-supported the candidate's spoken explanation is on a scale of 1–5 with justification."*
- Flag only **critical discrepancies** (e.g., claiming to have led a team when resume says intern) and surface them in the report, not in real time to avoid disrupting flow.

---

### 🔴 Problem 4: Gemini Realtime API — Interruptions & Flow Control
**Issue**: Gemini Realtime (Live API) supports barge-in (user interrupting the model), which is realistic but can cause the agent to lose its place in the interview node graph, repeat questions, or skip important sections.

**Solution**:
- Maintain a **server-side state machine** (not inside the agent's context) that tracks which node the interview is at and which questions have been asked.
- After every agent turn, the backend checks: *"Was the question acknowledged/answered?"* If yes, mark it done and move to next. This is tracked externally, not relying on the LLM's memory.
- Use function-calling or structured outputs from the agent to emit signals like `{"node": "experience", "question_id": 3, "status": "answered"}` so the backend can track state cleanly.

---

### 🟡 Problem 5: Generative UI Consistency
**Issue**: Dynamically rendering project cards and skill badges from an LLM's output can result in inconsistent formats, broken components, or hallucinated projects not in the resume.

**Solution**:
- **Do not generate UI directly from LLM freeform text.** Instead, the resume parser produces a **strict JSON schema** (`{ projects: [], skills: [] }`) validated by Zod/Pydantic. The UI renders from this schema deterministically.
- The LLM's role in UI generation is only to **classify and structure** the parsed data, not to invent it.
- UI components are pre-built card templates — the LLM just fills in the slots.

---

### 🟡 Problem 6: DSA Assessment Without Code Execution
**Issue**: If using pseudo-code or explanation-only DSA assessment, it's hard to objectively evaluate correctness. LLMs may be lenient or inconsistent.

**Solution**:
- Use a **two-track approach**: The user both types code AND explains verbally.
- For code: run it through a sandboxed executor (Judge0) against hidden test cases.
- For pseudo-code-only mode: use a structured LLM rubric — *"Does the solution address the correct time complexity? Does it handle edge cases?"* — scored on 5 explicit axes, not vague overall impression.
- Display the rubric to the candidate upfront (transparent scoring).

---

### 🟡 Problem 7: SQL Runtime Security
**Issue**: Running user-submitted SQL queries in a live database (even Docker-isolated) poses risks — destructive queries, resource exhaustion, injection attempts beyond the sandbox.

**Solution**:
- Use **DuckDB in-process** — it's a file-based analytical DB with no network surface, and it's trivially sandboxed.
- Only allow `SELECT` statements; parse the AST before execution and reject anything else.
- Pre-seed read-only schema snapshots per session — each session gets its own in-memory DuckDB instance that gets destroyed after the round.
- As a simpler alternative for MVP: use LLM-based SQL validation with a hardcoded expected answer — validate semantic equivalence, not literal string match.

---

### 🟡 Problem 8: Realtime Voice Latency & UX
**Issue**: Gemini Realtime adds inherent network latency. Combined with question injection delays and background LLM calls, the user may experience awkward silences or abrupt transitions.

**Solution**:
- Use **filler bridge phrases** injected by the system during processing: *"That's interesting, give me a moment to pull up my next question."* — this is a canned audio clip or a TTS phrase that masks processing time.
- Pre-warm the next node's question set while the current node is still in progress.
- Show a **subtle UI indicator** ("Interviewer is thinking...") so the user understands the pause is intentional.

---

### 🟡 Problem 9: Multi-Phase State Persistence (Session Crashes)
**Issue**: If the user's connection drops mid-interview (network issues, browser refresh), all state — current node, answered questions, transcript — is lost.

**Solution**:
- Persist interview state to a backend store (Redis + DB) after **every agent turn**.
- Implement a **resume session** flow — if the same user reconnects within 30 minutes, restore state and continue from the last answered question.
- Store transcripts in a DB (not in-memory only) so the report can still be generated even if the session ends abruptly.

---

### 🟢 Problem 10: Avatar Lipsync Complexity (Phase 3)
**Issue**: Syncing a Blender-rendered avatar's lip movements to Gemini Realtime audio output is technically non-trivial and can feel uncanny if not done well.

**Solution**:
- For Phase 3 MVP: use **pre-rendered looping animations** (talking, thinking, idle) triggered by voice activity detection — not true phoneme-level lipsync. This is much simpler and still effective.
- For full lipsync: use **Oculus OVR Lipsync** or **rhubarb-lip-sync** on the generated audio to produce phoneme timings, then map to blend shapes on the GLTF model in Three.js.
- Consider using **Ready Player Me** avatar instead of custom Blender — faster to integrate, has built-in lipsync support.

---

## 9. Summary Assessment

### ✅ Strengths
- **Genuinely novel end-to-end system** — no existing product does resume-aware, voice-driven, multi-phase agentic interviewing this way.
- **Agentic architecture is well thought out** — the separation of the main conversational agent and background task agents is the right design pattern.
- **Generative UI for project/skill selection** is a differentiator — it makes the system feel adaptive, not scripted.
- **Phase-wise development is realistic** — Phase 1 (MVP) is buildable in 4–8 weeks with a focused team.

### ⚠️ Key Risks
- **Gemini Realtime API maturity** — the Live API is relatively new; rate limits, pricing, and reliability at scale need to be validated early.
- **Context management is the hardest engineering problem** — getting the main agent to stay coherent across 45–60 minute interviews requires careful state design.
- **User experience of awkward silences** — background LLM latency must be masked with good UX, or the interview feels robotic.

### 🏆 Verdict
**High-potential, technically ambitious, and well-phased.** The core insight — that a voice agent should be *resume-aware* and *dynamically question-generating* rather than static — is the right idea. Execute Phase 1 cleanly, validate with real users, then layer in Phase 2. The architecture described is sound; the biggest executional risk is state/context management across a long voice session.

---

*Document prepared for project planning purposes — Version 1.0*
