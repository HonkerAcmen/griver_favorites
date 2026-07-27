from fastapi import FastAPI
from starlette import status

app = FastAPI()

@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/users", status_code=status.HTTP_201_CREATED)
async def create_user():
    return {
        "id": 1,
        "username": "admin",
        "password": "123456",
    }