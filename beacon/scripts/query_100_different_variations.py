import os
import subprocess
from pymongo import MongoClient
import time

# Connect to MongoDB
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
    
def get_random_genomic_variants(exclude_ids, sample_size=1):
    # Get a random sample of genomic variants excluding already queried ones
    pipeline = [
        {"$match": {"variantInternalId": {"$nin": exclude_ids}}},
        {"$sample": {"size": sample_size}},
        {"$project": {"variantInternalId": 1, "alleleFrequency": 1}}
    ]
    return list(collection.aggregate(pipeline))

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
    access_token = input("Enter the access token: ")
    queried_variant_ids = set()  # To track queried variants
    
    start_time = time.time()
    count = 0
    
    while count < 100:
        
        # Clear budget and history collections before starting queries
        clear_budget_and_history_collections()
            
        variant_docs = get_random_genomic_variants(list(queried_variant_ids))
            
        if not variant_docs:
            print("No genomic variants found in the database.")
            break
        
        for variant_doc in variant_docs:
            queried_variant_ids.add(variant_doc['variantInternalId'])  # Add to queried set
            
            print(f"Variant number: {count}")
            print(f"Querying variant id: {variant_doc['variantInternalId']}")
            variant_full_doc = collection.find_one({'variantInternalId': variant_doc['variantInternalId']})
            alt = variant_full_doc["variation"]["alternateBases"]
            ref = variant_full_doc["variation"]["referenceBases"]
            start = variant_full_doc["_position"]["startInteger"]
            end = variant_full_doc["_position"]["endInteger"]
            vType = variant_full_doc["variation"]['variantType']
            stdout, stderr = query_variant_with_curl(access_token, alt, ref, start, end, vType)
            
            print(stdout)
            if stdout == "true":
                print(f"Individuals were removed")
            
        count += 1
        
    end_time = time.time()  # End the timer
    
    # Calculate total time taken
    total_time = end_time - start_time
    
    print(queried_variant_ids)
    print("Run complete. Variants where individuals were removed are stored in removed_variants.json.")
    print(f"Total time taken: {total_time} seconds")

if __name__ == "__main__":
    main()
