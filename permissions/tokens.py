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
        payload_access_token = jwt.decode(access_token, options={"verify_signature": False})
        
        if payload_access_token['iss'] != idp_issuer:
            raise web.HTTPUnauthorized(text="Access token is not from the right issuer")
        
        if payload_access_token['aud'] != idp_client_id:
            raise web.HTTPUnauthorized(text="Access token is not for the right client")
        
        token_scopes = set(payload_access_token['scope'].split(" "))
        if token_scopes != SCOPES:
            LOG.error(f"Token scopes = {token_scopes}")
            LOG.error(f"Correct scopes = {SCOPES}")
            raise web.HTTPUnauthorized(text="Access token doesn't have the correct scopes")
        
        if payload_access_token['exp'] < time.time():
            raise web.HTTPUnauthorized(text="Access token is expired")
        
    except Exception as e:
        LOG.error(f"Error while verifying access token.\n{str(e)}")
        LOG.debug(f"Access token:\n\n{access_token}\n")
        raise web.HTTPUnauthorized(text=f"Error while verifying access token.")
    
    LOG.debug("Token verification OK")
    return True, payload_access_token['exp']

# returns decoded visa if everything ok
# raises Exception if error occurs
def verify_visa(visa, user_id):
    
    try:
        payload = jwt.decode(access_token, options={"verify_signature": False})
        
        if payload['exp'] < time.time():
            raise web.HTTPUnauthorized(text="Visa is expired")
        
        if payload["sub"] != user_id:
            raise web.HTTPUnauthorized(text="Visa is not for the right user")
        
        # verify that it has the expected value and that it is not empty
        if not payload["ga4gh_visa_v1"]["value"].strip():
            raise web.HTTPUnauthorized(text="Visa value is empty")
        
    except Exception as e:
        LOG.error(f"Error while verifying visa.\n{str(e)}")
        LOG.debug(f"visa:\n\n{visa}\n")
        raise web.HTTPUnauthorized(text=f"Error while verifying visa.")
    
    return payload

def decode_jwt(jwt_token):
    jwt.decode(access_token, options={"verify_signature": False})