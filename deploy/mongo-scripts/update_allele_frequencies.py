import requests
from pymongo import MongoClient
import os

# function to format a single variant
def format_variant_for_search(variant):
    chromosome = variant["_position"]["refseqId"]
    start_position = variant["_position"]["startInteger"]
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]

    formatted_variant = f"{chromosome}-{start_position}-{reference_base}-{alternate_base}"
    return formatted_variant

# function to query gnomAD for allele frequency
def query_gnomad(formatted_variant):
    url = f"https://gnomad.broadinstitute.org/api/variant/{formatted_variant}?dataset=gnomad_r4"
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()
        allele_frequency = data.get("variant", {}).get("allele_freq", None)
        return allele_frequency
    return None

# connect to MongoDB
database_password = os.getenv('DB_PASSWD')

database_host = 'mongo'
database_port = 27017
database_user = 'root'
database_name = 'beacon'
database_auth_source = 'admin'
      
client = MongoClient(
    f"mongodb://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}?authSource={database_auth_source}"

)
db = client['beacon']
collection = db['g_variants']
print(f"collection = {collection}")

print(f"{collection.find_one()}")

# iterate over all variants, format them, query gnomAD, and update the database
for variant in collection.find():
    formatted_variant = format_variant_for_search(variant)
    print(formatted_variant)
    #allele_frequency = query_gnomad(formatted_variant)
    #if allele_frequency is not None:
     #   collection.update_one(
      #      {"variantInternalId": variant["variantInternalId"]},
       #     {"$set": {"allele_frequency": allele_frequency}}
        #)
        #print(f"Updated variant {formatted_variant} with allele frequency {allele_frequency}")
    #else:
     #   print(f"Failed to retrieve allele frequency for {formatted_variant}")

print("Finished updating allele frequencies.")
