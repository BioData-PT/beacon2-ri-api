import logging
import asyncpg
from asyncpg import Pool
from typing import Dict, Optional
import yaml
import requests
from multidict import CIMultiDict
#import jwt

from beacon.utils.json import json_decoder, json_encoder

from permissions.auth import REMS_BEACON_RESOURCE_PREFIX, REMS_URL, REMS_API_USER, REMS_API_KEY
from permissions.auth import get_user_info
from permissions.tokens import parse_visa #decode_jwt

LOG = logging.getLogger(__name__)

class Permissions():
    """Base class, just to agree on the interface."""
    def __init__(self, *args, **kwargs):
        pass

    async def initialize(self):
        raise NotImplementedError('Overload this function in a subclass')

    async def get(self, username, requested_datasets=None):
        """Return an iterable for the granted datasets for the given username and within a requested list of datasets."""
        raise NotImplementedError('Overload this function in a subclass')

    async def close(self):
        raise NotImplementedError('Overload this function in a subclass')



class DummyPermissions(Permissions):
    """
    Dummy permissions plugin
    
    We hard-code the dataset permissions.
    """

    db: Dict = {}

    def __init__(self, *args, **kwargs):
        # Dummy permission database
        with open("/beacon/permissions/permissions.yml", 'r') as stream:
            out = yaml.safe_load(stream)
        self.db = out

    async def initialize(self):
        pass

    async def get(self, username, requested_datasets=None):
        try:
            datasets = set(self.db.get(username))
        except Exception:
            with open("/beacon/permissions/permissions.yml", 'r') as stream:
                permissions_dict = yaml.safe_load(stream)
            permissions_dict[username]=[]
            with open("/beacon/permissions/permissions.yml", 'w') as file:
                yaml.dump(permissions_dict, file)
                self.db = permissions_dict
            datasets = set(self.db.get(username))
            
        if requested_datasets:
            return set(requested_datasets).intersection(datasets)
        else:
            return datasets

    async def close(self):
        pass


class PostgresPermissions(Permissions):
    """
    Postgres permissions plugin
    
    """
    db: Optional[Pool] = None
    args = []
    kwargs = {}

    def __init__(self, *args, **kwargs):
        LOG.info("Creating a connection pool with %s and %s", args, kwargs)
        self.args = args
        self.kwargs = kwargs

    async def initialize(self):
        import asyncpg
        # Connection pool handles reconnections and keeps some expensive connections open for reuse
        self.db = await asyncpg.create_pool(*self.args, **self.kwargs)


    async def get(self, username, requested_datasets=None):
        try:
            assert(self.db is not None)
            async with self.db.acquire() as conn:
                await conn.set_type_codec('jsonb', encoder=json_encoder, decoder=json_decoder, schema='pg_catalog')            
                query = "SELECT dataset FROM datasets where username = $1 and datasets IN $2;"
                response = await conn.fetch(query, username, requested_datasets)
                return [r['dataset'] async for r in response]
        except (asyncpg.exceptions._base.InterfaceError,
                asyncpg.exceptions._base.PostgresError,
                asyncpg.exceptions.UndefinedFunctionError) as e:
            LOG.error('DB Error: %s', e)
            return None

    async def close(self):
        """Close DB Connection."""
        LOG.debug("Closing the database")
        if self.db:
            self.db.terminate()
        self.db = None


class RemsPermissions(Permissions):
    """
    REMS permissions plugin
    
    We get the permissions from the REMS instance
    """

    # TODO CACHE REMS RESPONSE
    db: Dict = {}

    def __init__(self, *args, **kwargs):
        pass

    async def initialize(self):
        LOG.info("Initializing REMS permissions")
        pass

    # TODO filter by requested datasets 
    async def get(self, username, requested_datasets=None):
        LOG.debug(f"ELIXIR ID: {username}")
        request_uri = f"{REMS_URL}/api/permissions/{username}?expired=false"
        headers = CIMultiDict()
        headers.add('content-type', "application/json")
        headers.add('x-rems-api-key', REMS_API_KEY)
        headers.add('x-rems-user-id', REMS_API_USER)
        
        try:
            response = requests.get(url=request_uri, headers=headers).json()
        except Exception as e:
            LOG.error(f"Error while getting permissions from REMS:\n{str(e)}")
            return []
        
        LOG.debug(f"Response from REMS:\n\n{response}\n")
        
        result_datasets = []
        
        # get info from passport
        try:
            visas = response["ga4gh_passport_v1"]
            for visa in visas:
                visa_decoded = parse_visa(visa, username)
                resource_id = visa_decoded["ga4gh_visa_v1"]["value"]
                
                # check if it is a beacon dataset
                if resource_id.startswith(REMS_BEACON_RESOURCE_PREFIX):
                    dataset_id = resource_id.split(REMS_BEACON_RESOURCE_PREFIX)[1]
                    result_datasets.append(dataset_id)
                
            
        except Exception as e:
            LOG.error(f"Error while parsing passport from REMS:{str(e)}\n")
            return []
        
        # remove duplicates
        return list(set(result_datasets))

    async def close(self):
        pass