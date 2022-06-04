from typing import Optional
from fastapi import APIRouter, Request, HTTPException, Cookie, Response
from fastapi.responses import RedirectResponse
from stravalib.client import Client
import logging
import os
import time
import traceback
from stravalib.model import Athlete

from strava_calendar_summary_data_access_layer import StravaCredentials, User, UserController
from strava_calendar_summary_utils import StravaUtil
from backend.models import user_auth, UserUI

router = APIRouter()


@router.get('/auth/strava')
def strava_get_authorization_token(request: Request):
    strava_client = Client()  # TODO: Move this to utils package
    auth_url = strava_client.authorization_url(
            client_id=int(os.getenv('STRAVA_CLIENT_ID')),
            redirect_uri=request.url_for('strava_authorized_callback'),
            scope=['activity:read_all'])

    return RedirectResponse(auth_url)


@router.get('/auth/strava/callback')
def strava_authorized_callback(request: Request):
    if 'code' not in request.query_params:
        return RedirectResponse(os.getenv('UI_BASE_URL'))
    code = request.query_params['code']

    strava_client = Client()  # TODO: Move this to utils package

    try:
        token_response = strava_client.exchange_code_for_token(
            client_id=int(os.getenv('STRAVA_CLIENT_ID')),
            client_secret=os.getenv('STRAVA_CLIENT_SECRET'),
            code=code)
    except:
        logging.error('Could not authenticate user with Strava. Strava exchange code for token failed.')
        raise HTTPException(
            status_code=400,
            detail='The authorization code provided was invalid. Please try authenticating with Strava again')

    access_token = token_response['access_token']
    refresh_token = token_response['refresh_token']
    expires_at = token_response['expires_at']

    strava_creds: StravaCredentials = StravaCredentials(access_token, refresh_token, expires_at)
    strava_util = StravaUtil(strava_creds)
    athlete: Athlete = strava_util.get_athlete()

    request.session['user_id'] = athlete.id

    user = User(str(athlete.id), athlete.firstname, athlete.lastname, strava_credentials=strava_creds)
    UserController().insert(user.user_id, user)

    response: RedirectResponse = RedirectResponse(os.getenv('UI_BASE_URL'))
    auth_cookie_encrypted = user_auth.update_session_cookie(user_auth.UserAuth(user.user_id, expires_at))
    response.set_cookie(key='Authentication', value=auth_cookie_encrypted, expires=expires_at, httponly=True)
    return response


@router.get('/user/me', response_model=UserUI)
async def get_strava_user_info(response: Response, Authentication: Optional[str] = Cookie(None)):
    # TODO: Put a redis cache in front of this and update the cache every time the strava refresh token is refreshed
    if Authentication is None:
        raise HTTPException(status_code=401, detail='User not signed in')

    auth_cookie: user_auth.UserAuth = user_auth.decrypt_session_cookie(Authentication)

    try:
        user: User = UserController().get_by_id(auth_cookie.user_id)
    except Exception as e:
        logging.exception('Failed retrieving user: {} while getting session data'.format(auth_cookie.user_id) + str(e))
        raise HTTPException(status_code=500, detail='An error occured while retrieving the signed in user details.')


    if user is None:
        raise HTTPException(status_code=401, detail='User does not exist')

    if auth_cookie.expires < time.time():
        # Refresh Strava access token
        refreshed_credentials: StravaCredentials = StravaUtil(user.strava_credentials, user).update_strava_credentials()

        if refreshed_credentials is None:
            raise HTTPException(status_code=401, detail='Couldn\'t refresh user strava access token')

        user.strava_credentials = refreshed_credentials  # Creds already updated in db so no need to re-update

    auth_cookie_encrypted = user_auth.update_session_cookie(
        user_auth.UserAuth(user.user_id, user.strava_credentials.expiry_date))

    resp_obj: UserUI = UserUI(user_id=user.user_id,
                              first_name=user.first_name,
                              last_name=user.last_name,
                              strava_authenticated=user.strava_credentials is not None,
                              calendar_authenticated=user.calendar_credentials is not None,
                              calendar_preferences=user.calendar_preferences.to_dict())

    response.set_cookie(key='Authentication', value=auth_cookie_encrypted,
                        expires=user.strava_credentials.expiry_date, httponly=True)
    return resp_obj
