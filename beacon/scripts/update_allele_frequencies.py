import requests
import sys
from pymongo import MongoClient
import os
import time

# Function to format a single variant
def format_variant_for_search(variant):
    chromosome = variant["_position"]["refseqId"]
    start_position = int(variant["_position"]["startInteger"])  # Ensure start position is an integer
    end_position = int(variant["_position"]["endInteger"])  # Ensure end position is an integer
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]
    formatted_variant = f"{chromosome}-{start_position}-{end_position}-{reference_base}-{alternate_base}"
    return formatted_variant

# Function to query 1000 Genomes for allele frequency
def query_1000_genomes(chrom, start, end, ref, alt, max_retries=5):
    server = "https://rest.ensembl.org"
    ext = f"/map/human/GRCh37/{chrom}:{start}..{end}/GRCh38?"
    
    retries = 0
    while retries < max_retries:
        r = requests.get(server + ext, headers={"Content-Type": "application/json"})
        
        if r.status_code == 429:  # Too many requests
            retries += 1
            wait_time = 2 ** retries
            print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)  # Exponential backoff
            continue
        elif not r.ok:
            print(f"Error: {r.status_code}. Exiting.")
            r.raise_for_status()
            sys.exit()
        
        decoded = r.json()
        mappings = decoded['mappings']
        
        if not mappings:
            raise ValueError(f"No mappings found for {chrom}:{start} in GRCh38")
        
        mapped_data = mappings[0]['mapped']
        mapped_start = int(mapped_data['start'])
        mapped_end = int(mapped_data['end'])

        # Fetch the reference allele from the Ensembl database
        ref_url = f"https://rest.ensembl.org/sequence/region/human/{chrom}:{mapped_start}..{mapped_end}:1?"
        ref_response = requests.get(ref_url, headers={"Content-Type": "application/json"})
        
        if ref_response.status_code != 200:
            print(f"Failed to fetch reference allele for {chrom}:{mapped_start}-{mapped_end}")
            return None
        
        ref_allele = ref_response.json().get('seq')

        # Ensure the reference allele matches exactly at the position
        exact_ref_allele = ref_allele[:len(ref)]

        if exact_ref_allele != ref:
            raise ValueError(f"Reference allele mismatch for variant {chrom}:{start}{ref}>{alt}. Ensembl returned {exact_ref_allele}")

        # Construct the HGVS notation
        hgvs_notation = f"{chrom}:g.{mapped_start}{ref}>{alt}"
        
        # Construct the URL for Ensembl VEP
        url = f"https://rest.ensembl.org/vep/human/hgvs/{hgvs_notation}?"
        
        # Throttle requests to avoid exceeding rate limits
        time.sleep(0.1)  # Sleep for 100 milliseconds (10 requests per second)
        
        # Make GET request to the API
        response = requests.get(url, headers={"Content-Type": "application/json"})
        
        if response.status_code == 429:
            retries += 1
            wait_time = 2 ** retries
            print(f"Rate limit exceeded. Retrying in {wait_time} seconds...")
            time.sleep(wait_time)  # Exponential backoff
            continue
        elif response.status_code == 200:
            # Parse the JSON response
            json_response = response.json()
            
            # Check if reference allele matches
            if json_response and json_response[1]['allele_string'].startswith(ref):
                return json_response
            else:
                raise ValueError(f"Reference allele mismatch for variant {chrom}-{start}-{ref}-{alt}. Ensembl returned {json_response[0]['allele_string']}")
        else:
            print(f"Bad request for variant {chrom}-{start}-{ref}-{alt}: {response.text}")
            return None

    print(f"Failed to retrieve data after {max_retries} retries.")
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
    formatted_variant = format_variant_for_search(variant)
    print("-----------")
    print(f"{formatted_variant}")

    # Split formatted_variant to extract chrom, pos, ref, alt
    parts = formatted_variant.split('-')
    chrom = parts[0]
    start = int(parts[1])  # Ensure start position is an integer
    end = int(parts[2])  # Ensure end position is an integer
    ref = parts[3]
    alt = parts[4]

    try:
        # Query 1000 Genomes for allele frequency
        allele_frequency = query_1000_genomes(chrom, start, end, ref, alt)
        print(allele_frequency)

        if allele_frequency is not None:
            collection.update_one(
                {"variantInternalId": variant["variantInternalId"]},
                {"$set": {"allele_frequency": allele_frequency}}
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
