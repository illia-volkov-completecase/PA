from typing import Optional, Union

from fastapi import Request, Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from bcrypt import checkpw

from settings.core import ROOT
from models.core import session
from models.accounts import Staff, Merchant


static_files = StaticFiles(directory=ROOT / 'static')
templates = Jinja2Templates(directory=ROOT / 'templates')
security = HTTPBasic(auto_error=False)


def paging(pageIndex: Optional[int] = None, pageSize: Optional[int] = None):
    if pageIndex and pageSize:
        return {'offset': (pageIndex - 1) * pageSize, 'limit': pageSize}
    return {'offset': None, 'limit': None}


def db_session():
    with session() as s:
        yield s


def try_get_merchant(
        credentials: HTTPBasicCredentials = Depends(security),
        session: Session = Depends(db_session)
):
    if credentials is None:
        return

    q = Merchant.username == credentials.username
    if merchant := session.query(Merchant).filter(q).first():
        if checkpw(credentials.password.encode(), merchant.password.encode()):
            return merchant


def get_merchant(merchant: Merchant = Depends(try_get_merchant)):
    if not merchant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correct merchant credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return merchant


def try_get_staff(
        credentials: HTTPBasicCredentials = Depends(security),
        session: Session = Depends(db_session)
):
    if credentials is None:
        return

    q = Staff.username == credentials.username
    if staff := session.query(Staff).filter(q).first():
        if checkpw(credentials.password.encode(), staff.password.encode()):
            return staff


def get_staff(staff: Staff = Depends(try_get_staff)):
    if not staff:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Correct staff credentials required",
            headers={"WWW-Authenticate": "Basic"},
        )
    return staff


def try_get_user(
        staff: Optional[Staff] = Depends(try_get_staff),
        merchant: Optional[Merchant] = Depends(try_get_merchant)
):
    if staff:
        return staff
    elif merchant:
        return merchant


def get_user(
        user: Union[Staff, Merchant, None] = Depends(try_get_user)
):
    if user:
        return user
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )


async def on_internal_error(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={"exc_type": str(type(e)), "exc": str(e)},
        )
