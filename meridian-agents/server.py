# meridian-agents/server.py - Agents Service API
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from graph.trading_graph import TradingAgentsGraph
import uvicorn
import os
import traceback

app = FastAPI(title="Meridian Agents API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request models
class AnalyzeRequest(BaseModel):
    company_name: str
    trade_date: str

# Initialize the graph (lazy load)
_graph_instance = None

def get_graph():
    global _graph_instance
    if _graph_instance is None:
        try:
            _graph_instance = TradingAgentsGraph()
        except Exception as e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to initialize TradingAgentsGraph: {str(e)}\n{traceback.format_exc()}"
            )
    return _graph_instance

@app.get("/health")
async def health():
    try:
        # Try to get graph to verify initialization works
        graph = get_graph()
        return {"status": "ok", "service": "meridian-agents", "graph_initialized": True}
    except Exception as e:
        return {
            "status": "error",
            "service": "meridian-agents",
            "error": str(e),
            "graph_initialized": False
        }

@app.post("/analyze")
async def analyze(request: AnalyzeRequest):
    try:
        graph = get_graph()
        final_state, decision = graph.propagate(request.company_name, request.trade_date)
        return {
            "company": request.company_name,
            "date": request.trade_date,
            "decision": decision,
            "state": final_state
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Analysis failed: {str(e)}\n{traceback.format_exc()}"
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8001))
    uvicorn.run(app, host="0.0.0.0", port=port)