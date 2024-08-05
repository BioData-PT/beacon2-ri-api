import os
import subprocess
import random
from pymongo import MongoClient
import json

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
    
    while True:
        variant_docs = get_random_genomic_variants()
        
        if not variant_docs:
            print("No genomic variants found in the database.")
            break
        
        for variant_doc in variant_docs:
            print(f"Querying variant id: {variant_doc['variantInternalId']}")
            variant_full_doc = collection.find_one({'variantInternalId': variant_doc['variantInternalId']})
            alt = variant_full_doc["variation"]["alternateBases"]
            ref = variant_full_doc["variation"]["referenceBases"]
            start = variant_full_doc["_position"]["startInteger"]
            end = variant_full_doc["_position"]["endInteger"]
            vType = variant_full_doc["variation"]['variantType']
            stdout, stderr = query_variant_with_curl(access_token, alt, ref, start, end, vType)
            print("Response:", stdout)
            if stderr:
                print("Error:", stderr)

if __name__ == "__main__":
    main()
