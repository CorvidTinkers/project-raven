# Project Raven: MVP Implementation Plan

The objective of the MVP is to establish a **low-latency, bi-directional voice proxy** between a Next.js 16 frontend and the Gemini Multimodal Live API via a FastAPI backend.

## 🏛️ Architecture Overview

```text
[Browser] <--- WebSocket (JSON/PCM) ---> [FastAPI] <--- WebSocket (Live SDK) ---> [Gemini Live API]
```

- **Frontend**: Next.js 16 (App Router) + TypeScript + Tailwind CSS.
- **Backend**: FastAPI + `websockets` + `google-genai` SDK.
- **State**: Ephemeral (In-memory for the MVP).

---

## 🛠️ Technical Specifications

### 1. Backend (FastAPI & Gemini SDK)
We will leverage the pattern from `gemini-live-genai-python-sdk` for the core connection.

#### **Gemini Service (`backend/services/gemini.py`)**
```python
class GeminiLive:
    def __init__(self, api_key, model, input_sample_rate):
        self.client = genai.Client(api_key=api_key)
        # Setup speech config with voice "Puck" or "Charon"
    
    async def start_session(self, audio_input_queue, audio_output_callback):
        async with self.client.aio.live.connect(model=self.model, config=config) as session:
            # Task 1: send_audio (queue -> Gemini)
            # Task 2: receive_loop (Gemini -> audio_output_callback)
            # Handle tool_calls & interruptions
```

#### **Audio Utils (`backend/services/audio.py`)**
- `convert_float32_to_int16`: For browser-to-Gemini (16kHz).
- `encode_base64_pcm`: For sending audio chunks to the client.

### 2. Frontend (Next.js 16 & Web Audio)
We will implement a custom audio engine to handle the real-time stream.

#### **Audio Hook (`frontend/hooks/useAudio.ts`)**
- **Capture**: Uses `AudioContext` to sample at 16kHz.
- **Playback**: Uses a `nextPlayTime` scheduler to queue 24kHz chunks.
- **Barge-in**: Clears all `sourceNodes` immediately when an `interrupted` event is received.

#### **WebSocket Hook (`frontend/hooks/useWebSocket.ts`)**
- Manages connection lifecycle with exponential backoff.
- Handles both `binary` (audio) and `json` (transcripts/events) messages.

---

## 🎨 UI Requirements
- **Connect Button**: Explicitly starts/stops the WebSocket and AudioContext.
- **Mic Toggle**: Mute/Unmute local microphone input.
- **Speaker Toggle**: Mute/Unmute AI's voice output (Hear/Silent).
- **Volume Visualizer**: Real-time feedback for both user and AI volume levels.

---

## 📅 Implementation Roadmap

### Phase 1: Environment & Scaffolding
- [ ] Initialize Next.js 16 project in `frontend/`.
- [ ] Install backend dependencies (`fastapi`, `uvicorn`, `websockets`, `google-genai`).
- [ ] Configure `.env` with `GEMINI_API_KEY`.

### Phase 2: Backend MVP (The Proxy)
- [ ] Implement `backend/services/audio.py`.
- [ ] Implement `backend/services/gemini.py` (SDK Wrapper).
- [ ] Implement `backend/api/websocket.py` (The Proxy Loop).

### Phase 3: Frontend MVP (The Voice)
- [ ] Implement `useAudio.ts` hook for capture/playback.
- [ ] Implement `useWebSocket.ts` for communication.
- [ ] Build the UI in `frontend/app/page.tsx` (Connect, Mic, Speaker controls).

### Phase 4: Manual Verification
- [ ] Test real-time conversation latency.
- [ ] Verify "Barge-in" (AI stops when user speaks).
- [ ] Verify Mic/Speaker muting works as expected.

---

## ⚠️ Known Challenges
1. **Sample Rate Mismatch**: Gemini expects 16kHz in and 24kHz out. The **Frontend** will handle all resampling natively using the Web Audio API to minimize backend CPU load and latency.
2. **Audio Buffer Jitter**: We will implement a small "jitter buffer" in the playback queue.
