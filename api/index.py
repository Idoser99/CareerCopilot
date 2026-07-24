from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()


@app.get("/ping")
def ping():
    return "pong"


@app.get("/api/team_info")
def team_info():
    return {
        "group_batch_order_number": "1_{order#}",
        "team_name": "Ido & Yarden",
        "students": [
            {"name": "Ido Oserovitz", "email": "idoser99@gmail.com"},
            {"name": "Yarden", "email": "yarden@gmail.com"}
        ]
    }


@app.get("/api/agent_info")
def agent_info():
    return {
        "description": "…",
        "purpose": "…",
        "prompt_template": {
            "template": "…"
        },
        "prompt_examples": [
            {
                "prompt": "Example prompt 1…",
                "full_response": "Full response your agent returns…",
                "steps": ["step1", "step2"]
            },
            {
                "prompt": "Example prompt 2…",
                "full_response": "Full response your agent returns…",
                "steps": ["step3", "step4"]
            }
        ]
    }


@app.get("/api/model_architecture", response_class=FileResponse)
def agent_architecture():
    return FileResponse("resources/architecture.png", media_type="image/png")


@app.post("/api/execute")
def execute(request: Request):
    return {
        "status": "ok",
        "error": None,
        "response": "CareerCopilot response",
        "steps": [
            {
                "module": "tailor CV",
                "prompt": {},
                "response": {},
            },
            {
                "module": "submit application",
                "prompt": {},
                "response": {},
            }
        ]
    }
