from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.staticfiles import StaticFiles
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from bcrypt import checkpw

from settings.core import ROOT
from models.core import engine
from models.accounts import Staff, Merchant


static_files = StaticFiles(directory=ROOT / 'static')
templates = Jinja2Templates(directory=ROOT / 'templates')
security = HTTPBasic()


def paging(pageIndex: Optional[int] = None, pageSize: Optional[int] = None):
    if pageIndex and pageSize:
        return {'offset': (pageIndex - 1) * pageSize, 'limit': pageSize}
    return {'offset': None, 'limit': None}


def db_session():
    return Session(engine)


def try_get_merchant(
        credentials: HTTPBasicCredentials = Depends(security),
        session: Session = Depends(db_session)
):
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


def get_user(
        staff: Optional[Staff] = Depends(try_get_staff),
        merchant: Optional[Merchant] = Depends(try_get_merchant)
):
    if staff:
        return staff
    elif merchant:
        return merchant
    else:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect credentials",
            headers={"WWW-Authenticate": "Basic"},
        )
