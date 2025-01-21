from fastapi import FastAPI
import os
import importlib
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

app = FastAPI()

origins = [
    "http://localhost:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Or ["*"] to allow all origins (not recommended in production)
    allow_credentials=True,
    allow_methods=["*"],  # Allow all HTTP methods
    allow_headers=["*"],  # Allow all headers
)

routes_dir = os.path.join(os.path.dirname(__file__), "routes")
for filename in os.listdir(routes_dir):
    if filename.endswith(".py") and filename != "__init__.py":
        module_name = f"routes.{filename[:-3]}"
        module = importlib.import_module(module_name)
        if hasattr(module, "router"):
            app.include_router(module.router)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
