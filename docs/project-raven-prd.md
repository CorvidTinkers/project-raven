# Project Raven: AI Technical Interviewer

Building **Project Raven** is a highly ambitious and technically complex undertaking. The core challenge here is bridging the gap between a **continuous, real-time voice stream** (Gemini Realtime) and a **deterministic, structured state machine** (the interview phases).

Your proposed stack—**LangGraph for the main agent/orchestration, LangChain for background tasks, and Gemini Realtime for the voice interface**—is absolutely the **right choice**. 

Here is a detailed, engineering-focused breakdown of how to architect, plan, and implement this system, especially focusing on your questions about the two-part system and the sliding context window.

---

### 1. Is the Technology Choice Right? (The "Two-Part" System)

**Yes, this is the most robust way to build Agentic systems today.** 
If you try to make one single LLM handle the conversation, parse the resume, grade the code, and remember the whole interview, it will hallucinate, lag, and fail.

*   **Front Main Agent (Gemini Realtime API via WebSockets):** Responsible **only** for natural, low-latency conversation. It acts as the "mouth and ears."
*   **The Orchestrator (LangGraph):** Acts as the "brain." It tracks what stage of the interview you are in, holds the state, and decides when to move to the next phase.
*   **Background Tasks (LangChain / FastAPI Background Tasks):** Acts as the "analysts." They run asynchronously (e.g., parsing the resume, validating claims, grading DSA code) without blocking the user's conversation.

---

### 2. Architecture: How the Components Interact

Here is how you will map out the backend system:

```text
                                ┌──────────────────────────────────────────────┐
                                │             LangGraph (The Brain)            │
                                │                                              │
┌────────────────┐             │  [Intro] ──▶ [Experience] ──▶ [DSA] ──▶ End  │
│                │  WebSockets │    ▲              │             │            │
│ Client (React) │ ◀─────────▶ │ ───┴──────────────┴─────────────┴─────────── │
│ • Voice        │             │    │ (Updates System Prompts & Context)      │
│ • Editor       │             └────┼─────────────────────────────────────────┘
│ • Dynamic UI   │                  │             
└────────────────┘                  ▼             
        │               ┌───────────────────────┐ 
        │ HTTP API      │ Gemini Realtime API   │ (The Mouth/Ears)
        ▼               │ (Persistent Session)  │ 
┌────────────────┐      └───────────────────────┘ 
│ FastAPI Router │                  ▲
│ (HTTP & WS)    │                  │
└────────────────┘                  ▼
        │               ┌───────────────────────┐
        │ Trigger       │ LangChain Background  │ (The Analysts)
        └─────────────▶ │ Tasks                │
                        │ • Q-Generation        │
                        │ • Resume Scoring      │
                        └───────────────────────┘
```

#### How it works in practice:
1. The React frontend opens a WebSocket to your FastAPI backend.
2. FastAPI opens a corresponding WebSocket to the **Gemini Realtime API**.
3. FastAPI initializes a **LangGraph State** for the user (`InterviewState`).
4. As the user speaks, Gemini replies instantly. However, Gemini is given a "Tool" called `advance_stage`.
5. When Gemini feels a section is done (or time is up), it calls that tool. FastAPI catches this, advances the LangGraph node, and pushes new instructions back to Gemini.

---

### 3. Handling the Sliding / Constantly Changing Context Window

This is the hardest problem. A 45-minute interview will easily blow past optimal context limits, causing the LLM to "forget" instructions or become sluggish.

**The Solution: The "Summarize & Swap" Pattern using LangGraph.**

You do not keep the entire transcript in the active Gemini context window. Instead, you treat the interview as discrete nodes. When transitioning from Node A (Intro) to Node B (Experience):

1. **The Trigger:** The current node ends (e.g., Gemini calls `end_intro()`).
2. **The Summarizer (Background LangChain task):** LangGraph triggers a fast, cheap LLM (like Gemini 1.5 Flash) to summarize the Intro phase. *("User introduced themselves as a backend dev. Mentioned a strong interest in distributed systems.")*
3. **The State Update:** LangGraph updates the central state object.
4. **The Swap (`session.update`):** You send a WebSockets `session.update` payload to the Gemini Realtime API. You completely **replace** its System Prompt.

**Example of the Dynamic System Prompt (Injected into Gemini):**
```text
You are Raven, a senior engineering interviewer. 
CURRENT STAGE: Deep Dive into Experience.

PREVIOUS CONTEXT (Do not ask about this again):
- Candidate is a Backend Dev interested in distributed systems.

NEW OBJECTIVE:
- Ask the candidate about their Internship at Google.
- Focus strictly on the question: "How did you optimize the caching layer?"

Wait for their answer, ask 1 follow-up, then call the tool `advance_stage`.
```
**Why this works:** The Gemini Realtime agent only ever "sees" the instructions for the exact minute it is in. It relies on the LangGraph state for long-term memory.

---

### 4. Step-by-Step Implementation Plan

#### Step 1: Define the LangGraph State
Start by defining the exact state your interview will hold in Python using `TypedDict` and LangGraph.

```python
from typing import TypedDict, List
from langgraph.graph import StateGraph

class InterviewState(TypedDict):
    candidate_id: str
    resume_data: dict          # Extracted by background task
    current_stage: str         # "intro", "experience", "dsa", "report"
    past_summaries: List[str]  # Sliding context
    current_questions: List[str] # Injected from Q-generator
    transcript: List[dict]     # Full log for the final report
```

#### Step 2: Build the Background Q-Generator (LangChain)
Before the interview starts (when the resume is uploaded), trigger an async task. 
Use LangChain to extract entities and generate questions. Push these into an in-memory store or directly into the Database attached to the `candidate_id`.

```python
# background_tasks.py
async def generate_questions_from_resume(resume_text: str):
    prompt = PromptTemplate.from_template("Extract projects and generate 3 hard questions for: {resume}")
    chain = prompt | llm | JsonOutputParser()
    questions = await chain.ainvoke({"resume": resume_text})
    # Save to in-memory state so LangGraph can pull them when the interview reaches the 'experience' node.
    in_memory_store[f"questions:{user_id}"] = json.dumps(questions)
```

#### Step 3: Integrate Gemini Realtime via WebSockets
FastAPI will act as a proxy between the React Frontend and Google's servers. 
When LangGraph changes a state, you send a `session.update` to Google.

```python
# Pseudocode for FastAPI WebSocket endpoint
@app.websocket("/ws/interview")
async def interview_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # Connect to Google Gemini Realtime
    async with websockets.connect("wss://generativelanguage.googleapis.com/ws/...") as gemini_ws:
        
        # 1. Initialize LangGraph State
        state = init_langgraph_state()
        
        # 2. Send initial prompt to Gemini
        await send_system_prompt_to_gemini(gemini_ws, state)

        # 3. Bi-directional proxy
        while True:
            # If user speaks -> send to Gemini
            # If Gemini speaks -> send to User
            
            # If Gemini uses a Tool Call (e.g., "stage_complete"):
            if is_tool_call(message):
                # 4. LangGraph advances state
                new_state = langgraph_app.invoke(state)
                # 5. Inject new context via Sliding Window
                await update_gemini_context(gemini_ws, new_state)
```

#### Step 4: The Generative UI & Sandbox Synchronization
When LangGraph transitions to the "DSA" node, it shouldn't just update Gemini. It must emit a JSON event to your React frontend.
*   **FastAPI emits:** `{"event": "ui_update", "component": "code_editor", "language": "python"}`
*   **React catches this:** Hides the avatar/project cards, mounts the Monaco Editor (Code Sandbox).
*   While the user types code, React sends the code back via standard HTTP (not the voice websocket) to an execution sandbox (e.g., Judge0 API) which LangChain then evaluates in the background.

---

### 5. Potential Pitfalls & How to Avoid Them

1.  **Race Conditions between Voice and Background Tasks:** 
    *   *Problem:* The user reaches the "Project" stage, but the background LangChain agent hasn't finished generating the custom questions yet.
    *   *Fix:* Implement "Readiness Flags" in LangGraph. If `questions_ready == False`, inject a prompt into Gemini instructing it to ask a generic bridge question to buy time: *"Before we dive into your projects, what is your favorite programming language and why?"*
2.  **Tool Call Latency:**
    *   *Problem:* Relying on Gemini to call `advance_stage` might lag. 
    *   *Fix:* Have a hard timeout in LangGraph. If a node lasts longer than 8 minutes, the backend forcefully triggers a state transition and updates the Gemini session context.
3.  **Generative UI Hallucinations:**
    *   Never let the voice LLM dictate UI state directly. The Voice LLM updates LangGraph. LangGraph enforces a strict Pydantic/Zod schema and *then* sends the deterministic UI command to the frontend.

### Summary Checklist for Implementation

1.  [ ] **MVP:** Build a simple FastAPI + WebSockets + Next.js app that just proxies voice to Gemini Realtime.
2.  [ ] **State Injection:** Prove you can send a `session.update` mid-conversation to change the AI's personality/topic seamlessly.
3.[ ] **LangGraph Orchestration:** Build the state graph (`Intro -> Projects -> DSA -> End`) and hook it to the session updates.
4.  [ ] **Background Tasks:** Add the LangChain resume parser on the PDF upload endpoint.
5.  [ ] **Dynamic UI:** Send UI-trigger JSONs down the websocket alongside the audio.





Implementing **Project Raven** requires careful orchestration of real-time audio streams, agentic state machines, and background LLM flows. Based on the latest Google Gemini Multimodal Live API specifications (using the `v1beta` WebSocket endpoint), here is the detailed, step-by-step technical implementation guide for all five milestones.

---

### 1. MVP: FastAPI + WebSockets + Next.js Proxy

The goal here is a pure voice proxy: **Browser Mic → FastAPI WebSocket → Gemini Live API → FastAPI WebSocket → Browser Speaker**.

#### **Backend (FastAPI)**
Gemini Live API requires a stateful WebSocket connection. We will use FastAPI to proxy this so your API key isn't exposed to the frontend.
*   **Audio Specs**: Input must be raw 16-bit PCM at 16kHz (Little-endian). Output comes back at 24kHz.

```python
# main.py (FastAPI)
import os
import json
import websockets
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
# v1beta is the current standard for the Live API
GEMINI_WS_URL = f"wss://generativelanguage.googleapis.com/ws/google.ai.generativelanguage.v1beta.GenerativeService.BidiGenerateContent?key={GEMINI_API_KEY}"

@app.websocket("/ws/interview")
async def interview_endpoint(client_ws: WebSocket):
    await client_ws.accept()
    
    async with websockets.connect(GEMINI_WS_URL) as gemini_ws:
        # 1. Send Setup Message to Gemini
        setup_msg = {
            "setup": {
                "model": "models/gemini-2.0-flash-exp",
                "systemInstruction": {"parts": [{"text": "You are Raven, an AI technical interviewer."}]}
            }
        }
        await gemini_ws.send(json.dumps(setup_msg))
        
        # 2. Bi-directional looping using asyncio.gather
        import asyncio
        async def receive_from_client():
            try:
                while True:
                    data = await client_ws.receive_json()
                    # Client sends {"realtimeInput": {"mediaChunks":[{"mimeType": "audio/pcm;rate=16000", "data": "<base64>"}]}}
                    await gemini_ws.send(json.dumps(data))
            except WebSocketDisconnect:
                pass

        async def receive_from_gemini():
            try:
                while True:
                    response = await gemini_ws.recv()
                    data = json.loads(response)
                    # Forward Gemini's audio parts back to Next.js
                    await client_ws.send_json(data)
            except websockets.exceptions.ConnectionClosed:
                pass

        await asyncio.gather(receive_from_client(), receive_from_gemini())
```

#### **Frontend (Next.js 14)**
Use the browser's `AudioContext` and `ScriptProcessorNode` (or `AudioWorklet`) to capture 16kHz audio, convert it to Base64, and send it.

```typescript
// components/InterviewRoom.tsx
import { useEffect, useRef } from 'react';

export default function InterviewRoom() {
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    ws.current = new WebSocket('ws://localhost:8000/ws/interview');
    
    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.serverContent?.modelTurn?.parts) {
        // Play audio buffer returned from Gemini (24kHz Base64 PCM)
        playAudio(data.serverContent.modelTurn.parts[0].inlineData.data);
      }
    };

    return () => ws.current?.close();
  },[]);

  const startMic = async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    const context = new AudioContext({ sampleRate: 16000 });
    const source = context.createMediaStreamSource(stream);
    const processor = context.createScriptProcessor(4096, 1, 1);
    
    processor.onaudioprocess = (e) => {
      const floatData = e.inputBuffer.getChannelData(0);
      const pcm16Data = convertFloat32ToInt16(floatData); // Custom function
      const base64Audio = btoa(String.fromCharCode(...new Uint8Array(pcm16Data.buffer)));
      
      // Send realtime audio chunk to FastAPI
      ws.current?.send(JSON.stringify({
        realtimeInput: {
          mediaChunks:[{ mimeType: "audio/pcm;rate=16000", data: base64Audio }]
        }
      }));
    };
    source.connect(processor);
    processor.connect(context.destination);
  };

  return <button onClick={startMic}>Start Interview</button>;
}
```

---

### 2. State Injection: Seamlessly Steering the AI

**The Problem:** You cannot modify the core `systemInstruction` of a Gemini WebSocket once it's open.
**The Solution:** Instead of a hard reboot, you inject a high-priority "System Command" as a `clientContent` message (text turn). This acts as an invisible steer.

```python
# Helper function in FastAPI
async def inject_system_command(gemini_ws, command: str):
    """
    Forces the AI to acknowledge a new state without the user having to speak.
    """
    injection_msg = {
        "clientContent": {
            "turns": [{
                "role": "user", 
                "parts": [{"text": f"[SYSTEM INSTRUCTION - DO NOT READ ALOUD]: {command}"}]
            }],
            "turnComplete": True
        }
    }
    await gemini_ws.send(json.dumps(injection_msg))

# Example usage mid-conversation:
await inject_system_command(gemini_ws, 
    "The Intro phase is over. Transition immediately to the Experience phase. "
    "Ask the candidate about their 'Stripe API' project from their resume."
)
```

---

### 3. LangGraph Orchestration: The Agentic Brain

LangGraph acts as the state machine tracking your interview nodes (`Intro`, `Projects`, `DSA`, `End`).

1. Provide Gemini with a Tool called `advance_stage`.
2. When Gemini calls the tool, FastAPI pauses audio forwarding, triggers LangGraph to mutate state, and then injects the new state back into Gemini.

```python
from langgraph.graph import StateGraph
from typing import TypedDict

class InterviewState(TypedDict):
    stage: str # 'intro', 'experience', 'dsa', 'report'
    resume_context: str

def advance_interview_node(state: InterviewState):
    # Determine next stage
    stages = ["intro", "experience", "dsa", "report"]
    current_idx = stages.index(state["stage"])
    next_stage = stages[current_idx + 1]
    
    # Generate the instruction for the new stage
    instructions = {
        "experience": "Move to Experience. Ask about the React frontend.",
        "dsa": "Move to DSA. Ask them to write a Two-Sum function.",
        "report": "Conclude the interview and say goodbye."
    }
    return {"stage": next_stage, "instruction": instructions[next_stage]}

# Build Graph
workflow = StateGraph(InterviewState)
workflow.add_node("transition", advance_interview_node)
workflow.set_entry_point("transition")
app = workflow.compile()

# Integration in your WebSocket loop:
# When receiving data from Gemini:
if "toolCall" in data:
    tool_name = data["toolCall"]["functionCalls"][0]["name"]
    if tool_name == "advance_stage":
        # 1. Update LangGraph State
        new_state = app.invoke({"stage": current_stage})
        current_stage = new_state["stage"]
        
        # 2. Tell Gemini the tool execution was successful
        tool_response = {
            "toolResponse": {
                "functionResponses": [{"id": data["toolCall"]["functionCalls"][0]["id"], "response": {"status": "ok"}}]
            }
        }
        await gemini_ws.send(json.dumps(tool_response))
        
        # 3. Inject new context via our stealth injection method
        await inject_system_command(gemini_ws, new_state["instruction"])
```

---

### 4. Background Tasks: LangChain Resume Parser

You need an upload endpoint that accepts a PDF, parses it via an LLM, and stores the structured schema in-memory *before* the WebSocket interview starts.

```python
import fitz  # PyMuPDF
from fastapi import UploadFile, BackgroundTasks
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.pydantic_v1 import BaseModel, Field
from langchain.output_parsers import PydanticOutputParser
from langchain_core.prompts import PromptTemplate

# Define structured output
class ResumeData(BaseModel):
    skills: list[str] = Field(description="List of technical skills")
    projects: list[str] = Field(description="List of project names and brief descriptions")
    experience_queries: list[str] = Field(description="3 generated interview questions based on work history")

parser = PydanticOutputParser(pydantic_object=ResumeData)

def process_resume_background(file_content: bytes, candidate_id: str):
    # 1. Extract Text
    doc = fitz.open(stream=file_content, filetype="pdf")
    text = "".join(page.get_text() for page in doc)
    
    # 2. Process with LangChain (Using Gemini 1.5 Flash for speed)
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
    prompt = PromptTemplate(
        template="Extract the following details from this resume.\n{format_instructions}\nResume: {text}\n",
        input_variables=["text"],
        partial_variables={"format_instructions": parser.get_format_instructions()},
    )
    chain = prompt | llm | parser
    structured_resume = chain.invoke({"text": text})
    
    # 3. Save to in-memory state (LangGraph will pull this during the interview)
    # in_memory_store[f"resume:{candidate_id}"] = structured_resume.json()

@app.post("/upload_resume/{candidate_id}")
async def upload_resume(candidate_id: str, file: UploadFile, background_tasks: BackgroundTasks):
    content = await file.read()
    # Execute non-blocking
    background_tasks.add_task(process_resume_background, content, candidate_id)
    return {"status": "parsing_started"}
```

---

### 5. Dynamic UI: WebSocket Control Signals

Since your Next.js frontend is already connected to FastAPI via WebSocket, you can use that **same connection** to push non-audio JSON commands to trigger UI changes (like mounting a code editor).

Modify the FastAPI LangGraph integration so that when the stage changes, it tells the frontend to update the DOM.

**Backend (FastAPI side):**
```python
# Inside your toolCall handling logic where stage transitions happen:

if current_stage == "dsa":
    # Tell Next.js to open the Monaco Editor
    ui_command = {
        "type": "ui_update",
        "payload": {
            "component": "code_editor",
            "language": "python",
            "default_text": "def two_sum(nums, target):\n    pass"
        }
    }
    # Send directly to the frontend client (NOT to Gemini)
    await client_ws.send_json(ui_command)
```

**Frontend (Next.js side):**
```tsx
import { useState } from 'react';
import Editor from "@monaco-editor/react";

export default function InterviewRoom() {
  const[uiState, setUiState] = useState<'avatar' | 'code_editor'>('avatar');
  const [editorProps, setEditorProps] = useState(null);

  // Inside your WebSocket onmessage handler:
  ws.current.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    // Check if it's a UI control signal from FastAPI
    if (data.type === "ui_update") {
      if (data.payload.component === "code_editor") {
        setUiState('code_editor');
        setEditorProps(data.payload);
      }
    }
    // Else process audio from Gemini...
  };

  return (
    <div className="flex h-screen">
      <div className="w-1/2">
        {/* Persistent Interviewer Avatar/Audio Panel */}
        <VoiceVisualizer />
      </div>
      
      <div className="w-1/2">
        {/* Dynamic UI Panel */}
        {uiState === 'avatar' && <ResumeSummaryCard />}
        {uiState === 'code_editor' && (
           <Editor 
              height="90vh" 
              language={editorProps.language} 
              defaultValue={editorProps.default_text} 
           />
        )}
      </div>
    </div>
  );
}
```

### Summary of Data Flows
1. **Audio**: Browser `Base64` → FastAPI WebSocket `realtimeInput` → Gemini.
2. **Brain**: Gemini outputs Tool Call `advance_stage` → FastAPI traps it → LangGraph processes state transition.
3. **Control**: FastAPI forces Gemini into new context via `clientContent` injection.
4. **UI Updates**: FastAPI pushes custom `ui_update` JSON back to the Browser, causing Next.js to dynamically render the `code_editor`.


Since you are building this as a **single-user demo app** (likely for a presentation, portfolio, or hackathon), your priorities completely shift. You don't need massive scalability or complex task queues. 

Instead, you must optimize for **reliability during a live demo, speed of development, and the "wow" factor (low latency and seamless UI sync).**

Here are the critical design choices, simplifications, and valuable code snippets specifically tailored for a killer demo.

---

### 🔑 1. Crucial Design Choices for a Demo

**A. Drop Redis and Databases; Use In-Memory State**
Setting up Redis and PostgreSQL for a single-user demo is unnecessary overhead. Use LangGraph’s built-in `MemorySaver` and simple Python global dictionaries to hold the resume parsed data. It disappears when the server restarts, which is exactly what you want for a repeatable demo.

**B. Timebox the Interview (The "Demo Mode" Prompt)**
A real technical interview takes 45 minutes. A live demo needs to show the whole system (Intro -> Projects -> Code -> Report) in **under 5 minutes**. 
*Design Choice:* Hardcode a strict rule in your System Prompt: *"Ask ONLY ONE question per stage. The user will answer. Acknowledge their answer in 1 sentence, then IMMEDIATELY call the `advance_stage` tool."*

**C. Drop Local Docker/SQL Run-times; Use "LLM-as-a-Judge"**
Running code in Docker/DuckDB during a live demo can crash or hang. Instead, when the user types code in the frontend Monaco editor, send the code to a background Gemini API call to *simulate* execution and grade it. It’s faster, 100% reliable, and impressive enough for a demo.

**D. Handle "Barge-In" (Interruptions)**
The "Wow" factor of voice AI is when you can interrupt it. If the AI is talking and the user says "Wait, let me explain," the AI should stop talking. Gemini's Live API supports this on the server, but your **frontend needs a way to flush the audio queue**.

---

### 💻 2. Valuable Code Snippets

#### Snippet A: Frontend Audio Queue & Barge-In Handling (React/Next.js)
When Gemini sends audio chunks, they arrive faster than they play. You must queue them. If the user interrupts, you must clear this queue instantly so the AI "shuts up."

```javascript
// frontend: useAudioPlayer.ts (Custom Hook)
import { useRef } from 'react';

export function useAudioPlayer() {
  const audioContext = useRef(new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 }));
  const nextPlayTime = useRef(0);
  const sourceNodes = useRef([]); // Track active audio nodes

  const playChunk = (base64Audio) => {
    // 1. Decode base64 to binary
    const binaryString = window.atob(base64Audio);
    const len = binaryString.length;
    const bytes = new Uint8Array(len);
    for (let i = 0; i < len; i++) { bytes[i] = binaryString.charCodeAt(i); }
    
    // 2. Convert to Float32Array (PCM 16-bit to Float32)
    const int16Array = new Int16Array(bytes.buffer);
    const float32Array = new Float32Array(int16Array.length);
    for (let i = 0; i < int16Array.length; i++) {
      float32Array[i] = int16Array[i] / 32768.0;
    }

    // 3. Create Audio Buffer
    const buffer = audioContext.current.createBuffer(1, float32Array.length, 24000);
    buffer.getChannelData(0).set(float32Array);

    // 4. Schedule playback
    const source = audioContext.current.createBufferSource();
    source.buffer = buffer;
    source.connect(audioContext.current.destination);
    
    const currentTime = audioContext.current.currentTime;
    if (nextPlayTime.current < currentTime) { nextPlayTime.current = currentTime; }
    
    source.start(nextPlayTime.current);
    nextPlayTime.current += buffer.duration;
    
    // Keep track of the node so we can stop it if user interrupts
    sourceNodes.current.push(source);
  };

  const stopAllAudio = () => {
    // BARGE-IN: User spoke. Kill all playing and queued audio!
    sourceNodes.current.forEach(node => {
      try { node.stop(); } catch (e) {}
    });
    sourceNodes.current =[];
    nextPlayTime.current = 0;
  };

  return { playChunk, stopAllAudio };
}
```
*How to use:* When the Gemini WebSocket sends a `serverContent.interrupted` message (or your mic detects speech volume over a threshold), immediately call `stopAllAudio()`.

#### Snippet B: LangGraph In-Memory State for the Backend
Skip Redis. Use this native LangGraph setup for your backend orchestration.

```python
# backend: graph.py
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from typing import TypedDict

class InterviewState(TypedDict):
    stage: str
    feedback: list[str] # Store feedback to generate the final report

def intro_node(state):
    return {"stage": "experience"}

def experience_node(state):
    return {"stage": "dsa"}

def dsa_node(state):
    return {"stage": "report"}

# Build Graph
workflow = StateGraph(InterviewState)
workflow.add_node("intro", intro_node)
workflow.add_node("experience", experience_node)
workflow.add_node("dsa", dsa_node)

workflow.add_edge(START, "intro")
workflow.add_edge("intro", "experience")
workflow.add_edge("experience", "dsa")
workflow.add_edge("dsa", END)

# USE MEMORY SAVER FOR DEMO (Persists state in RAM per session_id)
memory = MemorySaver()
app = workflow.compile(checkpointer=memory)

# Usage in FastAPI:
# new_state = app.invoke({"stage": "intro"}, config={"configurable": {"thread_id": "demo_user_1"}})
```

#### Snippet C: LLM-as-a-Judge for Code Evaluation (Safe Demo Method)
Instead of risking a Judge0 API timeout during a presentation, run a LangChain task that asks Gemini 1.5 Flash to grade the user's code quickly.

```python
# backend: evaluator.py
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field

class CodeEvaluation(BaseModel):
    score: int = Field(description="Score out of 10")
    feedback: str = Field(description="1 sentence of feedback on time complexity")
    is_correct: bool = Field(description="Does this solve the problem?")

def grade_dsa_code_for_demo(problem_description: str, user_code: str):
    llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", temperature=0)
    
    prompt = PromptTemplate.from_template(
        "You are an expert interviewer. The problem is: {problem}.\n"
        "The candidate wrote this code:\n{code}\n"
        "Evaluate it. Be generous as this is a demo."
    )
    
    # Use Structured Output
    structured_llm = llm.with_structured_output(CodeEvaluation)
    chain = prompt | structured_llm
    
    result = chain.invoke({"problem": problem_description, "code": user_code})
    return result
```

---

### 🎙️ 3. Handling the "Agent Speaking Before UI Mounts" Issue
**A common demo failure:** The AI says "Alright, let's write some code. Look at the editor," but the WebSocket takes 500ms to tell React to mount the Monaco editor. The UI feels lagging.

**The Fix:** 
Let the frontend dictate the timing, not the AI.
1. When LangGraph decides to change the stage to `DSA`, it sends the `ui_update` JSON to React **first**.
2. React mounts the Monaco Code Editor.
3. Once the `<Editor />` component fires its `onMount` or `useEffect` hook, the frontend sends a silent message back to the backend: `{"ui_ready": "dsa"}`.
4. ONLY THEN does the backend inject the prompt into Gemini: *"The code editor is now visible. Greet the user and explain the Two-Sum problem."*

This guarantees the AI never references a UI element that hasn't appeared on screen yet.

---

Here is the updated, highly detailed architecture diagram and a strictly timeboxed 5-minute user flow designed specifically for a live demo. 

Since a live demo requires zero latency and absolute reliability, this architecture emphasizes **in-memory state**, **LLM-as-a-judge for instant grading**, and **perfectly synced UI transitions**.

---

### 🏛️ 1. Updated Demo Architecture Diagram

```text
┌───────────────────────────────────────────────────────────────────────────────┐
│                          FRONTEND (Next.js / React)                           │
│                                                                               │
│  ┌───────────────┐ ┌───────────────────────────────────────────────────────┐  │
│  │ Audio Engine  │ │                  Dynamic UI Engine                    │  │
│  │ • Mic Capture │ │ ┌────────────┐ ┌──────────────┐ ┌───────────────────┐ │  │
│  │ • PCM 16kHz   │ │ │ Resume UI  │ │ Monaco Code  │ │ Final Report UI   │ │  │
│  │ • Audio Queue │ │ │ (Cards)    │ │ Editor (DSA) │ │ (Recharts Radar)  │ │  │
│  │ • Barge-in    │ │ └────────────┘ └──────────────┘ └───────────────────┘ │  │
│  └──────┬─▲──────┘ └──────────────────────────▲─┬──────────────────────────┘  │
└─────────│─│───────────────────────────────────│─│─────────────────────────────┘
          │ │ Audio (WS)                        │ │ JSON Control Signals (WS)
          ▼ │                                   │ ▼ 
┌─────────┼─┼───────────────────────────────────┼─┼─────────────────────────────┐
│         │ │         BACKEND (FastAPI / Python)│ │                             │
│  ┌──────▼─┴───────────────────────────────────┴─▼───────┐                     │
│  │                  WEBSOCKET PROXY                     │                     │
│  │  • Routes Audio chunks directly to Gemini            │                     │
│  │  • Intercepts Tool Calls & JSON UI signals           │                     │
│  └──────┬─▲───────────────────────────────────┬─▲───────┘                     │
│         │ │                                   │ │                             │
│   Audio │ │ Audio                             │ │ Triggers State Change       │
│         ▼ │                                   ▼ │                             │
│  ┌────────┴─────────────────┐      ┌────────────┴──────────────────────────┐  │
│  │   EXTERNAL AI (Google)   │      │      LANGGRAPH (The Orchestrator)     │  │
│  │                          │      │                                       │  │
│  │  ┌────────────────────┐  │      │[MemorySaver - In-Memory State]      │  │
│  │  │ Gemini Multimodal  │  │      │   1. Intro Node                       │  │
│  │  │ Live API (v1beta)  │  │      │   2. Experience Node                  │  │
│  │  │ • Persistent WS    │  │      │   3. DSA Node                         │  │
│  │  │ • Voice & Text     │  │      │   4. Report Node                      │  │
│  │  └────────────────────┘  │      │                                       │  │
│  └──────────────────────────┘      └────────────┬──────────────────────────┘  │
│                                                 │ Async Calls                 │
│                                                 ▼                             │
│                                    ┌───────────────────────────────────────┐  │
│                                    │  LANGCHAIN (Background Tasks)         │  │
│                                    │  • Gemini 1.5 Flash (Fast API)        │  │
│                                    │  • Task 1: Parse PDF -> JSON          │  │
│                                    │  • Task 2: Grade Code (LLM-as-Judge)  │  │
│                                    │  • Task 3: Generate Radar Chart       │  │
│                                    └───────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────────────┘
```

#### **Key Components for Demo Reliability:**
*   **Audio Engine (Frontend):** Handles raw PCM audio. Includes a "Barge-in" function that instantly flushes the playback queue if the user interrupts.
*   **WebSocket Proxy (FastAPI):** A single WebSocket connection to the frontend that carries *both* base64 audio and JSON UI control signals.
*   **LangGraph + MemorySaver:** Replaces Redis/Databases. State is held in RAM during the demo.
*   **LangChain Background Tasks:** Uses Gemini 1.5 Flash (via standard HTTP, not Live API) to instantly grade code and parse the resume.

---

### ⏱️ 2. The 5-Minute "Wow-Factor" User Flow

This flow is heavily time-boxed. The AI is explicitly prompted to ask **only one question per section** to keep the demo moving rapidly.

#### **Minute 0:00 - 0:45 | The Setup & Magic Parse**
1. **Action:** User opens the app and uploads a PDF Resume.
2. **Background:** LangChain instantly extracts the user's name, top skill, and 1 main project into JSON.
3. **UI Update:** The screen transitions to the "Interview Room". An abstract 3D orb/visualizer appears representing "Raven".

#### **Minute 0:45 - 2:00 | Voice Intro & Experience**
1. **Action:** User clicks "Start Interview" (Microphone connects).
2. **AI Action:** Raven speaks first: *"Hi [Name], I'm Raven. I see you built[Project Name] using [Skill]. Could you briefly tell me the biggest challenge you faced building that?"*
3. **User Action:** User explains their project for 30 seconds.
4. **AI Action:** Raven acknowledges naturally: *"That's a smart way to handle that. Let's move on to a quick technical assessment."*
5. **Trigger:** The AI calls the `advance_stage` tool.

#### **Minute 2:00 - 3:30 | The Dynamic UI & DSA Sync**
1. **LangGraph Action:** LangGraph transitions state to `dsa` node.
2. **UI Update:** FastAPI pushes a JSON signal. The screen splits instantly—the avatar shrinks to the corner, and a slick **Monaco Code Editor** mounts on the right side.
3. **Sync Trick:** The React frontend fires back a `{"ui_ready": "dsa"}` signal.
4. **AI Action:** *Only now* does Raven speak: *"Alright, you should see the code editor now. Let's do a simple Two-Sum problem. Can you write a Python function for this?"*
5. **User Action:** User types the solution while narrating their thought process. 

#### **Minute 3:30 - 4:30 | Instant Grading (LLM-as-a-Judge)**
1. **Action:** User clicks "Run Code" or says "I'm done."
2. **Background:** FastAPI grabs the code and sends it to LangChain (Gemini 1.5 Flash). It evaluates logic and time complexity in < 2 seconds.
3. **AI Action:** FastAPI injects the hidden grade into Raven's context. Raven speaks: *"Great job. Your logic is solid, and I noticed you achieved O(n) time complexity by using a hash map. Well done."*
4. **Trigger:** The AI calls `end_interview`.

#### **Minute 4:30 - 5:00 | The Grand Finale (Report Generation)**
1. **LangGraph Action:** Transitions to `report` node. Generates summary feedback.
2. **UI Update:** The Code editor vanishes. A beautiful animated **Radar Chart** (built with Recharts) appears, scoring the candidate on: *Communication, Code Logic, Resume Alignment, and Confidence*.
3. **AI Action:** Raven says: *"Thanks for your time! Your final report is up on the screen. Have a great day!"*
4. **End of Demo.**

---

### 🔄 3. Sequence Diagram: The UI-Sync Trick
*This is the most critical flow to make the demo feel like magic. If the AI talks about the code editor before it appears, the illusion breaks.*

```text
User/React                  FastAPI (LangGraph)           Gemini (Live API)
    │                               │                             │
    │[User finishes talking]      │                             │
    │──────────────────────────────>│                             │
    │                               │──────> [Audio Chunk] ──────>│
    │                               │                             │
    │                               │<──[Tool: advance_stage] ───│
    │                               │                             │
    │<── {"type": "ui_code_editor"}─│ (Pause Audio Forwarding)    │
    │                               │                             │
 [React mounts Monaco Editor]       │                             │
    │                               │                             │
    │─── {"ui_ready": "dsa"} ──────>│                             │
    │                               │                             │
    │                               │──────> [System Command] ───>│
    │                               │  "UI is ready. Greet user   │
    │                               │   and explain Two-Sum"      │
    │                               │                             │
    │                               │<────[Audio Response] ──────│
    │<─── [Audio: "Alright, you..."]│                             │
```

### 💡 Why this architecture guarantees a flawless demo:
1. **No Docker/Judge0 bottlenecks:** Code evaluation is done via LLM (Gemini 1.5 Flash), which is practically instant and won't crash if the user misses a semicolon.
2. **State is ephemeral:** MemorySaver ensures that if you mess up a demo run, you just refresh the page and restart the FastAPI server, and it's a completely clean slate.
3. **Strict AI Guardrails:** By injecting hidden system commands (`[SYSTEM INSTRUCTION: Acknowledge the answer and immediately call advance_stage]`), the AI will not ramble or get stuck in an endless loop of follow-up questions.

---

## 🛠️ May 2026 SDK Implementation Details

### Native Audio & Vertex AI Integration
To leverage **GCP Credits** and ensure high-fidelity voice interaction with the `gemini-live-2.5-flash-native-audio` model:
- **Initialization**: Use `genai.Client(vertexai=True, project=project_id)`.
- **Streaming**: Use `session.send(input=chunk)` for 16kHz PCM bytes.
- **Barge-in**: Listen for `message.server_content.interrupted` to immediately flush frontend buffers.

### Future Phase Breakdown

| Component | Phase 1 (MVP) | Phase 2 (Technical Interview) |
| :--- | :--- | :--- |
| **State** | Hardcoded Node Transitions | LangGraph Dynamic Pathing |
| **Context** | Fixed System Prompt | Summarize & Swap (Sliding Window) |
| **Grading** | Transcription logging | LLM-as-a-Judge for DSA/SQL |
| **UI** | Basic Transcript View | Monaco Editor + Radar Charts |

### Critical "UI-Ready" Signal Pattern
To avoid the AI speaking about a code editor before it appears, the system follows a **Handshake Protocol**:
1. Frontend sends `{"ui_ready": "node_name"}` once the component mounts.
2. Backend intercepts this and calls `inject_context()` to steer the AI turn.