import requests
from pymongo import MongoClient
import os

# Function to format a single variant
def format_variant_for_search(variant):
    chromosome = variant["_position"]["refseqId"]
    start_position = variant["_position"]["startInteger"]
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]
    formatted_variant = f"{chromosome}-{start_position}-{reference_base}-{alternate_base}"
    return formatted_variant

# Function to query 1000 Genomes for allele frequency
def query_1000_genomes(chrom, pos, ref, alt):
    try:
        # Construct the HGVS notation
        hgvs_notation = f"{chrom}:g.{pos}{ref}>{alt}"
        
        # Construct the URL
        url = f"https://rest.ensembl.org/vep/human/hgvs/{hgvs_notation}?"

        # Make GET request to the API
        response = requests.get(url, headers={"Content-Type": "application/json"})

        # Check if request was successful
        if response.status_code == 200:
            # Parse the JSON response
            json_response = response.json()

            # Check if reference allele matches
            if json_response[0]['allele_string'].startswith(ref):
                return json_response
            else:
                raise ValueError(f"Reference allele mismatch for variant {chrom}-{pos}-{ref}-{alt}. Ensembl returned {json_response[0]['allele_string']}")
        else:
            print(f"Bad request for variant {chrom}-{pos}-{ref}-{alt}: {response.text}")
            return None

    except Exception as e:
        print(f"Failed to retrieve allele frequency for {chrom}-{pos}-{ref}-{alt}: {str(e)}")
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
    pos = parts[1]
    ref = parts[2]
    alt = parts[3]

    try:
        # Query 1000 Genomes for allele frequency
        allele_frequency = query_1000_genomes(chrom, pos, ref, alt)
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
