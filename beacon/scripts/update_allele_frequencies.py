import requests
from pymongo import MongoClient
import os
import time
from collections import namedtuple
import itertools

# Function to flatten nested lists
def flatten(iterable):
    return list(itertools.chain.from_iterable(iterable))

# Function to format a single variant
def format_variant_for_search(variant):
    chromosome = variant["_position"]["refseqId"]
    start_position = variant["_position"]["startInteger"]
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]

    formatted_variant = f"{chromosome}-{start_position}-{reference_base}-{alternate_base}"
    return formatted_variant

# Function to query NCBI Variation Services for allele frequency
VAR_API_URL = "https://api.ncbi.nlm.nih.gov/variation/v0/"

def get(endpoint, **params):
    max_retries = 3
    for attempt in range(max_retries):
        try:
            reply = requests.get(VAR_API_URL + endpoint, params=params)
            reply.raise_for_status()
            return reply.json()
        except requests.exceptions.HTTPError as e:
            if reply.status_code >= 500:
                print(f"Server error: {e}. Retrying...")
                time.sleep(2 ** attempt)  # Exponential backoff
            else:
                print(f"Client error: {e}.")
                raise
    raise Exception(f"Failed to get data from {endpoint} after {max_retries} attempts")

Spdi = namedtuple('Spdi', 'seq_id position deleted_sequence inserted_sequence')

def remap(spdi):
    remap_url = 'spdi/{}:{}:{}:{}/canonical_representative'.format(*spdi)
    return Spdi(**get(remap_url)['data'])

def fetch_reference_base(chrom, pos):
    query_url = f'spdi/NC_0000{chrom}.10:{pos}:1:1'
    try:
        response = get(query_url)
        return response['data']['deleted_sequence']
    except Exception as e:
        print(f"Error fetching reference base for {chrom}-{pos}: {e}")
        return None

INPUT_VCF_ASSEMBLY = 'GCF_000001405.38'  # GRCh38 assembly

def query_ncbi_variation(formatted_variant):
    try:
        # Fetch reference base from NCBI
        chrom, pos, ref, alt = formatted_variant.split('-')
        alts = ','.join(map(str, alt))
        query_url = f'vcf/{chrom}/{pos}/{ref}/{alts}/contextuals'
        print(query_url)
        spdis_for_alts = [Spdi(**spdi_dict) for spdi_dict in get(query_url, assembly=INPUT_VCF_ASSEMBLY)['data']['spdis']]
        
        spdis_for_alts = [remap(spdi) for spdi in spdis_for_alts]
        
        frequencies = {}

        for spdi in spdis_for_alts:
            seq_id = spdi.seq_id
            min_pos = spdi.position
            max_pos = spdi.position + len(spdi.deleted_sequence)
            frequency_records = get(f'interval/{seq_id}:{min_pos}:{max_pos-min_pos}/overlapping_frequency_records')['results']
            for interval, interval_data in frequency_records.items():
                allele_counts = interval_data['counts']
                overall_frequencies = compute_frequencies(allele_counts)
                for allele, frequency in overall_frequencies.items():
                    frequencies[Spdi(seq_id, interval_data['interval']['start'], interval_data['ref'], allele)] = frequency
        return frequencies
    except Exception as e:
        print(f"Failed to query NCBI Variation Services for variant {formatted_variant}: {e}")
        return None

def compute_frequencies(allele_counts):
    total = float(sum(allele_counts.values()))
    if total:
        return {allele: count / total for allele, count in allele_counts.items()}
    else:
        return {allele: 0.0 for allele in allele_counts.keys()}

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

# Iterate over all variants, format them, query NCBI, and update the database
for variant in collection.find():
    formatted_variant = format_variant_for_search(variant)
    print("-----------")
    print(f"{formatted_variant}")
    allele_frequencies = query_ncbi_variation(formatted_variant)
    if allele_frequencies:
        collection.update_one(
            {"variantInternalId": variant["variantInternalId"]},
            {"$set": {"allele_frequencies": allele_frequencies}}
        )
        print(f"Updated variant {formatted_variant} with allele frequencies {allele_frequencies}")
    else:
       print(f"Failed to retrieve allele frequencies for {formatted_variant}")
    # Sleep to respect rate limits
    time.sleep(1)

print("Finished updating allele frequencies.")
