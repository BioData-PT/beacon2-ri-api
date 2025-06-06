from typing import Optional, Tuple, List, Dict, Set

from beacon import conf
from beacon.db.schemas import DefaultSchemas
from beacon.request import RequestParams
from beacon.request.model import Granularity

import logging

LOG = logging.getLogger(__name__)

def build_meta(qparams: RequestParams, entity_schema: Optional[DefaultSchemas], returned_granularity: Granularity):
    """"Builds the `meta` part of the response

    We assume that receivedRequest is the evaluated request (qparams) sent by the user.
    """

    meta = {
        'beaconId': conf.beacon_id,
        'apiVersion': conf.api_version,
        'returnedGranularity': returned_granularity,
        'receivedRequestSummary': qparams.summary(),
        'returnedSchemas': [entity_schema.value] if entity_schema is not None else []
    }
    return meta


def build_response_summary(exists, num_total_results):
    if num_total_results is None:
        return {
            'exists': exists
        }
    else:
        return {
            'exists': exists,
            'numTotalResults': num_total_results
        }


def build_generic_response(
    results_by_dataset:Dict[str,Tuple[int,list]], accessible_datasets:List[str], granularity:Granularity,
    qparams, entity_schema, is_registered:bool, is_authenticated:bool):

    """Builds the Beacon response, oculting the results from the required datasets.
    
    Receives results(count, records) of each queried dataset, authorized datasets, and granularity of results.
    """

    # iterate over all results to get:
    # total count
    # response by dataset

    num_total_results = 0
    response_list:List[Dict] = []
    for dataset_id in results_by_dataset:

        num_dataset_results = results_by_dataset[dataset_id][0]
        dataset_results = results_by_dataset[dataset_id][1]
        num_total_results += num_dataset_results
        
        dataset_response = {
            "id": dataset_id,
            "exists": num_dataset_results > 0,
            "setType": "dataset",
            "results": dataset_results,
            "resultsCount": num_dataset_results
        }
        
        # if dataset is not authorized, erase the records part
        if dataset_id not in accessible_datasets:
            dataset_response["results"] = []
            
        response_list.append(dataset_response)
    
    beacon_response = []
            
    beacon_response = {
        'meta': build_meta(qparams, entity_schema, granularity),
        'responseSummary': build_response_summary(num_total_results > 0, num_total_results),
        'beaconHandovers': conf.beacon_handovers,
        'response': {
            'resultSets': response_list
        }
    }
    

    return beacon_response

# not used at this moment
def build_response_by_dataset(data, response_dict, num_total_results, qparams, func):
    """"Fills the `response` part with the correct format in `results`"""
    list_of_responses=[]
    for k,v in response_dict.items():
        LOG.debug(len(v))
        response = {
            'id': k, # TODO: Set the name of the dataset/cohort
            'setType': 'dataset', # TODO: Set the type of collection
            'exists': len(v) > 0,
            'resultsCount': len(v),
            'results': v,
            # 'info': None,
            'resultsHandover': None,  # build_results_handover
        }
        list_of_responses.append(response)

    return list_of_responses

def build_response(data, num_total_results, qparams, func):
    """"Fills the `response` part with the correct format in `results`"""

    response = {
        'id': '', # TODO: Set the name of the dataset/cohort
        'setType': '', # TODO: Set the type of collection
        'exists': num_total_results > 0,
        'resultsCount': num_total_results,
        'results': data,
        # 'info': None,
        'resultsHandover': None,  # build_results_handover
    }

    return response


########################################
# Resultset Response
########################################
def build_beacon_resultset_response(data,
                                    num_total_results,
                                    qparams: RequestParams,
                                    func_response_type,
                                    entity_schema: DefaultSchemas):
    """"
    Transform data into the Beacon response format.
    """

    beacon_response = {
        'meta': build_meta(qparams, entity_schema, Granularity.RECORD),
        'responseSummary': build_response_summary(num_total_results > 0, num_total_results),
        # TODO: 'extendedInfo': build_extended_info(),
        'response': {
            'resultSets': [build_response(data, num_total_results, qparams, func_response_type)]
        },
        'beaconHandovers': conf.beacon_handovers,
    }
    return beacon_response

def build_beacon_resultset_response_by_dataset(data,
                                    list_of_dataset_dicts,
                                    num_total_results,
                                    qparams: RequestParams,
                                    func_response_type,
                                    entity_schema: DefaultSchemas):
    """"
    Transform data into the Beacon response format.
    """
    response_dict={}
    #LOG.debug(list_of_dataset_dicts)

    for dataset_dict in list_of_dataset_dicts:
        dataset_id = dataset_dict['dataset']
        response_dict[dataset_id] = []
    
    for dataset_dict in list_of_dataset_dicts:
        datas = dataset_dict['ids']
        try:
            biosample_list = datas[0]
        except Exception:
            biosample_list = []
            #for datas in dataset_dict['ids']:
        if isinstance(datas, str):
            dict_2={}
            dict_2['id']=datas
            dataset_id = dataset_dict['dataset']
            response_dict[dataset_id]=[]
            response_dict[dataset_id].append(dict_2)
            LOG.debug(response_dict)

        else:
            for doc in data:
                #LOG.debug(isinstance(doc,dict))
                #LOG.debug(doc)
                #convert doc to dict
                try:
                    if doc['id'] in biosample_list['biosampleIds']:
                        dataset_id = dataset_dict['dataset']
                        response_dict[dataset_id].append(doc)
                    elif doc['id'] in biosample_list['individualIds']:
                        dataset_id = dataset_dict['dataset']
                        response_dict[dataset_id].append(doc)
                except Exception:
                    pass


    
    beacon_response = {
        'meta': build_meta(qparams, entity_schema, Granularity.RECORD),
        'responseSummary': build_response_summary(num_total_results > 0, num_total_results),
        # TODO: 'extendedInfo': build_extended_info(),
        'response': {
            'resultSets': build_response_by_dataset(data, response_dict, num_total_results, qparams, func_response_type)
        },
        'beaconHandovers': conf.beacon_handovers,
    }
    return beacon_response

########################################
# Count Response
########################################

def build_beacon_count_response(data,
                                    num_total_results,
                                    qparams: RequestParams,
                                    func_response_type,
                                    entity_schema: DefaultSchemas):
    """"
    Transform data into the Beacon response format.
    """

    beacon_response = {
        'meta': build_meta(qparams, entity_schema, Granularity.COUNT),
        'responseSummary': build_response_summary(num_total_results > 0, num_total_results),
        # TODO: 'extendedInfo': build_extended_info(),
        'beaconHandovers': conf.beacon_handovers,
    }
    return beacon_response

########################################
# Boolean Response
########################################

def build_beacon_boolean_response(data,
                                    num_total_results,
                                    qparams: RequestParams,
                                    func_response_type,
                                    entity_schema: DefaultSchemas):
    """"
    Transform data into the Beacon response format.
    """

    beacon_response = {
        'meta': build_meta(qparams, entity_schema, Granularity.BOOLEAN),
        'responseSummary': build_response_summary(num_total_results > 0, None),
        # TODO: 'extendedInfo': build_extended_info(),
        'beaconHandovers': conf.beacon_handovers,
    }
    return beacon_response

########################################
# Collection Response
########################################

def build_beacon_collection_response(data, num_total_results, qparams: RequestParams, func_response_type, entity_schema: DefaultSchemas):
    beacon_response = {
        'meta': build_meta(qparams, entity_schema, Granularity.RECORD),
        'responseSummary': build_response_summary(num_total_results > 0, num_total_results),
        # TODO: 'info': build_extended_info(),
        'beaconHandovers': conf.beacon_handovers,
        'response': {
            'collections': func_response_type(data, qparams)
        }
    }
    return beacon_response

########################################
# Info Response
########################################

def build_beacon_info_response(data, qparams, func_response_type, authorized_datasets=None):
    if authorized_datasets is None:
        authorized_datasets = []

    beacon_response = {
        'meta': build_meta(qparams, None, Granularity.RECORD),
        'response': {
            'id': conf.beacon_id,
            'name': conf.beacon_name,
            'apiVersion': conf.api_version,
            'environment': conf.environment,
            'organization': {
                'id': conf.org_id,
                'name': conf.org_name,
                'description': conf.org_description,
                'address': conf.org_adress,
                'welcomeUrl': conf.org_welcome_url,
                'contactUrl': conf.org_contact_url,
                'logoUrl': conf.org_logo_url,
            },
            'description': conf.description,
            'version': conf.version,
            'welcomeUrl': conf.welcome_url,
            'alternativeUrl': conf.alternative_url,
            'createDateTime': conf.create_datetime,
            'updateDateTime': conf.update_datetime,
            'datasets': func_response_type(data, qparams, authorized_datasets),
        }
    }

    return beacon_response

########################################
# Service Info Response
########################################

def build_beacon_service_info_response():
    beacon_response = {
        'id': conf.beacon_id,
        'name': conf.beacon_name,
        'type': {
            'group': conf.ga4gh_service_type_group,
            'artifact': conf.ga4gh_service_type_artifact,
            'version': conf.ga4gh_service_type_version
        },
        'description': conf.description,
        'organization': {
            'name': conf.org_name,
            'url': conf.org_welcome_url
        },
        'contactUrl': conf.org_contact_url,
        'documentationUrl': conf.documentation_url,
        'createdAt': conf.create_datetime,
        'updatedAt': conf.update_datetime,
        'environment': conf.environment,
        'version': conf.version,
    }

    return beacon_response

########################################
# Filtering terms Response
########################################

def build_filtering_terms_response(data:List[Dict],
                                    num_total_results,
                                    qparams: RequestParams,
                                    func_response_type,
                                    entity_schema: DefaultSchemas):
    """"
    Transform data into the Beacon response format.
    """
    
    # TODO: Fix db values instead
    LOG.warning("WARNING: USING WRONG FILTERING TERMS SCHEMA, NEED TO REFACTOR THE CODE AND CREATE NEW VALUES IN DB")
    
    # argument is actually an iterable, need this to change the values
    data = list(data) 
    
    # Changing the format of the filtering terms response to respect BN
    # "scope" -> "scopes" 
    # str -> list
    # "individuals","cohorts","biosamples" -> "individual","cohort","biosample"
    for d in data:
        if "scope" in d:
            scope_original = d.pop("scope")
            d["scopes"] = [scope_original.removesuffix("s")]
        

    beacon_response = {
        'meta': build_meta(qparams, entity_schema, Granularity.RECORD),
        'responseSummary': build_response_summary(num_total_results > 0, num_total_results),
        # TODO: 'extendedInfo': build_extended_info(),
        'response': {
            'filteringTerms': data,
        },
        'beaconHandovers': conf.beacon_handovers,
    }
    return beacon_response
