import logging
from os import getenv
import time

from pymongo import MongoClient

LOG = logging.getLogger(__name__)

# Get environment variables or use default
DATABASE_NAME = getenv('DATABASE_NAME', 'beacon')
DATABASE_HOST = getenv('DATABASE_HOST', 'mongo')
DATABASE_PORT = getenv('DATABASE_PORT', '27017')
USERNAME = getenv('USERNAME', 'root')
PASSWORD = getenv('DB_PASSWD', 'example')

COLLECTION = 'access_tokens'

def get_db_handle(db_name, host, port, username, password):
    client = MongoClient(host=host,
                         port=int(port),
                         username=username,
                         password=password
                        )
    db_handle = client[db_name][COLLECTION]
    return db_handle, client

db_handle, _ = get_db_handle(DATABASE_NAME, DATABASE_HOST, DATABASE_PORT, USERNAME, PASSWORD)

# Insert token into database
def insert_acess_token(token, exp):
    newDoc = {
        "access_token":token, 
        "exp": exp
    }
    foundDoc = db_handle.find_one(newDoc)
    if foundDoc is None:
        db_handle.insert_one(newDoc)
        return
    
    LOG.debug("Token already in database")

# returns True if token is valid
def check_token(token)->bool:
    doc = db_handle.find_one({"access_token":token})
    if doc is None:
        LOG.debug("Token not found")
        return False
    if doc["exp"] < time.time():
        LOG.debug("Token expired")
        return False
    return True

def prune_expired_tokens():
    # Prune expired tokens
    # TODO
    pass