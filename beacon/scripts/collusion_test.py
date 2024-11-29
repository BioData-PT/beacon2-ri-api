import math
import os
import subprocess
from pymongo import MongoClient, ReturnDocument


# connect to MongoDB
database_password = os.getenv('DB_PASSWD')

client = MongoClient(
    "mongodb://{}:{}@{}:{}/{}?authSource={}".format(
        "root",
        database_password,
        "db",
        27017,
        "beacon",
        "admin"
    )
)

collection = client.beacon.get_collection('genomicVariations')


def clear_budget_and_history_collections():
    client.beacon.get_collection('budget').delete_many({})
    client.beacon.get_collection('history').delete_many({})
    print("Cleared budget and history collections.")
    
individuals_collection = client.beacon.get_collection('individuals')
    
def get_random_individual(exclude_ids=set()):
    # Get a random individual document excluding already selected ones
    pipeline = [
        {"$match": {"_id": {"$nin": list(exclude_ids)}}},
        {"$sample": {"size": 1}}
    ]
    return list(individuals_collection.aggregate(pipeline))
    

def get_genomic_variants_for_individual(biosample_id):

    # query to find all genomic variants for the given biosampleId = individualId
    query = {'caseLevelData.biosampleId': biosample_id}

    # find the genomic variants and sort by alleleFrequency (ascending order)
    genomic_variants = collection.find(query, {'variantInternalId': 1, 'alleleFrequency': 1}).sort('alleleFrequency', 1)

    # extract the id of those genomic variants
    variant_ids = [variant['variantInternalId'] for variant in genomic_variants]

    return variant_ids

def query_variant_with_curl(access_token, alt, ref, start, end, vType):
    # Construct the curl command
    curl_command = [
    'curl',
    '-H', 'Content-Type: application/json',
    '-X', 'POST',
    '-H', f'Authorization: Bearer {access_token}',
    '-d', f'''{{
        "meta": {{
            "apiVersion": "2.0"
        }},
        "query": {{
            "requestParameters": {{
                "alternateBases": "{alt}",
                "referenceBases": "{ref}",
                "start": [{start}],
                "end": [{end}],
                "variantType": "{vType}"
            }},
            "filters": [],
            "includeResultsetResponses": "HIT",
            "pagination": {{
                "skip": 0,
                "limit": 10
            }},
            "testMode": false,
            "requestedGranularity": "record"
        }}
    }}''',
    'http://localhost:5050/api/g_variants/'
]


    # Execute the curl command and capture the output
    result = subprocess.run(curl_command, capture_output=True, text=True)
    return result.stdout, result.stderr


def update_user_budget_to_initial(individual_id, bt):
        budget_collection = client.beacon['budget']
        budget_doc = client.beacon.get_collection('budget').find_one({"individualId": individual_id})
        if budget_doc is None:
            print(f"No budget document found for individualId: {individual_id}")
            return  # Or handle this scenario appropriately
        print("O BUDGET È ESTEEEEEEEEE:", bt)
        print("111111:", client.beacon.get_collection('budget').find_one({"individualId": individual_id})['budget'])
        #LOG.debug(f"Updating budget for individual_id={individual_id} by amount={amount}")

        # Find the document and update it, returning the updated document
        budget_collection.find_one_and_update(
            {"individualId": individual_id},
            {"$inc": {"budget": (-math.log10(0.5) - bt)}}
        )
        
        print("222222:", client.beacon.get_collection('budget').find_one({"individualId": individual_id})['budget'])
    
    
    
def main():
    access_token = input("Enter the access token: ")
    #individual_ids = ["NA19755", "HG01767", "HG01440", "HG01302", "NA20287", "NA20528", "NA18633", "NA19247", "HG01403", "HG00138",
     #                 "HG03259", "HG01915", "HG01761", "NA19209", "NA18945", "NA12413", "HG00245", "HG00110", "HG02345", "NA19074",
      #                "HG02322", "HG00332", "NA19332", "HG03074", "HG01374", "HG01776", "NA19159", "NA19443", "HG00437", "HG00349",
       #               "HG00254", "NA20357", "HG02583", "HG01271", "HG00139", "NA19222", "NA19057", "HG03572", "HG01383", "NA12273",
        #              "HG03919", "HG01800", "NA20334", "HG00620", "HG02009", "HG01398", "HG00662", "HG03871", "HG03086", "HG03079",
         #             "HG00736", "HG00328", "NA19375", "HG02051", "HG03640", "HG00181", "HG03019", "HG00176", "HG02786", "HG01686",
          #            "HG00106", "HG03295", "HG01890", "HG00123", "HG03446", "HG03271", "HG00338", "HG03048", "HG03838", "NA19701", 
           #           "HG02787", "HG03476", "NA18562", "HG01811", "HG01275", "HG02470", "NA21099", "NA18933", "HG00324", "HG01277",
            #          "HG01979", "HG01253", "HG04038", "HG04186", "HG00378", "NA19403", "HG02813", "HG02277", "NA18519", "NA11843",
             #         "NA19310", "NA20809", "NA20525", "NA19334", "HG01254", "HG00553", "NA18613", "HG02655", "HG00513", "NA12006"]

    individual_ids = ["NA19755"]

    response = {}

    for individual_id in individual_ids:
        var_count = 0
        user_count = 1
        current_budget = -(math.log10(0.5))
        total_risk = -(math.log10(0.1))
        
        # Clear budget and history collections before starting queries
        clear_budget_and_history_collections()

        variant_ids = get_genomic_variants_for_individual(individual_id)
        print(f"Processing individual: {individual_id}")

        # Try and query all the variants starting with the lower frequency ones
        if variant_ids:
            print(f"The genomic variants for biosampleId {individual_id} are (sorted by alleleFrequency):")
            for vid in variant_ids:
                var_count += 1
                variant_doc = collection.find_one({'variantInternalId': vid})
                print(f"Querying variant id: {vid}")
                alt = variant_doc["variation"]["alternateBases"]
                ref = variant_doc["variation"]["referenceBases"]
                start = variant_doc["_position"]["startInteger"]
                end = variant_doc["_position"]["endInteger"]
                vType = variant_doc["variation"]['variantType']
                stdout, stderr = query_variant_with_curl(access_token, alt, ref, start, end, vType)
                print("THE BUDGET OF THE INDIVIDUAL IS BEGIN: ", client.beacon.get_collection('budget').find_one({"individualId": individual_id})['budget'])
                if individual_id in stdout:
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print(f"The individual {individual_id} was removed in variant number {var_count}")
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    bt = client.beacon.get_collection('budget').find_one({"individualId": individual_id})['budget']
                    print("THE BUDGET OF THE INDIVIDUAL IS: ", bt)
                    total_risk -= (current_budget - client.beacon.get_collection('budget').find_one({"individualId": individual_id})['budget'])
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print("The total risk is now: ", total_risk)
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    if total_risk <= 0:
                        print("The number of users after the re-identification limit is: ", user_count)
                        break
                    user_count += 1
                    clear_budget_and_history_collections()
                    update_user_budget_to_initial(individual_id, bt)
                    budget_info = client.beacon.get_collection('budget').find_one({"individualId": individual_id})['budget']
                    print("The budget is now QUERO VER ISTO: ", budget_info)
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                    print("THE NUMBER OF USERS IS NOW:", user_count)
                    print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                if stderr:
                    print("Error:", stderr)

        response[individual_id] = user_count
        print(response)

if __name__ == "__main__":
    main()
