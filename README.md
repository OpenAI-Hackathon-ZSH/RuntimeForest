# RuntimeForest

Integration and demo for real-time code instrumentation visualization.

Combines RuntimeSpy (instrumentation library) with BranchFrequencyVisual (visualization UI) to show live execution frequencies.

## Quick Start

### Prerequisites
- Python 3.12+
- Node.js 18+

### Setup

```bash
# Clone dependencies
git clone https://github.com/OpenAI-Hackathon-ZSH/RuntimeSpy.git
git clone https://github.com/OpenAI-Hackathon-ZSH/BranchFrequencyVisual.git

# Install Python dependencies
pip install -r requirements.txt

# Install frontend dependencies
cd BranchFrequencyVisual
npm install
cd ..
```

### Run the Demo

**Terminal 1: Backend API**
```bash
python services/backend/server.py
```

**Terminal 2: Instrumented Mock Service**
```bash
CODE_MANAGER_INSTRUMENT=1 \
CODE_MANAGER_BACKEND_URL=http://127.0.0.1:8000 \
uvicorn services.mock.server:app --host 127.0.0.1 --port 8100
```

**Terminal 3: Workload Generator**
```bash
python run_mock_workload.py --script representative --repeat --interval 2
```

**Terminal 4: Frontend**
```bash
cd BranchFrequencyVisual
npm run dev
```

Then open http://localhost:3000 and click "Live Backend"

## What's Included

- `services/backend/` - FastAPI backend that caches instrumentation data
- `services/mock/` - Example e-commerce service with feature gates
- `run_mock_workload.py` - HTTP workload generator

## Data Flow

```
Workload (HTTP requests)
  ↓
Mock Service (instrumented)
  ↓
Backend (caches frequencies)
  ↓
Frontend (polls every 3s)
  ↓
Browser (displays live updates)
```

## See Also

- [RuntimeSpy](https://github.com/OpenAI-Hackathon-ZSH/RuntimeSpy) - Instrumentation library
- [BranchFrequencyVisual](https://github.com/OpenAI-Hackathon-ZSH/BranchFrequencyVisual) - Visualization UI
