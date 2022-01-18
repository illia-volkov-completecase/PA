from fastapi import FastAPI

from views import router
from dependencies import static_files, on_internal_error


app = FastAPI()
app.include_router(router)
app.mount("/static", static_files, name="static")
app.middleware('http')(on_internal_error)
