import logging
import math
from os import getenv

from pymongo import ReturnDocument
from beacon.db import client

LOG = logging.getLogger(__name__)

FIELD_INDIVIDUAL_ID = "individualId"
FIELD_USER_ID = "userId"
FIELD_DATASET_ID = "datasetId"
FIELD_BUDGET = "budget"
FIELD_QUERY = "query"

P_VALUE = float(getenv("RIP_P_VALUE",default=0.1))
INITIAL_BUDGET = -(math.log10(P_VALUE))  # initial budget

# support functions for the budget strategy

def update_individual_budget(user_id, individual_id, dataset_id, amount):
    """Updates the budget of a specific individual for a user in the budget collection.
    
    Returns the new DB document, or None if there is not enough budget. May throw an Exception
    
    There is a race condition in this procedure if two different queries are
    being ran at the same time for the same individual. If that happens,
    both queries may fail even though there is enough budget for one of them.
    This isn't a big deal, and is arguably better than locking a transaction
    or running the risk of permitting too many queries."""
    
    # try to find and update document
    def find_and_modify_document(amount):
        # Find the document and update it, returning the updated document
        updated_document = budget_collection.find_one_and_update(
            {
                FIELD_INDIVIDUAL_ID: individual_id,
                FIELD_USER_ID: user_id,
                FIELD_DATASET_ID: dataset_id
            },
            {
                "$inc": {FIELD_BUDGET: -amount}
            },
            return_document=ReturnDocument.AFTER  # Return the updated document
        )
        return updated_document
    
    # try to create document (can return unique-related error)
    def create_budget_document():
        new_doc = {
          FIELD_INDIVIDUAL_ID: individual_id,
          FIELD_USER_ID: user_id,
          FIELD_DATASET_ID: dataset_id,
          FIELD_BUDGET: INITIAL_BUDGET - amount
        }
        client.beacon['budget'].insert_one(new_doc)
        return new_doc
    
    try:
        budget_collection = client.beacon['budget']
        #LOG.debug(f"Updating budget for individual_id={individual_id} by amount={amount}")
        # try to find and update document
        updated_document = find_and_modify_document(amount)
        # try to create document if it doesn't exist yet
        if updated_document is None:
            try:
                new_doc = create_budget_document()
            except Exception as e:
                # another thread created the document
                # try to find and modify it again
                updated_document = find_and_modify_document(amount)
        
        # not found again, something is wrong
        if updated_document is None:
            LOG.error(f"Couldn't create nor find document: {new_doc}")
            raise Exception("Couldn't get nor find budget document")
        res_budget = updated_document[FIELD_BUDGET]
        # not enough budget, might need to increment it back
        if res_budget < 0:
            # there might be enough budget for other queries
            # so, we need to increment it back
            if res_budget + amount >= 0:
                find_and_modify_document(-amount)
            # Budget below zero anyway, no point incrementing
            #else:
            #    pass
            return None
        
        return updated_document

    except Exception as e:
        LOG.error(f"Unexpected error updating budget: {str(e)}")
        return None

def pvalue_strategy(user_id, records, qparams):
    helper = []
    total_cases = 0
    removed_individuals = []
    removed = False

    for record in records:
        individual_ids = set()
        individuals_to_remove = set()

        # step 4: compute the risk for that query: ri = -log(1 - Di)
        allele_frequency = record.get('alleleFrequency')
        # total number of individuals
        N = client.beacon.get_collection('individuals').estimated_document_count() 
        Di = (1 - allele_frequency) ** (2 * N)
        ri = -(math.log10(1 - Di))
        LOG.debug(f"Query RIP cost: {ri}")

        # fetch individualId from the biosample collection
        case_level_data = record.get('caseLevelData', [])
        for case in case_level_data:
            individual_id = case.get('biosampleId')  # biosampleId = individualId
            individual_ids.add(individual_id)

        for individual_id in individual_ids:
            
            budget_search_criteria = {
                FIELD_USER_ID: user_id,
                FIELD_INDIVIDUAL_ID: individual_id
            }

            # Step 2: check if query has been asked before
            response_history = client.beacon['history'].find_one({
                FIELD_USER_ID: user_id, 
                FIELD_QUERY: qparams.summary()
            })
            if response_history is not None:
                LOG.debug(f"Query was previously done by the same user")
                # Return stored answer if query was asked before by the same user
                return response_history["response"], helper, total_cases, removed, removed_individuals

            # Step 3: check if there are records with bj > ri
            budget_info = client.beacon['budget'].find_one(budget_search_criteria)
            if not budget_info:
                
                budget_info = {
                    FIELD_USER_ID: user_id,
                    FIELD_INDIVIDUAL_ID: individual_id,
                    FIELD_BUDGET: INITIAL_BUDGET
                }
                client.beacon['budget'].insert_one(budget_info)

            # re-fetch the budget_info to ensure we have the latest data
            budget_info = client.beacon['budget'].find_one(budget_search_criteria)

            if budget_info and budget_info['budget'] < ri:
                
                individuals_to_remove.add(individual_id)
            else:
                if budget_info['budget'] >= ri:
                    # Step 7: reduce their budgets by ri
                    update_individual_budget(user_id, individual_id, ri)
                    budget_info = client.beacon['budget'].find_one(budget_search_criteria)

        if individuals_to_remove:
            # filter the individuals from the record
            removed = True
            removed_individuals = individuals_to_remove
            LOG.debug(f"Removed individuals: {list(individuals_to_remove)}") # signal to know which individuals have no more budget
            record['caseLevelData'] = [case for case in record['caseLevelData'] if case.get('biosampleId') not in individuals_to_remove]
            if record['caseLevelData'] != []:
                helper.append(record)
        else:
            helper.append(record)
        
        total_cases += len(record['caseLevelData'])        

    return None, helper, total_cases, removed, removed_individuals


def apply_rip_logic(query, query_results, is_authenticated, is_registered, dataset_is_accessible, dataset_id):
    """
    Checks if the query is a sequence or gene query.
    Checks if query is cached
    Censors reponse (if needed) using RIP algorithm
    Updates the user's budget for the targeted individuals
    """
    