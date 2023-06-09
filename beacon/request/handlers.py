import json
import asyncio
import copy
import logging
from aiohttp import web
from aiohttp.web_request import Request
from bson import json_util
from beacon import conf

from beacon.request import ontologies
from beacon.request.model import Granularity, RequestParams
from beacon.response.build_response import (
    build_beacon_resultset_response,
    build_beacon_collection_response,
    build_beacon_boolean_response,
    build_beacon_count_response,
    build_filtering_terms_response,
    build_beacon_resultset_response_by_dataset
)
from beacon.utils.stream import json_stream
from beacon.db.datasets import get_datasets, get_public_datasets
from beacon.utils.auth import resolve_token

LOG = logging.getLogger(__name__)


def collection_handler(db_fn, request=None):
    async def wrapper(request: Request):
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams = RequestParams(**json_body).from_request(request)
        LOG.debug(f"Query Params = {qparams}")
        entry_id = request.match_info["id"] if "id" in request.match_info else None
        
        # backup qparams before db_fn modifies it
        qparams_backup = copy.deepcopy(qparams)
        
        # Get response
        entity_schema, count, records = db_fn(entry_id, qparams)
        response_converted = (
            [r for r in records] if records else []
        )
        
        # restore qparams
        qparams = qparams_backup
        
        response = build_beacon_collection_response(
            response_converted, count, qparams, lambda x, y: x, entity_schema
        )
        return await json_stream(request, response)

    return wrapper

# TODO
# THIS IS THE OLD IMPLEMENTATION, THE NEW ONE IS BELOW.
# The new one has responses by datasets, this one doesn't
# Later we should replace this one with the new one
def generic_handler(db_fn, request=None):
    async def wrapper(request: Request):
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams = RequestParams(**json_body).from_request(request)
        LOG.debug(f"Query Params = {qparams}")
        entry_id = request.match_info.get('id', None)

        # backup qparams before db_fn modifies it
        qparams_backup = copy.deepcopy(qparams)

        # Get response
        entity_schema, count, records = db_fn(entry_id, qparams)
        response_converted = records

        LOG.debug(f"*** Difference between qparams ***"
                  f"\nQparams changed: {qparams.dict()}"
                  f"\nQparams backup: {qparams_backup.dict()}")
        # restore qparams
        qparams = qparams_backup
        
        response = None

        if qparams.query.requested_granularity == Granularity.BOOLEAN:
            response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
        
        elif qparams.query.requested_granularity == Granularity.COUNT:
            if conf.max_beacon_granularity == Granularity.BOOLEAN:
                response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            else:
                response = build_beacon_count_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
        
        # qparams.query.requested_granularity == Granularity.RECORD:
        else:

            if conf.max_beacon_granularity == Granularity.BOOLEAN:
                response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            elif conf.max_beacon_granularity == Granularity.COUNT:
                response = build_beacon_count_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            else:
                response = build_beacon_resultset_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
                
        return await json_stream(request, response)

    return wrapper

"""
TODO : THIS IS CURRENTLY COMMENTED TO MAINTAIN THE OLD BEHAVIOUR OF THE BEACON
Sooner or later we will have to implement this

def generic_handler(db_fn, request=None):
    async def wrapper(request: Request):
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams:RequestParams = RequestParams(**json_body).from_request(request)

        LOG.debug(f"Query Params = {qparams}")
        
        search_datasets = []
        authenticated=False
        access_token = request.headers.get('Authorization')
        LOG.debug(f"Auth token = {access_token}")
        
        list_of_dataset_dicts : list[dict] = []
        
        if access_token is None:
            list_of_dataset_dicts = [doc["name"] for doc in get_public_datasets()]
            LOG.debug(f"list of pub datasets = {list_of_dataset_dicts}")
            beacon_datasets = [ r for r in datasets ]
        # Authorized acess
        else:
            try:
                specific_datasets = qparams.query.request_parameters['datasets']
            except Exception:
                specific_datasets = []
            access_token = access_token[7:]  # cut out 7 characters: len('Bearer ')
            
            authorized_datasets, authenticated = await resolve_token(access_token, search_datasets)
            LOG.debug(authorized_datasets)
            #LOG.debug('all datasets:  %s', all_datasets)
            LOG.info('resolved datasets:  %s', authorized_datasets)
            LOG.debug(authenticated)
            LOG.debug(specific_datasets)

            specific_datasets_unauthorized = []
            specific_datasets_unauthorized_and_found = []
            bio_list = []
            search_and_authorized_datasets = []
            specific_search_datasets = []
            # Get response
            if specific_datasets != []:
                for element in authorized_datasets:
                    if element in specific_datasets:
                        search_and_authorized_datasets.append(element)
                for elemento in specific_datasets:
                    if elemento not in search_and_authorized_datasets:
                        specific_datasets_unauthorized.append(elemento)
                qparams.query.request_parameters = {}
                qparams.query.request_parameters['datasets'] = '*******'
                _, _, datasets = get_datasets(None, qparams)
                beacon_datasets = [ r for r in datasets ]
                all_datasets = [r['id'] for r in beacon_datasets]
                
                response_datasets = [ r['id'] for r in beacon_datasets if r['id'] in search_and_authorized_datasets]
                LOG.debug(specific_search_datasets)
                LOG.debug(response_datasets)

                list_of_dataset_dicts=[]

                for data_r in response_datasets:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_r
                    dict_dataset['ids']=[ r['ids'] for r in beacon_datasets if r['id'] == data_r ]
                    list_of_dataset_dicts.append(dict_dataset)

                for dataset_searched in specific_datasets_unauthorized:
                    if dataset_searched not in all_datasets:
                        dict_dataset = {}
                        dict_dataset['dataset']=dataset_searched
                        dict_dataset['ids'] = ['Dataset not found']
                        LOG.debug(dict_dataset['dataset'])
                        LOG.debug(dict_dataset['ids'])
                        list_of_dataset_dicts.append(dict_dataset)
                
                for data_s in specific_datasets_unauthorized_and_found:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_s
                    dict_dataset['ids'] = ['Unauthorized dataset']
                    list_of_dataset_dicts.append(dict_dataset)

                LOG.debug(specific_datasets_unauthorized_and_found)
                LOG.debug(specific_datasets_unauthorized)
                LOG.debug(list_of_dataset_dicts)

            # if specific_datasets = []
            else:
                qparams.query.request_parameters = {}
                qparams.query.request_parameters['datasets'] = '*******'
                _, _, datasets = get_datasets(None, qparams)
                beacon_datasets = [ r for r in datasets ]
                specific_datasets = [ r['id'] for r in beacon_datasets if r['id'] not in authorized_datasets]
                response_datasets = [ r['id'] for r in beacon_datasets if r['id'] in authorized_datasets]
                LOG.debug(specific_datasets)
                LOG.debug(response_datasets)
                specific_datasets_unauthorized.append(specific_datasets)
                for unauth in specific_datasets_unauthorized:
                    for unauth_spec in unauth:
                        biosample_ids = [ r['ids'] for r in beacon_datasets if r['id'] == unauth_spec ]
                        bio_list.append(biosample_ids)
                
                list_of_dataset_dicts=[]

                for data_r in response_datasets:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_r
                    dict_dataset['ids']=[ r['ids'] for r in beacon_datasets if r['id'] == data_r ]
                    list_of_dataset_dicts.append(dict_dataset)
                
                for data_s in specific_datasets:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_s
                    dict_dataset['ids'] = ['Unauthorized dataset']
                    list_of_dataset_dicts.append(dict_dataset)
                LOG.debug(list_of_dataset_dicts)
            
            # -- end of if Authorized acess --
        
        qparams = RequestParams(**json_body).from_request(request)
        

        entry_id = request.match_info.get('id', None)
        entity_schema, count, records = db_fn(entry_id, qparams)
        LOG.debug(f"schema = {entity_schema}")
        
        if records:
            LOG.debug(f"first record = {records[0]}")
        else:
            LOG.debug(f"no records found")

        response_converted = records
        
        if qparams.query.requested_granularity == Granularity.BOOLEAN:
            response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
        
        elif qparams.query.requested_granularity == Granularity.COUNT:
            if conf.max_beacon_granularity == Granularity.BOOLEAN:
                response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            else:
                response = build_beacon_count_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
        
        # if requested_granularity == Granularity.RECORD:
        else:

            if conf.max_beacon_granularity == Granularity.BOOLEAN:
                response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            elif conf.max_beacon_granularity == Granularity.COUNT:
                response = build_beacon_count_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            else:
                response = build_beacon_resultset_response_by_dataset(response_converted, list_of_dataset_dicts, count, qparams, lambda x, y: x, entity_schema)
                
        return await json_stream(request, response)

    return wrapper
    
"""

def filtering_terms_handler(db_fn, request=None):
    async def wrapper(request: Request):
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams = RequestParams(**json_body).from_request(request)

        LOG.debug(qparams)
        
        search_datasets = []
        authenticated=False
        access_token = request.headers.get('Authorization')
        LOG.debug(access_token)
        if access_token is not None:
            try:
                specific_datasets = qparams.query.request_parameters['datasets']
            except Exception:
                specific_datasets = []
            access_token = access_token[7:]  # cut out 7 characters: len('Bearer ')
            
            authorized_datasets, authenticated = await resolve_token(access_token, search_datasets)
            LOG.debug(authorized_datasets)
            #LOG.debug('all datasets:  %s', all_datasets)
            LOG.info('resolved datasets:  %s', authorized_datasets)
            LOG.debug(authenticated)
            LOG.debug(specific_datasets)

            specific_datasets_unauthorized = []
            specific_datasets_unauthorized_and_found = []
            bio_list = []
            search_and_authorized_datasets = []
            specific_search_datasets = []
            # Get response
            if specific_datasets != []:
                for element in authorized_datasets:
                    if element in specific_datasets:
                        search_and_authorized_datasets.append(element)
                for elemento in specific_datasets:
                    if elemento not in search_and_authorized_datasets:
                        specific_datasets_unauthorized.append(elemento)
                qparams.query.request_parameters = {}
                qparams.query.request_parameters['datasets'] = '*******'
                _, _, datasets = get_datasets(None, qparams)
                beacon_datasets = [ r for r in datasets ]
                all_datasets = [r['id'] for r in beacon_datasets]
                
                response_datasets = [ r['id'] for r in beacon_datasets if r['id'] in search_and_authorized_datasets]
                LOG.debug(specific_search_datasets)
                LOG.debug(response_datasets)

                list_of_dataset_dicts=[]

                for data_r in response_datasets:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_r
                    dict_dataset['ids']=[ r['ids'] for r in beacon_datasets if r['id'] == data_r ]
                    list_of_dataset_dicts.append(dict_dataset)

                for dataset_searched in specific_datasets_unauthorized:
                    if dataset_searched not in all_datasets:
                        dict_dataset = {}
                        dict_dataset['dataset']=dataset_searched
                        dict_dataset['ids'] = ['Dataset not found']
                        LOG.debug(dict_dataset['dataset'])
                        LOG.debug(dict_dataset['ids'])
                        list_of_dataset_dicts.append(dict_dataset)
                
                for data_s in specific_datasets_unauthorized_and_found:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_s
                    dict_dataset['ids'] = ['Unauthorized dataset']
                    list_of_dataset_dicts.append(dict_dataset)

                LOG.debug(specific_datasets_unauthorized_and_found)
                LOG.debug(specific_datasets_unauthorized)

            else:
                qparams.query.request_parameters = {}
                qparams.query.request_parameters['datasets'] = '*******'
                _, _, datasets = get_datasets(None, qparams)
                beacon_datasets = [ r for r in datasets ]
                specific_datasets = [ r['id'] for r in beacon_datasets if r['id'] not in authorized_datasets]
                response_datasets = [ r['id'] for r in beacon_datasets if r['id'] in authorized_datasets]
                LOG.debug(specific_datasets)
                LOG.debug(response_datasets)
                specific_datasets_unauthorized.append(specific_datasets)
                for unauth in specific_datasets_unauthorized:
                    for unauth_spec in unauth:
                        biosample_ids = [ r['ids'] for r in beacon_datasets if r['id'] == unauth_spec ]
                        bio_list.append(biosample_ids)
                
                list_of_dataset_dicts=[]

                for data_r in response_datasets:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_r
                    dict_dataset['ids']=[ r['ids'] for r in beacon_datasets if r['id'] == data_r ]
                    list_of_dataset_dicts.append(dict_dataset)
                
                for data_s in specific_datasets:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_s
                    dict_dataset['ids'] = ['Unauthorized dataset']
                    list_of_dataset_dicts.append(dict_dataset)
                LOG.debug(list_of_dataset_dicts)
        else:
            list_of_dataset_dicts=[]

        qparams = RequestParams(**json_body).from_request(request)
        

        entry_id = request.match_info.get('id', None)
        entity_schema, count, records = db_fn(entry_id, qparams)

        response_converted = records
        
        if qparams.query.requested_granularity == Granularity.BOOLEAN:
            response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
        
        elif qparams.query.requested_granularity == Granularity.COUNT:
            if conf.max_beacon_granularity == Granularity.BOOLEAN:
                response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            else:
                response = build_beacon_count_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
        
        # qparams.query.requested_granularity == Granularity.RECORD:
        else:

            if conf.max_beacon_granularity == Granularity.BOOLEAN:
                response = build_beacon_boolean_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            elif conf.max_beacon_granularity == Granularity.COUNT:
                response = build_beacon_count_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
            else:
                response = build_filtering_terms_response(response_converted, count, qparams, lambda x, y: x, entity_schema)
                
        return await json_stream(request, response)

    return wrapper
