import logging
from typing import Dict, List, Optional
from beacon.db.filters import apply_alphanumeric_filter, apply_filters
from beacon.db.schemas import DefaultSchemas
from beacon.db.utils import query_id, query_ids, get_count, get_documents, get_cross_query, get_cross_query_variants, get_filtering_documents
from beacon.request.model import AlphanumericFilter, Operator, RequestParams
from beacon.db import client
import json
from bson import json_util
from aiohttp import web


LOG = logging.getLogger(__name__)

VARIANTS_PROPERTY_MAP = {
    "assemblyId": "_position.assemblyId",
    "referenceName": "_position.refseqId",
    "Chromosome": "_position.refseqId",
    "start": "_position.start",
    "end": "_position.end",
    "referenceBases": "variation.referenceBases",
    "alternateBases": "variation.alternateBases",
    "variantType": "variation.variantType",
    "variantMinLength": None,
    "variantMaxLength": None,
    "mateName": None,
    "geneId": "molecularAttributes.geneIds",
    "aachange": "molecularAttributes.aminoacidChanges",
    "aminoacidChange": "molecularAttributes.aminoacidChanges",
    "genomicAlleleShortForm":"genomicHGVSId"
}

def is_genomicallele_query(qparams: RequestParams) -> bool:
    """
    Check if the query is a genomic allele query (short form)
    """
    if qparams is None:
        return False
    
    LOG.debug(f"query = {qparams}")

    if "genomicAlleleShortForm" in qparams.query.request_parameters:
        return True

    return False

def is_aachange_query(qparams: RequestParams) -> bool:
    """
    Check if the query is an amino acid change query
    """
    if qparams is None:
        return False

    if "aminoacidChange" in qparams.query.request_parameters:
        return True

    return False

def is_sequence_query(qparams: RequestParams) -> bool:
    """
    Check if the query is a sequence query
    """
    if qparams is None:
        return False
    
    # check required parameters
    parameters = ("start", "referenceName", "alternateBases", "referenceBases")
    for param in parameters:
        if param not in qparams.query.request_parameters \
            or qparams.query.request_parameters.get(param) is None:
                
            return False

    # bracket query?
    failed_start_format = False
    start = qparams.query.request_parameters["start"]
    if not isinstance(start, int):
        if isinstance(start, list):
            if len(start) != 1: # it's a list but not a single-element
                failed_start_format = True
        else:
            # not an int nor list
            failed_start_format = True
    
    if failed_start_format:
        LOG.debug(f"not a sequence query: start is not an int or single-element array: {start} ({type(start)})")
        return False
    
    # region query?
    if "end" in qparams.query.request_parameters:
        LOG.debug(f"not a sequence query: 'end' key in request parameters")
        return False
    
    return True

def include_resultset_responses(query: Dict[str, List[dict]], qparams: RequestParams):
    LOG.debug("Include Resultset Responses = {}".format(qparams.query.include_resultset_responses))
    include = qparams.query.include_resultset_responses
    if include == 'HIT':
        query = query
    elif include == 'ALL':
        query = {}
    elif include == 'NONE':
        query = {'$text': {'$search': '########'}}
    else:
        query = query
    return query


def generate_position_filter_start(key: str, value: List[int], is_region_query:bool) -> List[AlphanumericFilter]:
    LOG.debug("len value = {}".format(len(value)))
    filters = []
    if len(value) == 1:
        if is_region_query:
            operator = Operator.GREATER_EQUAL
        else:
            operator = Operator.EQUAL
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=operator
        ))
    elif len(value) == 2:
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=Operator.GREATER_EQUAL
        ))
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[1]],
            operator=Operator.LESS_EQUAL
        ))
    return filters


def generate_position_filter_end(key: str, value: List[int], is_region_query:bool) -> List[AlphanumericFilter]:
    LOG.debug("len value = {}".format(len(value)))
    filters = []
    if len(value) == 1:
        if is_region_query:
            operator = Operator.LESS_EQUAL
        else:
            operator = Operator.EQUAL
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=operator
        ))
    elif len(value) == 2:
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[0]],
            operator=Operator.GREATER_EQUAL
        ))
        filters.append(AlphanumericFilter(
            id=VARIANTS_PROPERTY_MAP[key],
            value=[value[1]],
            operator=Operator.LESS_EQUAL
        ))
    return filters


def apply_request_parameters(query: Dict[str, List[dict]], qparams: RequestParams):
    collection = 'g_variants'
    LOG.debug("Request parameters len = {}".format(len(qparams.query.request_parameters)))
    # check if it is a region query (has start and end)
    is_region_query = True
    for param in ("start", "end"):
        if param not in qparams.query.request_parameters.keys():
            is_region_query = False
            break
    
    #LOG.debug(f"is_region_query = {is_region_query}")
    
    if len(qparams.query.request_parameters) > 0 and "$and" not in query:
        query["$and"] = []
    for k, v in qparams.query.request_parameters.items():
        if k == "start":
            if isinstance(v, str):
                v = v.split(',')
            filters = generate_position_filter_start(k, v, is_region_query)
            for filter in filters:
                query["$and"].append(apply_alphanumeric_filter({}, filter, collection))
        elif k == "end":
            if isinstance(v, str):
                v = v.split(',')
            filters = generate_position_filter_end(k, v, is_region_query)
            for filter in filters:
                query["$and"].append(apply_alphanumeric_filter({}, filter, collection))
        elif k == "variantMinLength" or k == "variantMaxLength" or k == "mateName":
            continue
        elif k == "datasets":
            pass
        else:
            try:
                query["$and"].append(apply_alphanumeric_filter({}, AlphanumericFilter(
                    id=VARIANTS_PROPERTY_MAP[k],
                    value=v
                ), collection))
            except KeyError:
                LOG.error(f"Invalid parameter: {k}")
                raise ValueError(f"Invalid parameter: {k}")
    return query


def get_variants(entry_id: Optional[str], qparams: RequestParams):
    collection = 'g_variants'
    query = apply_request_parameters({}, qparams)
    query = apply_filters(query, qparams.query.filters, collection)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.GENOMICVARIATIONS
    count = get_count(client.beacon.genomicVariations, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.genomicVariations,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.genomicVariations, negative_query)
    else:
        docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_variant_with_id(entry_id: Optional[str], qparams: RequestParams):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters, collection)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.GENOMICVARIATIONS
    count = get_count(client.beacon.genomicVariations, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.genomicVariations,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.genomicVariations, negative_query)
    else:
        docs = get_documents(
            client.beacon.genomicVariations,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_biosamples_of_variant(entry_id: Optional[str], qparams: RequestParams):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters)
    
    variantDoc = client.beacon.genomicVariations \
        .find_one(query)
    
    # extract biosample ids from g_variant document
    biosample_ids = []
    if "caseLevelData" in variantDoc:
        for case in variantDoc["caseLevelData"]:
            if "biosampleId" in case and case["biosampleId"]:
                biosample_ids.append(case["biosampleId"])
    
    # build query to find all matches for ids in biosample collection
    query = apply_request_parameters({}, qparams)
    query["id"] = {"$in": biosample_ids}
    query = apply_filters(query, qparams.query.filters)
    
    schema = DefaultSchemas.BIOSAMPLES
    
    # handle MISS case
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.biosamples,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.biosamples,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.biosamples, negative_query)
    else:
        # normal case (HIT)
        count = len(biosample_ids)
        docs = get_documents(
            client.beacon.biosamples,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )

    return schema, count, docs


def get_individuals_of_variant(entry_id: Optional[str], qparams: RequestParams):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters, collection)
    count = get_count(client.beacon.genomicVariations, query)
    individual_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})

    individual_ids = get_cross_query_variants(individual_ids,'biosampleId','id')
    query = apply_filters(individual_ids, qparams.query.filters, collection)

    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.INDIVIDUALS
    count = get_count(client.beacon.individuals, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.individuals,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.individuals,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.individuals, negative_query)
    else:
        docs = get_documents(
            client.beacon.individuals,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs

def get_runs_of_variant(entry_id: Optional[str], qparams: RequestParams):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters, collection)
    count = get_count(client.beacon.genomicVariations, query)
    run_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})
    
    run_ids=get_cross_query_variants(run_ids,'biosampleId','biosampleId')
    query = apply_filters(run_ids, qparams.query.filters, collection)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.RUNS
    count = get_count(client.beacon.runs, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.runs,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.runs,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.runs, negative_query)
    else:
        docs = get_documents(
            client.beacon.runs,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs


def get_analyses_of_variant(entry_id: Optional[str], qparams: RequestParams):
    collection = 'g_variants'
    query = {"$and": [{"variantInternalId": entry_id}]}
    query = apply_request_parameters(query, qparams)
    query = apply_filters(query, qparams.query.filters, collection)
    count = get_count(client.beacon.genomicVariations, query)
    analysis_ids = client.beacon.genomicVariations \
        .find_one(query, {"caseLevelData.biosampleId": 1, "_id": 0})

    analysis_ids=get_cross_query_variants(analysis_ids,'biosampleId','biosampleId')
    query = apply_filters(analysis_ids, qparams.query.filters, collection)
    query = include_resultset_responses(query, qparams)
    schema = DefaultSchemas.ANALYSES
    count = get_count(client.beacon.analyses, query)
    include = qparams.query.include_resultset_responses
    if include == 'MISS':
        pre_docs = get_documents(
            client.beacon.analyses,
            query,
            qparams.query.pagination.skip,
            count
        )
        negative_query={}
        ids_array = []
        for doc in pre_docs:
            elem_query={}
            elem_query['_id']=doc['_id']
            ids_array.append(elem_query)
        
        negative_query['$nor']=ids_array
        LOG.debug(negative_query)
        docs = get_documents(
            client.beacon.analyses,
            negative_query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
        count = get_count(client.beacon.analyses, negative_query)
    else:
        docs = get_documents(
            client.beacon.analyses,
            query,
            qparams.query.pagination.skip,
            qparams.query.pagination.limit
        )
    return schema, count, docs

def get_filtering_terms_of_genomicvariation(entry_id: Optional[str], qparams: RequestParams):
    query = {'scope': 'genomicVariations'}
    schema = DefaultSchemas.FILTERINGTERMS
    count = get_count(client.beacon.filtering_terms, query)
    remove_id={'_id':0}
    docs = get_filtering_documents(
        client.beacon.filtering_terms,
        query,
        remove_id,
        qparams.query.pagination.skip,
        qparams.query.pagination.limit
    )
    return schema, count, docs