import logging
from typing_extensions import Self

from pydantic import BaseModel
from strenum import StrEnum
from typing import List, Optional, Union
from beacon import conf
from humps.main import camelize
from aiohttp.web_request import Request

LOG = logging.getLogger(__name__)


class CamelModel(BaseModel):
    class Config:
        alias_generator = camelize
        allow_population_by_field_name = True


class IncludeResultsetResponses(StrEnum):
    ALL = "ALL",
    HIT = "HIT",
    MISS = "MISS",
    NONE = "NONE"


class Similarity(StrEnum):
    EXACT = "exact",
    HIGH = "high",
    MEDIUM = "medium",
    LOW = "low"


class Operator(StrEnum):
    EQUAL = "=",
    LESS = "<",
    GREATER = ">",
    NOT = "!",
    LESS_EQUAL = "<=",
    GREATER_EQUAL = ">="

class Granularity(StrEnum):
    BOOLEAN = "boolean",
    COUNT = "count",
    RECORD = "record"
    
    # returns the lower granularity between 2 granularities
    def get_lower(g1, g2):
        """Returns the lower level of granularity between the 2 given"""
        
        if not isinstance(g1, Granularity):
            LOG.error(f"First value is not granularity: {g1.__repr__}")
            raise ValueError("One of the values is not a granularity object")
        if not isinstance(g2, Granularity):
            LOG.error(f"Second value is not granularity: {g2.__repr__}")
            raise ValueError("One of the values is not a granularity object")
        
        this_value = g1.value
        other_value = g2.value
        
        # iterate over the possible values of granularity from lower to higher
        # when it matches one of the args, returns
        for granularity_level in (Granularity.BOOLEAN, Granularity.COUNT, Granularity.RECORD):
            if granularity_level.value in (g1.value, g2.value):
                return granularity_level

class OntologyFilter(CamelModel):
    id: str
    scope: Optional[str] = None
    include_descendant_terms: bool = False
    similarity: Similarity = Similarity.EXACT


class AlphanumericFilter(CamelModel):
    id: str
    value: Union[str, List[int]]
    scope: Optional[str] = None
    operator: Operator = Operator.EQUAL


class CustomFilter(CamelModel):
    id: str
    scope: Optional[str] = None


class Pagination(CamelModel):
    skip: int = 0
    limit: int = 10


class RequestMeta(CamelModel):
    requested_schemas: List[str] = []
    api_version: str = conf.api_version


class RequestQuery(CamelModel):
    filters: List[dict | str] = []
    include_resultset_responses: IncludeResultsetResponses = IncludeResultsetResponses.HIT
    pagination: Pagination = Pagination()
    request_parameters: dict = {}
    test_mode: bool = False
    requested_granularity: Granularity = Granularity(conf.default_beacon_granularity)


class RequestParams(CamelModel):
    meta: RequestMeta = RequestMeta()
    query: RequestQuery = RequestQuery()

    def from_request(self, request: Request) -> Self:
        
        # GET request or POST but without body
        if request.method == "GET" or \
            request.method == "POST" and (not request.has_body or not request.can_read_body):
            
            for k, v in request.query.items():
                LOG.debug(f"Request query parameter {k} = {v}")
                if k == "requestedSchema":
                    self.meta.requested_schemas = [v]
                elif k == "skip":
                    self.query.pagination.skip = int(v)
                elif k == "limit":
                    self.query.pagination.limit = int(v)
                elif k == "includeResultsetResponses":
                    self.query.include_resultset_responses = IncludeResultsetResponses(v)
                else:
                    # all other request parameters
                    self.query.request_parameters[k] = v
        
        # convert start and end to an integer array
        for k,v in self.query.request_parameters.items():
            if k in ("start", "end"):
                    if isinstance(v, str):
                        res = []
                        for item in v.split(","):
                            res.append(int(item))
                        self.query.request_parameters[k] = res
                        LOG.debug(f"Request query parameter {k} = {res}")
                    elif isinstance(v, int):
                        self.query.request_parameters[k] = [v]
                        
        return self

    def summary(self):
        
        # convert filters to list of strings
        if self.query.filters: # filters in POST (json)
            #LOG.debug(f"query Filters = {self.query.filters}")
            
            filters_dict = self.query.filters
            filters = []
            for filter in filters_dict:
                #LOG.debug(f"Filter type = {type(filter)}")
                
                filter_str = filter_to_str(filter)
                filters.append(filter_str)
                
        else: # filters in URL (e.g. ?filters=NCIT:C20197,NCIT:C16576)
            filters = []
            filters_req = self.query.request_parameters.get("filters", [])
            #LOG.debug(f"req Filters = {filters_req}")
            if isinstance(filters_req, str):
                filters = list(filters_req.split(","))
            else:
                filters = filters_req
        
        #LOG.debug(f"Filter summary = {filters}")
        
        return {
            "apiVersion": self.meta.api_version,
            "requestedSchemas": self.meta.requested_schemas,
            "filters": filters,
            "requestParameters": self.query.request_parameters,
            "includeResultsetResponses": self.query.include_resultset_responses,
            "pagination": self.query.pagination.dict(),
            "requestedGranularity": self.query.requested_granularity,
            "testMode": self.query.test_mode
        }
        
def filter_to_str(filter_dict):
    if "id" not in filter_dict:
        raise ValueError(f"Unrecognized filter: {filter_dict}")
    
    if "value" not in filter_dict:
        # just id
        return f"{filter_dict['id']}"
    
    if "operator" not in filter_dict:
        # add default operator (=)
        return f"{filter_dict['id']}={filter_dict['value']}"
    
    return f"{filter_dict['id']}{filter_dict['operator']}{filter_dict['value']}"
