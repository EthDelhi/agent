from fastapi import FastAPI
from pydantic import BaseModel
from commits import HackathonAnalyzer
from fastapi import HTTPException
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class RepoRequest(BaseModel):
    url: str
    start_date: str
    end_date: str

@app.post("/analyze")
def analyze_repo(request: RepoRequest):
    analyzer = HackathonAnalyzer(
        hackathon_start=request.start_date,
        hackathon_end=request.end_date
    )
    return analyzer.analyze_repository(request.url)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
