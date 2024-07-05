import requests, sys
from pymongo import MongoClient
import os
import time

# Function to convert GRCh37 to GRCh38 using Ensembl REST API
def convert_to_grch38(start, alt, ref, chrom):
    # Construct Ensembl REST URL for mapping from GRCh37 to GRCh38
    ensembl_rest_url = f"https://rest.ensembl.org/map/human/GRCh37/{chrom}:{start}:{ref}:{alt}/GRCh38?"
    print("LINK" + ensembl_rest_url)

    # Make GET request to Ensembl REST API
    response = requests.get(ensembl_rest_url, headers={"Content-Type": "application/json"})

    # Check if request was successful
    if response.ok:
        # Parse JSON response
        json_response = response.json()

        # Extract mapped coordinates
        mappings = json_response.get('mappings', [])
        if mappings:
            mapped_data = mappings[0].get('mapped', {})
            start = mapped_data.get('start')
            end = mapped_data.get('end')
            return start, end
        else:
            print(f"No mappings found for {hgvs_id}")
            return None, None
    else:
        print(f"Failed to fetch mapping for {hgvs_id}: {response.status_code}")
        return None, None

# Function to query 1000 Genomes for allele frequency
def query_1000_genomes(end_grch38, ref, alt, chrom):
    
    # Construct the HGVS notation
    
    # Construct the URL for Ensembl VEP
    hgvs_notation = f"{chrom}:g.{end_grch38}{ref}>{alt}"
    url = f"https://rest.ensembl.org/vep/human/hgvs/{hgvs_notation}?"
    print(url)
 
    # Make GET request to the API
    time.sleep(1)
    response = requests.get(url, headers={"Content-Type": "application/json"})
 
    # Check if request was successful
    if response.status_code == 200:
        # Parse JSON response
        json_response = response.json()
        mappings = json_response.get('mappings', [])
        if mappings:
            mapped_data = mappings[0].get('mapped', {})
            start = mapped_data.get('start')
            end = mapped_data.get('end')
            return start, end
        else:
            print(f"No mappings found for {hgvs_id}")
            return None, None
    else:
        print(f"Failed to fetch mapping for {hgvs_id}: {response.status_code}")
        return None, None


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
    hgvs_id = variant["identifiers"]["genomicHGVSId"]
    start = variant['_position']['startInteger']
    alt = variant['variation']['alternateBases']
    ref = variant['variation']['referenceBases']
    chrom = variant['_position']['refseqId']
    tart_grch38, end_grch38 = convert_to_grch38(start, alt, ref, chrom)

    try:
        # Query 1000 Genomes for allele frequency
        allele_frequency = query_1000_genomes(end_grch38, ref, alt, chrom)
        print(allele_frequency)

        if allele_frequency is not None:
            collection.update_one(
                {"variantInternalId": variant["variantInternalId"]},
                {"$set": {"allele_frequency": allele_frequency}}
            )
            print(f"Updated variant {hgvs_id} with allele frequency {allele_frequency}")
        else:
           print(f"Failed to retrieve allele frequency for {hgvs_id}")

    except ValueError as e:
        print(str(e))
        continue
    except Exception as e:
        print(f"Failed to process variant {hgvs_id}: {e}")
        continue

print("Finished updating allele frequencies.")
