import os
import subprocess
from pymongo import MongoClient

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
    
individuals_collection = client.beacon.get_collection('genomicVariations')
    
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

def main():
    i = 0
    access_token = input("Enter the access token: ")
    queried_individual_ids = set()
    
    while i < 100:
        count = 1
        var = 1
    
        # Clear budget and history collections before starting queries
        clear_budget_and_history_collections()
        
        individual = get_random_individual(queried_individual_ids)["id"]
        queried_individual_ids.add(individual['_id'])
        
        while var == 1:
        
            variant_ids = get_genomic_variants_for_individual(individual)
            
            # Try and query all the variants starting with the lower frequency ones and see when the individual is removed from the output
            if variant_ids:
                print(f"Variant number: {count}")
                count += 1
                print(f"The genomic variants for biosampleId {individual} are (sorted by alleleFrequency):")
                for vid in variant_ids:
                    variant_doc = collection.find_one({'variantInternalId': vid})
                    print(f"Querying variant id: {vid}")
                    alt = variant_doc["variation"]["alternateBases"]
                    ref = variant_doc["variation"]["referenceBases"]
                    start = variant_doc["_position"]["startInteger"]
                    end = variant_doc["_position"]["endInteger"]
                    vType = variant_doc["variation"]['variantType']
                    stdout, stderr = query_variant_with_curl(access_token, alt, ref, start, end, vType)
                    print("Removed individuals:", stdout)
                    if individual in stdout:
                        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                        print("The individual was removed")
                        print("!!!!!!!!!!!!!!!!!!!!!!!!!!!")
                        var = 0
                        break
                    if stderr:
                        print("Error:", stderr)
                        
        i += 1

if __name__ == "__main__":
    main()
