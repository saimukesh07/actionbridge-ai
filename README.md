# ActionBridge AI

> **"Bridge the gap between what people want to achieve and what they actually execute."**

ActionBridge AI is an intelligent strategy-making and verified execution platform. It transforms natural language goals into rigorous strategic analyses, actionable phased roadmaps, human-gated tool executions, and independently verified outcomes.

---

## 🌟 Core Features

1. **📹 YouTube Video to Actionable Strategy (New!)**: Paste any YouTube tutorial, tech talk, business breakdown, or lecture URL. ActionBridge AI automatically inspects the video metadata, transcribes closed captions, conducts a 4-question adaptive diagnostic interview based on the video's concepts, and generates an execution roadmap.
2. **🎙️ Dynamic Adaptive Interview**: Discovers hidden constraints, technical baselines, and success criteria through tailored follow-up questions for any custom goal.
3. **Strategic Reasoning Engine**: Uses Multi-Provider AI (Groq + Gemini with local fallback) to break down problem definitions, root causes, assumptions, and compare multiple strategic approaches with feasibility/impact scores.
4. **Action Plan Generator**: Converts the chosen strategy into prioritized, phased tasks with dependencies, estimated durations, and assigned execution tools.
5. **Controlled Tool Execution & Human Gatekeeper**: Restricts filesystem operations to an isolated `workspace/` sandbox. Automatically quarantines consequential actions behind mandatory human approval.
6. **Independent Post-Condition Verification**: Empirically audits physical file presence, SHA256 content checksums, and arithmetic invariants on disk. Never trusts an LLM's claim of completion without evidence.
7. **Strategy Persistence & Switching**: Automatically archives formulated strategies with progress tracking, allowing seamless switching across previous projects.

---

## 🚀 Quickstart Guide (Windows)

### 1. Open Terminal & Navigate to Project
Open Windows PowerShell or Command Prompt:
```powershell
cd C:\Users\saimu\actionbridge-ai
```

### 2. Configure Environment (Optional)
Copy `.env.example` to `.env`:
```powershell
Copy-Item .env.example .env
```
Add your free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey):
```env
GEMINI_API_KEY=your_gemini_api_key_here
GEMINI_MODEL=gemini-2.5-flash
```
*(Note: If you do not have an API key, ActionBridge AI automatically runs in a deterministic local demo mode so you can test all features offline!)*

### 3. Run the Automated Tests
```powershell
python tests/test_core.py
```

### 4. Launch the Streamlit Dashboard
```powershell
streamlit run app.py
```
Open **[http://localhost:8501](http://localhost:8501)** in your web browser.

---

## 📁 Project Architecture

```
actionbridge-ai/
├── app.py                     # Streamlit multi-page frontend & navigation
├── config/
│   └── settings.py            # Environment loading & workspace sandbox paths
├── core/
│   ├── schemas.py             # Pydantic models (Goal, Strategy, Plan, Task, Risk)
│   └── gemini_client.py       # Google GenAI client with offline fallback engine
├── tools/
│   ├── registry.py            # Controlled tool whitelist & workspace containment
│   └── verification.py        # Independent physical verification & SHA256 auditing
├── workspace/                 # Sandboxed directory for generated deliverables
└── tests/
    └── test_core.py           # Automated test suite
```
