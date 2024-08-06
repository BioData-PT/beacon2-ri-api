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
    
def get_random_genomic_variants(sample_size=1):
    # Get a random sample of genomic variants
    pipeline = [
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
    i = 0
    variant_removal_list = []
    
    start_time = time.time()
    
    while i < 100:
        count = 1
        var = 1
        
        # Clear budget and history collections before starting queries
        clear_budget_and_history_collections()
        
        while var == 1:
            
            variant_docs = get_random_genomic_variants()
            
            if not variant_docs:
                print("No genomic variants found in the database.")
                break
            
            for variant_doc in variant_docs:
                print(f"Variant number: {count}")
                count += 1
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
                    variant_removal_list.append(count - 2)
                    var = 0
                    break
                
                #print("Response:", stdout)
                #if stderr:
                #    print("Error:", stderr)
        i += 1
        
    end_time = time.time()  # End the timer
    
    # Calculate total time taken
    total_time = end_time - start_time
    
    print(variant_removal_list)
    print("Run complete. Variants where individuals were removed are stored in removed_variants.json.")
    print(f"Total time taken: {total_time} seconds")

if __name__ == "__main__":
    main()
