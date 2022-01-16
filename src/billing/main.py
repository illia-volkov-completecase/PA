from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from views import router
from dependencies import static_files


app = FastAPI()
app.include_router(router)
app.mount("/static", static_files, name="static")


@app.middleware('http')
async def on_internal_error(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"exception": str(e)},
        )
