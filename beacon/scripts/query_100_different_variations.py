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
    queried_variant_ids = {'chr22_16139740_A_G', 'chr22_16136506_G_T', 'chr22_16064261_C_T', 'chr22_16063481_TAA_T', 'chr22_16133452_G_C', 'chr22_16058056_C_T', 
                           'chr22_16123353_G_A', 'chr22_16059343_G_A', 'chr22_16062988_C_T', 'chr22_16065307_C_T', 'chr22_16054424_C_T', 'chr22_16055127_G_A', 
                           'chr22_16086492_T_G', 'chr22_16050954_G_A', 'chr22_16119409_G_A', 'chr22_16057172_G_A', 'chr22_16135992_G_C', 'chr22_16063219_C_G', 
                           'chr22_16053127_C_T', 'chr22_16057850_G_A', 'chr22_16096647_C_T', 'chr22_16085285_G_A', 'chr22_16057320_G_A', 'chr22_16064133_T_G', 
                           'chr22_16070681_T_C', 'chr22_16123467_C_T', 'chr22_16138596_A_G', 'chr22_16054248_C_A', 'chr22_16135601_T_A', 'chr22_16053458_G_C', 
                           'chr22_16050115_G_A', 'chr22_16071624_A_G', 'chr22_16126752_C_T', 'chr22_16123403_C_T', 'chr22_16080425_T_C', 'chr22_16061902_C_A', 
                           'chr22_16057417_C_T', 'chr22_16067722_C_T', 'chr22_16081610_A_G', 'chr22_16081589_C_T', 'chr22_16058809_C_T', 'chr22_16054646_T_C', 
                           'chr22_16056801_G_T', 'chr22_16059009_G_C', 'chr22_16066781_T_C', 'chr22_16115378_T_A', 'chr22_16110847_C_A', 'chr22_16069481_G_A', 
                           'chr22_16069783_T_A', 'chr22_16071205_A_G', 'chr22_16115374_C_G', 'chr22_16052872_G_C', 'chr22_16055268_G_A', 'chr22_16123182_C_T', 
                           'chr22_16061872_C_T', 'chr22_16096583_G_C', 'chr22_16063314_C_T', 'chr22_16063513_T_C', 'chr22_16115047_A_G', 'chr22_16122898_G_C', 
                           'chr22_16065812_A_G', 'chr22_16081593_G_C', 'chr22_16098399_G_C', 'chr22_16050678_C_T', 'chr22_16114253_C_T', 'chr22_16056725_C_A', 
                           'chr22_16055294_G_A', 'chr22_16130498_A_T', 'chr22_16120001_G_A', 'chr22_16056518_G_A', 'chr22_16061949_G_C', 'chr22_16073412_G_A', 
                           'chr22_16069307_G_A', 'chr22_16060627_C_T', 'chr22_16062837_C_T', 'chr22_16054839_G_A', 'chr22_16115182_T_A', 'chr22_16072330_G_A', 
                           'chr22_16053812_T_C', 'chr22_16065004_G_A', 'chr22_16062297_C_T', 'chr22_16052097_G_A', 'chr22_16064462_C_A', 'chr22_16059063_A_C', 
                           'chr22_16053260_T_C', 'chr22_16053659_A_C', 'chr22_16059952_G_A', 'chr22_16056936_C_T', 'chr22_16078632_G_A', 'chr22_16136556_G_A', 
                           'chr22_16059796_A_C', 'chr22_16050972_G_A', 'chr22_16066033_G_T', 'chr22_16129025_C_T', 'chr22_16073296_G_C', 'chr22_16127413_G_A', 
                           'chr22_16051477_C_A', 'chr22_16067164_G_A', 'chr22_16052384_G_C', 'chr22_16055725_G_A'}
    
    start_time = time.time()
        
    # Clear budget and history collections before starting queries
    clear_budget_and_history_collections()
            
        
    for variant_id in queried_variant_ids:
        
        print(f"Querying variant id: {variant_id}")
        variant_full_doc = collection.find_one({'variantInternalId': variant_id})
        alt = variant_full_doc["variation"]["alternateBases"]
        ref = variant_full_doc["variation"]["referenceBases"]
        start = variant_full_doc["_position"]["startInteger"]
        end = variant_full_doc["_position"]["endInteger"]
        vType = variant_full_doc["variation"]['variantType']
        stdout, stderr = query_variant_with_curl(access_token, alt, ref, start, end, vType)
        
        print(stdout)
        
        
    end_time = time.time()  # End the timer
    
    # Calculate total time taken
    total_time = end_time - start_time
    
    print(queried_variant_ids)
    print("Run complete. Variants where individuals were removed are stored in removed_variants.json.")
    print(f"Total time taken: {total_time} seconds")

if __name__ == "__main__":
    main()
