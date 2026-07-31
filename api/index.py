from fastapi import FastAPI
from fastapi.responses import FileResponse
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
from api.schemas import (
    AgentInfoResponse,
    ExecuteRequest,
    ExecuteResponse,
    ExecutionStep,
    PromptExample,
    PromptTemplate,
    Student,
    TeamInfoResponse,
)

load_dotenv()

model_name = os.getenv("OPENAI_MODEL_PREFIX") + "-" + "gpt-5-mini"
llm = ChatOpenAI(model=model_name)

app = FastAPI()


@app.get("/ping")
def ping():
    return "pong"


@app.get("/api/team_info", response_model=TeamInfoResponse)
def team_info() -> TeamInfoResponse:
    return TeamInfoResponse(
        group_batch_order_number="1_{order#}",
        team_name="Ido & Yarden",
        students=[
            Student(name="Ido Oserovitz", email="idoser99@gmail.com"),
            Student(name="Yarden", email="yarden@gmail.com"),
        ],
    )


@app.get("/api/agent_info", response_model=AgentInfoResponse)
def agent_info() -> AgentInfoResponse:
    return AgentInfoResponse(
        description="…",
        purpose="…",
        prompt_template=PromptTemplate(template="…"),
        prompt_examples=[
            PromptExample(
                prompt="Example prompt 1…",
                full_response="Full response your agent returns…",
                steps=[
                    ExecutionStep(
                        module="CV Tailoring",
                        prompt={},
                        response={},
                    )
                ],
            ),
            PromptExample(
                prompt="Example prompt 2…",
                full_response="Full response your agent returns…",
                steps=[
                    ExecutionStep(
                        module="Submit Application",
                        prompt={},
                        response={},
                    )
                ],
            ),
        ],
    )


@app.get("/api/model_architecture", response_class=FileResponse)
def agent_architecture():
    return FileResponse("resources/architecture.png", media_type="image/png")


@app.post("/api/execute", response_model=ExecuteResponse)
def execute(request: ExecuteRequest) -> ExecuteResponse:
    # todo: add augmented prompt
    llm_response = llm.invoke(request.prompt)
    response = llm_response.content
    # todo: check if needed a specific tool - if so reroute to it
    return ExecuteResponse(
        status="ok",
        error=None,
        response=response,
        steps=[
            # ExecutionStep(
            #     module="CV Tailoring",
            #     prompt={},
            #     response={},
            # ),
            # ExecutionStep(
            #     module="Submit Application",
            #     prompt={},
            #     response={},
            # )
        ],
    )
