import jwt
import time
from typing import *
from aiohttp import web
from os import getenv

from permissions.auth import REMS_PUB_URL, SCOPES
from permissions.auth import idp_client_id, idp_issuer

MAX_TOKEN_AGE = int(getenv("MAX_TOKEN_AGE", None))

import logging

LOG = logging.getLogger(__name__)

# returns (isOk, exp_date, max_age)
def verify_access_token(access_token) -> Tuple[bool, int, int]:
    
    now = int(time.time())
    
    try:
        # check accessToken
        payload_access_token = jwt.decode(access_token, options={"verify_signature": False})
        
        if payload_access_token['iss'] != idp_issuer:
            raise web.HTTPUnauthorized(text="Access token is not from the right issuer")
        
        if payload_access_token['iat'] > now:
            raise web.HTTPUnauthorized(text="Access token was issued in the future")
        
        if payload_access_token['aud'] != idp_client_id:
            raise web.HTTPUnauthorized(text="Access token is not for the right client")
        
        token_scopes = set(payload_access_token['scope'].split(" "))
        if token_scopes != SCOPES:
            LOG.error(f"Token scopes = {token_scopes}")
            LOG.error(f"Correct scopes = {SCOPES}")
            raise web.HTTPUnauthorized(text="Access token doesn't have the correct scopes")
        
        if payload_access_token['exp'] < now:
            raise web.HTTPUnauthorized(text="Access token is expired")
        
    except Exception as e:
        LOG.error(f"Error while verifying access token.\n{str(e)}")
        LOG.debug(f"Access token:\n\n{access_token}\n")
        raise web.HTTPUnauthorized(text=f"Error while verifying access token.")
    
    LOG.debug("Token verification OK")
    # force Beacon to just accept this token for a max configurable amount
    # instead of as much as user wants
    exp_max = payload_access_token["iat"] + MAX_TOKEN_AGE
    exp_token = payload_access_token["exp"]
    exp = min(exp_max, exp_token)
    max_age = exp - now
    if max_age < 0:
        LOG.error(f"Negative max_age: {max_age}")
        return False, 0, 0
    return True, exp, max_age

# returns decoded visa if everything ok
# raises Exception if error occurs
def parse_visa(visa, user_id):
    
    try:
        payload = jwt.decode_jwt(visa)
        
        if payload['exp'] < time.time():
            raise web.HTTPUnauthorized(text="Visa is expired")
        
        if payload["sub"] != user_id:
            raise web.HTTPUnauthorized(text="Visa is not for the right user")
        
        # verify that it has the expected value and that it is not empty
        if not payload["ga4gh_visa_v1"]["value"].strip():
            raise web.HTTPUnauthorized(text="Visa value is empty")
        
        """
        # TODO THIS WILL NEED TO BE REPLACED BY A SERIOUS LIST OF
        # TRUSTED ISSUERS AND THEIR JWT ENDPOINT
        if payload["ga4gh_visa_v1"]["source"] != REMS_PUB_URL:
            LOG.error(f"Visa source doesn't match")
            LOG.erorr(f"Expected: {REMS_PUB_URL}")
            LOG.error(f'Received: {payload["ga4gh_visa_v1"]["source"]}')
            raise web.HTTPUnauthorized(text="Visa source doesn't match.")
        """    
        
        
    except Exception as e:
        LOG.error(f"Error while verifying visa.\n{str(e)}")
        LOG.debug(f"visa:\n\n{visa}\n")
        raise web.HTTPUnauthorized(text=f"Error while verifying visa.")
    
    return payload

def decode_jwt(jwt_token):
    return jwt.decode(jwt_token, options={"verify_signature": False})

# receives passport in list format (decoded)
# returns True if passports grant registered access, False otherwise
def verify_registered(passport:List[str], user_id) -> bool:
    found_researcher_status = False
    found_accepted_terms = False
    
    for encoded_visa in passport:
        try:
            decoded_visa = parse_visa(encoded_visa, user_id)["ga4gh_visa_v1"]
            if decoded_visa["type"] == "ResearcherStatus":
                found_researcher_status = True
            elif decoded_visa["type"] == "AcceptedTermsAndPolicies":
                found_accepted_terms = True
                
        except Exception as e:
            LOG.error(f"Error verifying visa: {e}")
            
        if found_researcher_status and found_accepted_terms:
            return True
        
    return False