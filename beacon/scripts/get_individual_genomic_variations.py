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
        '-H', f"Authorization: Bearer {access_token}",
        '-d', f'''{{
            "meta": {{
                "apiVersion": "2.0"
            }},
            "query": {{
                "requestParameters": {
                f"alternateBases: {alt}" ,
                f"referenceBases: {ref}" ,
                f"start: [ {start} ]",
                f"end: [ {end} ]",
                f"variantType: {vType}"
        },,
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
    biosample_id = input("Enter the individualId to search: ")
    variant_ids = get_genomic_variants_for_individual(biosample_id)
    
    # Try and query all the variants starting with the lower frequency ones and see when the individual is removed from the output
    if variant_ids:
        print(f"The genomic variants for biosampleId {biosample_id} are (sorted by alleleFrequency):")
        for vid in variant_ids:
            variant_doc = collection.find_one({'variantInternalId': vid})
            print(f"Querying variant id: {vid}")
            alt = variant_doc["variation"]["alternateBases"]
            print(f"ALT: {alt}")
            ref = variant_doc["variation"]["referenceBases"]
            print(f"REF: {ref}")
            start = variant_doc["_position"]["startInteger"]
            print(f"START: {start}")
            end = variant_doc["_position"]["endInteger"]
            print(f"END: {end}")
            vType = variant_doc["variation"]['variantType']
            print(f"TYPE: {vType}")
            stdout, stderr = query_variant_with_curl(access_token, alt, ref, start, end, vType)
            print("Response:", stdout)
            if stderr:
                print("Error:", stderr)
    else:
        print(f"No genomic variants found for individualId {biosample_id}")

if __name__ == "__main__":
    main()
