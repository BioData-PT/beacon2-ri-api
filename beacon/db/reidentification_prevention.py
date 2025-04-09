import logging
import math

from pymongo import ReturnDocument
from beacon.db import client

LOG = logging.getLogger(__name__)

# support functions for the budget strategy

def update_individual_budget(user_id, individual_id, amount):
    """Updates the budget of a specific individual for a user in the budget collection.
    
    Returns the new DB document"""
    try:
        budget_collection = client.beacon['budget']
        #LOG.debug(f"Updating budget for individual_id={individual_id} by amount={amount}")

        # Find the document and update it, returning the updated document
        updated_document = budget_collection.find_one_and_update(
            {"individualId": individual_id, "userId": user_id},
            {"$inc": {"budget": -amount}},
            return_document=ReturnDocument.AFTER  # Return the updated document
        )

        return updated_document

    except Exception as e:
        LOG.error(f"Error updating budget: {str(e)}")
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
        N = client.beacon.get_collection('individuals').estimated_document_count()  # total number of individuals !! if user requestes dataset, N = individuals in that dataset
        Di = (1 - allele_frequency) ** (2 * N)
        ri = -(math.log10(1 - Di))
        LOG.debug(f"Query cost: {ri}")

        # fetch individualId from the biosample collection
        case_level_data = record.get('caseLevelData', [])
        for case in case_level_data:
            individual_id = case.get('biosampleId')  # biosampleId = individualId
            individual_ids.add(individual_id)

        for individual_id in individual_ids:
            
            search_criteria = {
                "userId": user_id,
                "individualId": individual_id
            }

            # Step 2: check if query has been asked before
            response_history = client.beacon['history'].find_one({"userId": user_id, "query": qparams.summary()})
            if response_history is not None:
                LOG.debug(f"Query was previously done by the same user")
                # Return stored answer if query was asked before by the same user
                return response_history["response"], helper, total_cases, removed, removed_individuals

            # Step 3: check if there are records with bj > ri
            budget_info = client.beacon['budget'].find_one(search_criteria)
            if not budget_info:
                p_value = 0.5 # upper bound on test errors
                bj = -(math.log10(p_value))  # initial budget
                budget_info = {
                    "userId": user_id,
                    "individualId": individual_id,
                    "budget": bj
                }
                client.beacon['budget'].insert_one(budget_info)

            # re-fetch the budget_info to ensure we have the latest data
            budget_info = client.beacon['budget'].find_one(search_criteria)

            if budget_info and budget_info['budget'] < ri:
                
                individuals_to_remove.add(individual_id)
            else:
                if budget_info['budget'] >= ri:
                    # Step 7: reduce their budgets by ri
                    update_individual_budget(user_id, individual_id, ri)
                    budget_info = client.beacon['budget'].find_one(search_criteria)

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
    Checks if query is cached
    Censors reponse (if needed) using RIP algorithm
    Updates the user's budget for the targeted individuals
    """
    