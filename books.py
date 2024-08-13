from fastapi import FastAPI

app = FastAPI()

@app.get("/{name}")
def read_api(name: str):
    return {"Welcome": name}