import requests
import sys
from pymongo import MongoClient
import os
import time

def query_1000_genomes(chrom, start, end, ref, alt):
    print("START " + f"{start}")
    print("END " + f"{end}")
    server = "https://rest.ensembl.org"
    ext = f"/map/human/GRCh37/{chrom}:{start}..{end}:1/GRCh38?"
 
    r = requests.get(server + ext, headers={"Content-Type": "application/json"})
 
    if not r.ok:
        r.raise_for_status()
        sys.exit()

    decoded = r.json()
    mappings = decoded['mappings']
    if not mappings:
        print(f"No mapping found for {chrom}:{start}-{end}")
        return None

    mapped_data = mappings[0]['mapped']
    mapped_start = mapped_data['start']
    mapped_end = mapped_data['end']
    
    # Construct the HGVS notation
    hgvs_notation = f"{chrom}:g.{mapped_start}{ref}>{alt}"
    
    # Construct the URL for Ensembl VEP
    url = f"https://rest.ensembl.org/vep/human/hgvs/{hgvs_notation}?"
 
    # Make GET request to the API
    time.sleep(1)
    response = requests.get(url, headers={"Content-Type": "application/json"})
 
    # Check if request was successful
    if response.status_code == 200:
        # Parse the JSON response
        json_response = response.json()
 
        # Check if reference allele matches
        if json_response and json_response[0]['allele_string'].startswith(ref):
            return json_response
        else:
            # If reference allele does not match, retry with actual reference allele from response
            actual_ref = json_response[0]['allele_string'].split('/')[0]
            if actual_ref != ref:
                corrected_hgvs_notation = f"{chrom}:g.{mapped_start}{actual_ref}>{alt}"
                corrected_url = f"https://rest.ensembl.org/vep/human/hgvs/{corrected_hgvs_notation}?"
                time.sleep(1)
                corrected_response = requests.get(corrected_url, headers={"Content-Type": "application/json"})
                if corrected_response.status_code == 200:
                    return corrected_response.json()
                else:
                    print(f"Bad request for corrected variant {chrom}-{start}-{actual_ref}-{alt}: {corrected_response.text}")
                    return None
            else:
                raise ValueError(f"Reference allele mismatch for variant {chrom}-{start}-{ref}-{alt}. Ensembl returned {json_response[0]['allele_string']}")
    else:
        print(f"Bad request for variant {chrom}-{start}-{ref}-{alt}: {response.text}")
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
    
    formatted_variant = f"{chromosome}-{start_position}-{end_position}-{reference_base}-{alternate_base}"
    print("-----------")
    print(f"{formatted_variant}")
    try:
        # Query 1000 Genomes for allele frequency
        allele_frequency = query_1000_genomes(chromosome, start_position, end_position, reference_base, alternate_base)
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
