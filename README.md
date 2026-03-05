# GUNA-ASTRA
### Local Autonomous Multi-Agent AI System

> Powered by **Ollama (Llama3)** + **MongoDB** | Built in Python

---

## What is GUNA-ASTRA?

GUNA-ASTRA is a personal autonomous AI assistant that works like a company:

- **You = CEO** — give high-level goals in plain English
- **GUNA-ASTRA = Manager** — plans and coordinates all work
- **11 Agents = Employees** — each specialized in a domain

---

## System Architecture

```
You (User)
    ↓
GUNA-ASTRA Orchestrator
    ↓
Planner Agent       ← breaks goal into tasks
    ↓
Task Dispatcher     ← routes tasks to agents
    ↓
┌─────────────────────────────────────┐
│  ResearchAgent   CodingAgent        │
│  SystemAgent     DataAgent          │
│  CyberAgent      MemoryAgent        │
└─────────────────────────────────────┘
    ↓
Testing Agent       ← tests any code
    ↓
Verification Agent  ← safety + correctness check
    ↓
Result Synthesizer  ← final clean response
    ↓
You (User)
```

---

## The 11 Agents

| # | Agent | Role |
|---|-------|------|
| 1 | PlannerAgent | Breaks goals into ordered tasks |
| 2 | TaskDispatcher | Routes tasks to correct agents |
| 3 | MemoryAgent | MongoDB read/write |
| 4 | ResearchAgent | Internet research + summarization |
| 5 | CodingAgent | Writes and debugs Python code |
| 6 | SystemAgent | OS commands, files, browser, YouTube |
| 7 | DataAgent | Data analysis and visualization |
| 8 | CyberAgent | Security concepts and code review |
| 9 | TestingAgent | Tests generated scripts |
| 10 | VerificationAgent | Quality and safety checking |
| 11 | ResultSynthesizer | Final user-facing response |

---

## Setup Instructions

### Step 1: Install Python dependencies

```bash
cd GUNA-ASTRA
pip install -r requirements.txt
```

### Step 2: Install and start Ollama

Download from https://ollama.ai then run:

```bash
ollama pull llama3
ollama serve
```

### Step 3: Install MongoDB (optional but recommended)

Download from https://www.mongodb.com/try/download/community

If MongoDB is not installed, GUNA-ASTRA automatically uses in-memory storage.

### Step 4: Run GUNA-ASTRA

```bash
python main.py
```

---

## Example Goals

```
Play some relaxing jazz music on YouTube
Write a Python script that generates prime numbers
Create a PowerPoint presentation on climate change
Analyze this dataset: [paste CSV data]
Check this code for security vulnerabilities: [paste code]
Draft an email to my professor saying I'm sick today
Open Google and search for machine learning tutorials
```

---

## Safety Features

- **Dangerous actions** (deleting files, sending emails, running scripts) require your explicit confirmation
- **Max 10 task iterations** per goal to prevent infinite loops
- **60-second timeout** per task
- **Verification Agent** checks every output before it reaches you
- Agents **cannot modify** the orchestrator or planner

---

## Commands

| Command | Action |
|---------|--------|
| `history` | Show recent tasks |
| `status` | Check Ollama + MongoDB status |
| `help` | Show usage guide |
| `clear` | Clear screen |
| `exit` | Quit the system |

---

## File Structure

```
GUNA-ASTRA/
├── main.py                    ← Entry point
├── requirements.txt
├── config/
│   └── settings.py            ← All configuration
├── core/
│   └── orchestrator.py        ← Main controller
├── agents/
│   ├── base_agent.py          ← Base class
│   ├── planner_agent.py
│   ├── task_dispatcher.py
│   ├── memory_agent.py
│   ├── research_agent.py
│   ├── coding_agent.py
│   ├── system_agent.py
│   ├── data_agent.py
│   ├── cyber_agent.py
│   ├── testing_agent.py
│   ├── verification_agent.py
│   └── result_synthesizer.py
├── utils/
│   ├── llm_client.py          ← Ollama API wrapper
│   ├── memory_db.py           ← MongoDB interface
│   ├── logger.py              ← Colored logging
│   └── banner.py              ← Startup banner
└── logs/                      ← Auto-created log files
```

---

## Troubleshooting

**"Ollama is not running"**
→ Run `ollama serve` in a separate terminal

**"MongoDB unavailable"**
→ Normal — system uses in-memory storage automatically

**Agent returns ERROR**
→ Check that `llama3` model is pulled: `ollama list`

---

*GUNA-ASTRA — Your personal AI command center.*
