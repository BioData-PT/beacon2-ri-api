import requests, sys
from pymongo import MongoClient
import os
import time


# Function to query 1000 Genomes for allele frequency
def query_gnomad(chrom, start, ref, alt):
    server = "https://gnomad.broadinstitute.org/api"
    ext = f"/v3/variant/{chrom}-{start}-{ref}-{alt}"
    
    url = server + ext
    response = requests.get(url)
    
    if response.status_code == 200:
        data = response.json()
        return data
    else:
        print(f"Error querying gnomAD API: {response.status_code}")
        return None
    
    
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

# Iterate over all variants, format them, query 1000 Genomes, and update the database
for variant in collection.find():
    chromosome = variant["_position"]["refseqId"]
    start_position = variant["_position"]["startInteger"]
    end_position = variant["_position"]["endInteger"]
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]
    hgvs_notation = variant["identifiers"]["genomicHGVSId"]
    
    formatted_variant = f"{chromosome}-{start_position}-{end_position}-{reference_base}-{alternate_base}"
    print("-----------")
    print(f"{formatted_variant}")
    try:
        # Query 1000 Genomes for allele frequency
        allele_frequency = query_gnomad(chromosome, start_position, reference_base, alternate_base)
        print(allele_frequency)
        if allele_frequency is not None:
            collection.update_one(
                {"variantInternalId": variant["variantInternalId"]},
                {"$set": {"alleleFrequency": allele_frequency}}
            )
            print(f"Updated variant {formatted_variant} with allele frequency {allele_frequency}")
        else:
           print(f"Failed to retrieve allele frequency for {formatted_variant}")
    except ValueError as e:
        print(str(e))
        continue
    except Exception as e:
        print(f"Failed to process variant {formatted_variant}: {e}")
        continue
print("Finished updating allele frequencies.")