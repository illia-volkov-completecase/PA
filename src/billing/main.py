from fastapi import FastAPI

from views import router
from dependencies import static_files


app = FastAPI()
app.include_router(router)
app.mount("/static", static_files, name="static")
