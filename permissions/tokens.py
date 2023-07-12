import jwt
import time
from aiohttp import web

from permissions.auth import SCOPES
from permissions.auth import idp_client_id, idp_issuer

import logging

LOG = logging.getLogger(__name__)

def verify_access_token(access_token):
    
    try:
        # check accessToken
        payloadAccessToken = jwt.decode(access_token, options={"verify_signature": False})
        
        if payloadAccessToken['iss'] != idp_issuer:
            raise web.HTTPUnauthorized(text="Access token is not from the right issuer")
        
        if payloadAccessToken['aud'] != idp_client_id:
            raise web.HTTPUnauthorized(text="Access token is not for the right client")
        
        token_scopes = set(payloadAccessToken['scope'].split(" "))
        if token_scopes != SCOPES:
            LOG.error(f"Token scopes = {token_scopes}")
            LOG.error(f"Correct scopes = {SCOPES}")
            raise web.HTTPUnauthorized(text="Access token doesn't have the correct scopes")
        
        if payloadAccessToken['exp'] < time.time():
            raise web.HTTPUnauthorized(text="Access token is expired")
        
    except Exception as e:
        LOG.error(f"Error while verifying access token.\n{str(e)}")
        LOG.debug(f"Access token:\n\n{access_token}\n")
        raise web.HTTPUnauthorized(text=f"Error while verifying access token.")
    
    LOG.debug("Token verification OK")
    return True, payloadAccessToken['exp']