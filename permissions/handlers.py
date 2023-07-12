import logging
import time

from typing import Optional

from aiohttp import web
from aiohttp.web import FileField
from aiohttp.web_request import Request
from multidict import CIMultiDict
import requests

from permissions.auth import SCOPES, bearer_required
from permissions.auth import idp_authorize, idp_client_id, idp_client_secret, idp_callback_url, idp_token_url, idp_issuer
from permissions.auth import ALLOWED_LOCATIONS
from permissions.db import insert_acess_token, check_token

from urllib.parse import urlparse
from base64 import b64decode, b64encode
import jwt

from permissions.tokens import verify_access_token


LOG = logging.getLogger(__name__)

@bearer_required
async def permission(request: Request, username: Optional[str]):

    if request.headers.get('Content-Type') == 'application/json':
        post_data = await request.json()
    else:
        post_data = await request.post()
    LOG.debug('POST DATA: %s', post_data)

    v = post_data.get('datasets')
    if v is None:
        requested_datasets = []
    elif isinstance(v, list):
        requested_datasets = v
    elif isinstance(v, FileField):
        requested_datasets = []
    else:
        requested_datasets = v.split(sep=',')  # type: ignore
        
    LOG.debug('requested datasets: %s', requested_datasets)
    datasets = await request.app['permissions'].get(username, requested_datasets=requested_datasets)
    LOG.debug('selected datasets: %s', datasets)

    return web.json_response(list(datasets or [])) # cuz python-json doesn't like sets

# Redirect to the login URI
async def login_redirect(request: Request, username: Optional[str]):
    callback_url = idp_callback_url
    if callback_url is None:
        logging.error("OIDC_CALLBACK_URL not set")
        raise web.HTTPInternalServerError(text="OIDC_CALLBACK_URL not set")
    
    client_id = idp_client_id
    if client_id is None:
        logging.error("CLIENT_ID not set")
        raise web.HTTPInternalServerError(text="CLIENT_ID not set")
    
    state = request.query.get('state')
    stateDecoded = b64decode(state)
    redirect_uri = f"{idp_authorize}?response_type=code&client_id={client_id}&scope={' '.join(SCOPES)}&state={state}&redirect_uri={callback_url}"
    logging.debug(f"Raw State is {state}")
    logging.debug(f"Decoded state is {stateDecoded}")
    logging.info(f"Redirecting to {redirect_uri}")
    raise web.HTTPSeeOther(location=redirect_uri)

# TODO
# Callback from the login URI, at the end redirects user to the original request
async def login_callback(request: Request, username: Optional[str]):
    
    code = request.query.get('code')
    logging.info(f"Code is {code}")
    
    if not code:
        logging.error("No code provided")
        raise web.HTTPUnauthorized(text="No code provided")
    
    # search for url in state to redirect user to the original webpage
    try:
        state = request.query.get('state')
        logging.debug(f"State is {state}")
        stateDecoded = b64decode(state)
        logging.debug(f"State (decoded) is {stateDecoded}")
        urlParser = urlparse(stateDecoded)
    except Exception as e:
        logging.error(f"Error while parsing state {e}")
        raise web.HTTPUnauthorized(text=f"Error while parsing state {e}")
    
    # check that state is a trusted url
    if urlParser.scheme != "https":
        logging.error("Redirect URI is not https")
        raise web.HTTPUnauthorized(text="Redirect URI is not https")
    
    if urlParser.netloc not in ALLOWED_LOCATIONS:
        logging.error("Redirect URI is not allowed, allowed locations are: %s", ALLOWED_LOCATIONS)
        raise web.HTTPUnauthorized(text=f"Redirect URI is not allowed, allowed_locations={ALLOWED_LOCATIONS}")       
    
    # url is trusted
    redirect_uri = stateDecoded
    
    # use code to get access token
    request_uri = f'{idp_token_url}?' \
    'grant_type=authorization_code&' \
    'code={code}&' \
    'client_id={idp_client_id}&' \
    'client_secret={idp_client_secret}&' \
    f'scope={"%20".join(SCOPES)}&' \
    'requested_token_type=urn:ietf:params:oauth:token-type:refresh_token&' \
    'redirect_uri={idp_callback_url}'
    
    logging.debug(f"Token request URI is {request_uri}")
    headersRequest = CIMultiDict()
    headersRequest.add('Content-Type', 'application/x-www-form-urlencoded')
    
    # get access token from the IDP
    try:
        response = requests.post(url=request_uri, headers=headersRequest).json()
        access_token = response['access_token']
    except Exception as e:
        logging.error(f"Error while getting access token {e}")
        raise web.HTTPUnauthorized(text=f"Error while getting access token {e}")
    
    verification_result, exp = verify_access_token(access_token)
    
    if not verification_result:
        logging.error("Error while verifying access token")
        raise web.HTTPUnauthorized(text="Error while verifying access token")
    
    # save access token in the DB
    insert_acess_token(access_token, exp)

    # redirect user to the original webpage
    # redirect_uri is the url in the state param
    headers = CIMultiDict()
    headers.add('Authorization', f"Bearer {access_token}")
    
    raise web.HTTPSeeOther(location=redirect_uri, headers=headers)