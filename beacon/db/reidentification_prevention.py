import logging
import math

from pymongo import ReturnDocument
from beacon.db import client

LOG = logging.getLogger(__name__)

# support functions for the budget strategy

# update the budget of a specific individual for a user in the budget collection
def update_individual_budget(user_id, individual_id, amount):
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

def pvalue_strategy(access_token, records, qparams):
    helper = []
    total_cases = 0
    removed_individuals = []
    removed = False

    for record in records:
        individual_ids = set()
        individuals_to_remove = set()

        # step 4: compute the risk for that query: ri = -log(1 - Di)
        allele_frequency = record.get('alleleFrequency')
        N = client.beacon.get_collection('individuals').count_documents({})  # total number of individuals !! if user requestes dataset, N = individuals in that dataset
        Di = (1 - allele_frequency) ** (2 * N)
        ri = -(math.log10(1 - Di))
        LOG.debug(f"Query cost: {ri}")

        # fetch individualId from the biosample collection
        case_level_data = record.get('caseLevelData', [])
        for case in case_level_data:
            individual_id = case.get('biosampleId')  # biosampleId = individualId
            individual_ids.add(individual_id)

        for individualId in individual_ids:
            
            search_criteria = {
                "userId": access_token,
                "individualId": individualId
            }

            # Step 2: check if query has been asked before
            response_history = client.beacon['history'].find_one({"userId": access_token, "query": qparams.summary()})
            if response_history is not None:
                LOG.debug(f"Query was previously done by the same user")
                return response_history["response"], helper, total_cases, removed, removed_individuals  # Return stored answer if query was asked before by the same user

            # Step 3: check if there are records with bj > ri
            budget_info = client.beacon['budget'].find_one(search_criteria)
            if not budget_info:
                p_value = 0.5 # upper bound on test errors
                bj = -(math.log10(p_value))  # initial budget
                budget_info = {
                    "userId": access_token,
                    "individualId": individualId,
                    "budget": bj
                }
                client.beacon['budget'].insert_one(budget_info)

            # re-fetch the budget_info to ensure we have the latest data
            budget_info = client.beacon['budget'].find_one(search_criteria)

            if budget_info and budget_info['budget'] < ri:
                
                individuals_to_remove.add(individualId)
            else:
                if budget_info['budget'] >= ri:
                    # Step 7: reduce their budgets by ri
                    update_individual_budget(access_token, individualId, ri)
                    budget_info = client.beacon['budget'].find_one(search_criteria)

        if individuals_to_remove:
            # filter the individuals from the record
            removed = True
            removed_individuals = individuals_to_remove
            LOG.debug(f"Removed individuals: {list(individuals_to_remove)}") # signal to know which individuals have no more budget
            record['caseLevelData'] = [case for case in record['caseLevelData'] if case.get('biosampleId') not in individuals_to_remove]
            if  record['caseLevelData'] != []:
                helper.append(record)
        else:
            helper.append(record)
        
        total_cases += len(record['caseLevelData'])        

    return None, helper, total_cases, removed, removed_individuals


