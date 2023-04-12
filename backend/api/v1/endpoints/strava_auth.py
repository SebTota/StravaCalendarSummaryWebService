from datetime import datetime, timezone
import logging

from fastapi import APIRouter, HTTPException, Depends
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from stravalib.client import Client

from backend import models, schemas, crud
from backend.api import deps
from backend.core.config import settings

router = APIRouter()


@router.get('/auth')
def strava_auth(current_user: models.User = Depends(deps.get_current_active_user)):
    auth_url = Client().authorization_url(
            client_id=int(settings.STRAVA_CLIENT_ID),
            redirect_uri=settings.STRAVA_AUTH_CALLBACK_URL,
            scope=['read', 'activity:read_all'])

    return RedirectResponse(auth_url + '&approval_prompt=auto')


@router.get('/callback', response_model=schemas.Msg)
def strava_auth_callback(code: str,
                         db: Session = Depends(deps.get_db),
                         current_user: models.User = Depends(deps.get_current_active_user)):
    try:
        token_response = Client().exchange_code_for_token(
            client_id=int(settings.STRAVA_CLIENT_ID),
            client_secret=settings.STRAVA_CLIENT_SECRET,
            code=code)
    except:
        logging.error('Could not authenticate user with Strava. Strava exchange code for token failed.')
        raise HTTPException(status_code=400,
                            detail='The authorization code provided was invalid. '
                                   'Please try authenticating with Strava again')

    access_token: str = str(token_response['access_token'])
    refresh_token: str = token_response['refresh_token']
    expires_at: datetime = datetime.fromtimestamp(token_response['expires_at'], timezone.utc)

    strava_credentials_obj: schemas.StravaCredentialsCreate = schemas.StravaCredentialsCreate(access_token=access_token,
                                                                                       expires_at=expires_at,
                                                                                       refresh_token=refresh_token)

    crud.strava_credentials.create_and_add_to_user(db, current_user.id, strava_credentials_obj)

    return schemas.Msg(msg="Authenticated.")
