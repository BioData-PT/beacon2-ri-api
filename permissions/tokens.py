import jwt
import time
from aiohttp import web

from permissions.auth import SCOPES
from permissions.auth import idp_client_id, idp_issuer


def verify_access_token(access_token):
    
    try:
        # check accessToken
        payloadAccessToken = jwt.decode(access_token, verify=True)
        
        if payloadAccessToken['iss'] != idp_issuer:
            raise web.HTTPUnauthorized(text="Access token is not from the right issuer")
        
        if payloadAccessToken['aud'] != idp_client_id:
            raise web.HTTPUnauthorized(text="Access token is not for the right client")
        
        if payloadAccessToken['scope'] != SCOPES:
            raise web.HTTPUnauthorized(text=\
                f"Access token doesn't have the right scope.\n" \
                f"Expected: {SCOPES}, got: {payloadAccessToken['scope']}"\
            )
        
        if payloadAccessToken['exp'] < time.time():
            raise web.HTTPUnauthorized(text="Access token is expired")
        
    except Exception as e:
        raise web.HTTPUnauthorized(text=f"Error while getting access token.\n{e}")
    
    return True, payloadAccessToken['exp']