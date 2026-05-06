# Google GenAI Package Research: Multimodal Live API & Orchestration

This document provides a detailed breakdown of the `google-genai` (New) and `google-generativeai` (Legacy) Python SDKs, specifically focusing on real-time orchestration and state injection for Project Raven.

---

## 1. SDK Comparison: Legacy vs. New

### **Google Generative AI (`google-generativeai`) - DEPRECATED for Live API**
*   **Version**: 0.x
*   **Import**: `import google.generativeai as genai`
*   **Architecture**: Model-centric (`genai.GenerativeModel`).
*   **Real-time Support**: Limited. Uses `start_chat()` or `generate_content(stream=True)`.
*   **Live API**: Introduced as a late addition but lacks the robust type-safety and session management of the newer SDK.

### **Google GenAI (`google-genai`) - RECOMMENDED**
*   **Version**: 1.x+
*   **Import**: `from google import genai`
*   **Architecture**: Client-centric (`genai.Client`).
*   **Unified Interface**: Supports both Gemini Developer API (AI Studio) and Vertex AI (GCP) with the same code.
*   **Live API**: Native support via `client.aio.live.connect()`.

---

## 2. Multimodal Live API: Core Implementation

The `google-genai` SDK uses an asynchronous WebSocket-based session to handle continuous audio/video/text streams.

### **Session Initialization**
```python
from google import genai
from google.genai import types

client = genai.Client(api_key="YOUR_API_KEY", http_options={'api_version': 'v1alpha'})

async with client.aio.live.connect(model="gemini-2.0-flash-exp", config=config) as session:
    # Interaction loop here
```

### **Session Configuration (`LiveConnectConfig`)**
Used to set initial state:
*   `system_instruction`: The primary persona/instructions.
*   `tools`: List of tool definitions (functions).
*   `tool_config`: Configuration for tool execution (e.g., function calling mode).
*   `speech_config`: Voice selection (e.g., "Puck", "Charon") and VAD settings.

---

## 3. State Injection & Orchestration

State injection allows you to "steer" the AI mid-session or inject background context from LangGraph without restarting the WebSocket.

### **Method A: `session_update` (Hard Steer)**
Updates the core configuration of the session. Useful for transitioning between interview phases (e.g., Intro -> DSA).

*   **How it works**: Send a `SessionUpdate` message via `session.send`.
*   **Effect**: Updates the `system_instruction` and available `tools` for all subsequent turns.
*   **Command**:
    ```python
    await session.send(
        input=types.LiveClientMessage(
            session_update=types.SessionUpdate(
                system_instruction="You are now in the DSA phase. Ask a Two-Sum problem.",
                tools=[types.Tool(function_declarations=[...])]
            )
        )
    )
    ```

### **Method B: `client_content` (Soft Steer/Injection)**
Injects conversation history or hidden instructions as if they were a user turn.

*   **How it works**: Send a `ClientContent` message.
*   **Effect**: Adds text/media to the conversation history. If `turn_complete=True`, the model responds immediately.
*   **Command**:
    ```python
    await session.send(
        input=types.LiveClientMessage(
            client_content=types.ClientContent(
                turns=[types.Content(role="user", parts=[types.Part(text="[SYSTEM]: Candidate uploaded a resume. Context updated.")])],
                turn_complete=False  # Do not trigger a spoken response yet
            )
        )
    )
    ```

---

## 4. Orchestration Hooks & Tool Calls

To bridge the Live API with **LangGraph**, we use Tool Calls as triggers.

### **The `advance_stage` Tool**
1.  Define a tool in the `LiveConnectConfig`.
2.  When the model decides a phase is over, it emits a `ToolCall`.
3.  The backend catches the `ToolCall`, advances the LangGraph state, and sends a `session_update` back to the model with the new phase's instructions.

### **Handling Responses**
```python
async for message in session.receive():
    if message.tool_call:
        for call in message.tool_call.function_calls:
            if call.name == "advance_stage":
                # 1. Update LangGraph State
                # 2. Perform Session Update
                await session.send(types.LiveClientMessage(tool_response=...))
    
    if message.server_content:
        # Forward audio to frontend
```

---

## 5. Required Functionalities for Project Raven

| Feature | `google-genai` Class/Method | Implementation Note |
| :--- | :--- | :--- |
| **Connection** | `client.aio.live.connect` | Must use `aio` for non-blocking WebSocket. |
| **Barge-in** | `server_content.interrupted` | Backend must detect this and notify frontend to flush buffers. |
| **Phase Change** | `types.SessionUpdate` | Cleanest way to swap system prompts mid-interview. |
| **Context Injection** | `types.ClientContent` | Best for injecting "thought" or resume facts without AI speaking them. |
| **Function Calling** | `types.Tool` | Essential for `advance_stage` and `run_code` triggers. |

---

## 💡 Engineering Recommendation
Use **`google-genai` v1.x**. 
Avoid using `google-generativeai` for the WebSocket logic as the type definitions for `LiveClientMessage` and `ServerContent` are much more robust and future-proof in the new SDK. 
