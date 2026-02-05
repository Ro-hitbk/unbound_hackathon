# 🔄 Veriflow - Agentic Workflow Builder

An agentic workflow builder that chains AI agents together to automate complex multi-step tasks. Built for the Unbound Hackathon.

![Veriflow](https://img.shields.io/badge/Veriflow-Agentic%20Workflows-blue)
![Python](https://img.shields.io/badge/Python-3.11+-green)
![React](https://img.shields.io/badge/React-19-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-Latest-teal)

## ✨ Features

### Core Features
- **Multi-Step Workflows** - Create workflows with multiple LLM-powered steps
- **Context Passing** - Output from each step flows to the next as context
- **Completion Criteria** - Define success criteria that the AI evaluates
- **Model Selection** - Choose from available models (kimi-k2p5, kimi-k2-instruct-0905)
- **Real-time Execution** - Watch your workflow execute step by step

### Bonus Features
- **💰 Cost Tracking** - Track token usage and estimated costs per step/execution
- **📥 Export/Import** - Save and share workflows as JSON files
- **🤖 Auto Model Selection** - Automatically picks the best model based on task type

### Additional Features
- **🔄 Retry Logic** - Automatic retry with exponential backoff for network reliability
- **📊 Token Usage Display** - See prompt/completion tokens per step
- **📱 Responsive Design** - Works on desktop and mobile

## 🛠️ Tech Stack

### Backend
| Technology | Purpose |
|------------|---------|
| **FastAPI** | Modern Python web framework |
| **SQLAlchemy** | ORM for database operations |
| **MySQL / SQLite** | Database (MySQL local, SQLite production) |
| **Unbound API** | LLM integration |
| **Pydantic** | Data validation |

### Frontend
| Technology | Purpose |
|------------|---------|
| **React 19** | UI library |
| **Vite** | Build tool and dev server |
| **Axios** | HTTP client |

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- MySQL (for local development)

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Run the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run dev server
npm run dev
```

Open http://localhost:5173 in your browser.

### Environment Variables

**Backend** (optional - has defaults for local dev):
| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | Database connection string |
| `UNBOUND_API_KEY` | Your Unbound API key |

**Frontend** (optional - defaults to localhost:8000):
| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL |

## 📖 Usage

1. **Create a Workflow** - Click "New Workflow" and give it a name
2. **Add Steps** - Add LLM steps with prompts and completion criteria
3. **Execute** - Click "Run" to execute the workflow
4. **Monitor** - Watch each step execute and view results
5. **Export** - Save workflows as JSON to share or backup

### Example Workflow: Blog Post Pipeline

```
Step 1: Generate Outline
  Prompt: "Create an outline for a blog post about {topic}"
  Criteria: "Must have at least 5 sections"

Step 2: Write Introduction  
  Prompt: "Write an engaging introduction based on this outline"
  Criteria: "Must be 100-200 words"

Step 3: Polish & Edit
  Prompt: "Improve the writing quality and fix any issues"
  Criteria: "Must be professional and error-free"
```

## 🏗️ Project Structure

```
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI routes
│   │   ├── models.py            # SQLAlchemy models
│   │   ├── schemas.py           # Pydantic schemas
│   │   ├── database.py          # Database config
│   │   ├── unbound_client.py    # Unbound API client
│   │   ├── workflow_executor.py # Execution engine
│   │   └── criteria_checker.py  # Criteria evaluation
│   ├── requirements.txt
│   └── nixpacks.toml            # Railway config
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx              # Main app component
│   │   ├── api.js               # API client
│   │   └── components/
│   │       ├── WorkflowList.jsx
│   │       ├── WorkflowBuilder.jsx
│   │       ├── StepEditor.jsx
│   │       └── ExecutionViewer.jsx
│   ├── package.json
│   └── nixpacks.toml            # Railway config
│
└── README.md
```

## 🌐 Deployment (Railway)

1. Push code to GitHub
2. Create Railway project → Deploy from GitHub
3. Add **Backend** service (Root Directory: `backend`)
   - Set `DATABASE_URL=sqlite` 
   - Set `UNBOUND_API_KEY=your_key`
4. Add **Frontend** service (Root Directory: `frontend`)
   - Set `VITE_API_URL=https://your-backend-url.railway.app`

## 📝 API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/workflows/` | List all workflows |
| POST | `/workflows/` | Create workflow |
| GET | `/workflows/{id}` | Get workflow details |
| PUT | `/workflows/{id}` | Update workflow |
| DELETE | `/workflows/{id}` | Delete workflow |
| POST | `/workflows/{id}/steps/` | Add step to workflow |
| PUT | `/steps/{id}` | Update step |
| DELETE | `/steps/{id}` | Delete step |
| POST | `/workflows/{id}/execute` | Execute workflow |
| GET | `/workflows/{id}/export` | Export as JSON |
| POST | `/workflows/import` | Import from JSON |
| GET | `/executions/{id}` | Get execution details |
| GET | `/models/` | List available models |

## 🎯 Hackathon Requirements

### Basic Requirements ✅
- ✅ Multi-step workflow builder UI
- ✅ LLM step configuration (prompt, model, parameters)
- ✅ Completion criteria per step
- ✅ Workflow execution engine
- ✅ Context passing between steps

### Bonus Challenges ✅
- ✅ **Cost Tracking** - Token usage and cost per step/execution
- ✅ **Workflow Export/Import** - Save and share workflows as JSON
- ✅ **Auto Model Selection** - Picks best model based on task type

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

MIT License - Built for Unbound Hackathon 2026

---

**Built with ❤️ for the Unbound Hackathon**
