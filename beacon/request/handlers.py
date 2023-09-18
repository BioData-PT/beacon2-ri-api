import json
import asyncio
import copy
import logging
from typing import Dict, List, Tuple
from aiohttp import web
from aiohttp.web_request import Request
from bson import json_util
from beacon import conf
import yaml

from beacon.request import ontologies
from beacon.request.model import AlphanumericFilter, Granularity, RequestParams
from beacon.response.build_response import (
    build_beacon_resultset_response,
    build_beacon_collection_response,
    build_beacon_boolean_response,
    build_beacon_count_response,
    build_filtering_terms_response,
    build_beacon_resultset_response_by_dataset,
    build_generic_response
)
from beacon.utils.stream import json_stream
from beacon.db.datasets import get_datasets, get_public_datasets
from beacon.utils.auth import get_accessible_datasets, resolve_token

LOG = logging.getLogger(__name__)


def collection_handler(db_fn, request=None):
    async def wrapper(request: Request):
        LOG.info("-- Collection handler --")
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams = RequestParams(**json_body).from_request(request)
        LOG.debug(f"Query Params = {qparams}")
        entry_id = request.match_info["id"] if "id" in request.match_info else None
        
        # backup qparams before db_fn modifies it
        qparams_backup = copy.deepcopy(qparams)
        
        # find permissions for user
        
        
        # add qparam to filter datasets by permissions
        
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


# handler with authentication & REMS
# mostly from BioData.pt
def generic_handler(db_fn, request=None):
    
    async def wrapper(request:Request):
        LOG.info("-- Generic handler --")
        
        # Get params
        entry_id = request.match_info.get('id', None)
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams:RequestParams = RequestParams(**json_body).from_request(request)
        
        LOG.debug(f"Query Params = {qparams}")
        
        authenticated=False
        
        access_token_header = request.headers.get('Authorization')
        access_token_cookies = request.cookies.get("Authorization")
        LOG.debug(f"Access token header = {access_token_header}")
        LOG.debug(f"Access token cookies = {access_token_cookies}")
        
        # set access_token as the one we recieve in the header
        # if not in header, get the one from cookies
        if access_token_header:
            access_token = access_token_header
        else:
            access_token = access_token_cookies
        
        # TODO: get requested datasets from qparams
        requested_datasets = None # will search all datasets
        
        # Start async task to request datasets from permissions server
        task_permissions = asyncio.create_task(get_accessible_datasets(access_token, requested_datasets))

        # get list of datasets
        _, _, all_datasets_docs = get_datasets(None, RequestParams())
        all_dataset_ids = [ doc["id"] for doc in all_datasets_docs]
        
        # query all datasets in parallel
        tasks_dataset_queries = []
        # { dataset_id:(count, records) }
        datasets_query_results:Dict[str, Tuple[int,List[dict]]] = {}
        
        db_fn_submodule = str(db_fn.__module__).split(".")[-1]
        LOG.debug(f"db_fn submodule = {db_fn_submodule}")
        
        entity_schema = db_fn_submodule # in case no records are found
        
        # TODO do this asynchronously
        for dataset_id in all_dataset_ids:
            qparams_dataset = copy.deepcopy(qparams)
            LOG.debug("")
            LOG.debug(f"=========================")
            LOG.debug(f"dataset_id = {dataset_id}")
            LOG.debug(f"=========================")
            # change field for genomicVariations
            if db_fn_submodule == "g_variants":
                filter_dataset_id = {
                    "id": "_info.datasetId",
                    "value": dataset_id 
                }
            else:
                filter_dataset_id = {
                    "id": "datasetId", 
                    "value": dataset_id
                }
                
            qparams_dataset.query.filters.append(filter_dataset_id)
            LOG.debug(f"Dataset Qparams = {qparams_dataset}")
            entity_schema, count, records = db_fn(entry_id, qparams_dataset)
            dataset_result = (count, list(records))
            datasets_query_results[dataset_id] = (dataset_result)
        
        LOG.debug(f"schema = {entity_schema}")
        
        # get response of permissions server
        accessible_datasets:List[str] = [] # array of dataset ids
        accessible_datasets, authenticated = await task_permissions

        # get the max authorized granularity
        requested_granularity = qparams.query.requested_granularity
        max_granularity = Granularity(conf.max_beacon_granularity)
        response_granularity = Granularity.get_lower(requested_granularity, max_granularity)
        
        # build response
        
        response = build_generic_response(
            results_by_dataset=datasets_query_results,
            accessible_datasets=accessible_datasets,
            granularity=response_granularity,
            qparams=qparams,
            entity_schema=entity_schema
        )
        
        return await json_stream(request, response)
        
        
    return wrapper
    
    
    
# handler with authentication
# mostly from CRG

def generic_handler_crg(db_fn, request=None):
    
    async def wrapper(request: Request):
        LOG.info("-- Generic handler --")
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams:RequestParams = RequestParams(**json_body).from_request(request)

        LOG.debug(f"Query Params = {qparams}")
        
        search_datasets = []
        authenticated=False
        
        access_token_header = request.headers.get('Authorization')
        access_token_cookies = request.cookies.get("Authorization")
        LOG.debug(f"Access token header = {access_token_header}")
        LOG.debug(f"Access token cookies = {access_token_cookies}")
        
        # set access_token as the one we recieve in the header
        # if not in header, get the one from cookies
        if access_token_header:
            access_token = access_token_header
        else:
            access_token = access_token_cookies
        
        if access_token is not None:
            with open("/beacon/beacon/request/public_datasets.yml", 'r') as stream:
                public_datasets = yaml.safe_load(stream)
            list_of_public_datasets= public_datasets['public_datasets']
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
            for public_dataset in list_of_public_datasets:
                authorized_datasets.append(public_dataset)
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
                        list_of_dataset_dicts.append(dict_dataset)
                
                for data_s in specific_datasets_unauthorized_and_found:
                    dict_dataset = {}
                    dict_dataset['dataset']=data_s
                    dict_dataset['ids'] = ['Unauthorized dataset']
                    list_of_dataset_dicts.append(dict_dataset)

                LOG.debug(specific_datasets_unauthorized_and_found)
                LOG.debug(specific_datasets_unauthorized)
                LOG.debug(f"list of datasets = {[e['dataset'] for e in list_of_dataset_dicts]}")

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
                LOG.debug(f"list of datasets = {[e['dataset'] for e in list_of_dataset_dicts]}")
            
            # -- end of if Authorized acess --
        
        else:
            #write here code for public datasets
            list_of_dataset_dicts=[]
            qparams.query.request_parameters = {}
            qparams.query.request_parameters['datasets'] = '*******'
            _, _, datasets = get_datasets(None, qparams)
            beacon_datasets = [ r for r in datasets ]
            with open("/beacon/beacon/request/public_datasets.yml", 'r') as stream:
                public_datasets = yaml.safe_load(stream)
            list_of_public_datasets= public_datasets['public_datasets']
            LOG.debug(f"Pub datasets = {list_of_public_datasets}")
            for data_r in list_of_public_datasets:
                dict_dataset = {}
                dict_dataset['dataset']=data_r
                dict_dataset['ids']=[ r['ids'] for r in beacon_datasets if r['id'] == data_r ]
                list_of_dataset_dicts.append(dict_dataset)
            LOG.debug(f"list of datasets = {[e['dataset'] for e in list_of_dataset_dicts]}")

            

        qparams = RequestParams(**json_body).from_request(request)
        

        entry_id = request.match_info.get('id', None)
        entity_schema, count, records = db_fn(entry_id, qparams)
        LOG.debug(f"schema = {entity_schema}")
        
        recordsList = list(records[0:100])
        recordsDebug = recordsList[0:10]
        LOG.debug(f"records = {recordsDebug}")
        
        # if it had at least one record
        if recordsDebug:
            LOG.debug(f"first record = {recordsDebug[0:1]}")
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




def filtering_terms_handler(db_fn, request=None):
    async def wrapper(request: Request):
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams = RequestParams(**json_body).from_request(request)
        entry_id = request.match_info.get('id', None)

        # Get response
        #_, _, records = db_fn(entry_id, qparams)
        #resources = ontologies.get_resources()
        #response = build_filtering_terms_response(records, resources, qparams)
        entity_schema, count, records = db_fn(entry_id, qparams)
        response = build_filtering_terms_response(records, count, qparams, lambda x, y: x, entity_schema)
        return await json_stream(request, response)

    return wrapper


# I don't know why this function was changed to look like this
# So I replaced it with an older version of it, the one above this
def filtering_terms_handler_auth(db_fn, request=None):
    async def wrapper(request: Request):
        # Get params
        json_body = await request.json() if request.method == "POST" and request.has_body and request.can_read_body else {}
        qparams = RequestParams(**json_body).from_request(request)

        LOG.debug(qparams)
        
        search_datasets = []
        authenticated=False

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

