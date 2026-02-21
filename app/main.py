from fastapi import FastAPI

from app.infrastructure.web.routers.threads import router as threads_router
from app.infrastructure.web.routers.runs import router as runs_router
from app.infrastructure.web.routers.users import router as users_router


app = FastAPI()

app.include_router(threads_router)
app.include_router(runs_router)
app.include_router(users_router)


@app.get("/")
def hello():
    return {"message": "hello world"}
