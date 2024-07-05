from collections import namedtuple
import requests
from pymongo import MongoClient
import os
from ratelimit import limits, sleep_and_retry
from tqdm import tqdm
import itertools

# function to flatten nested lists
def flatten(iterable):
    return list(itertools.chain.from_iterable(iterable))

# function to format a single variant
def format_variant_for_search(variant):
    chromosome = variant["_position"]["refseqId"]
    start_position = variant["_position"]["startInteger"]
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]

    formatted_variant = f"{chromosome}-{start_position}-{reference_base}-{alternate_base}"
    return formatted_variant

# function to query NCBI Variation Services for allele frequency
VAR_API_URL = "https://api.ncbi.nlm.nih.gov/variation/v0/"
@sleep_and_retry
@limits(calls=1, period=1)  # Limit request rate to 1 RPS
def get(endpoint, **params):
    reply = requests.get(VAR_API_URL + endpoint, params=params)
    reply.raise_for_status()
    return reply.json()

Spdi = namedtuple('Spdi', 'seq_id position deleted_sequence inserted_sequence')

def query_ncbi_variation(formatted_variant):
    chrom, pos, ref, alt = formatted_variant.split('-')
    query_url = f'vcf/{chrom}/{pos}/{ref}/{alt}/contextuals'
    spdis_for_alts = [Spdi(**spdi_dict) for spdi_dict in get(query_url)['data']['spdis']]
    frequencies = {}

    for spdi in spdis_for_alts:
        seq_id = spdi.seq_id
        min_pos = spdi.position
        max_pos = spdi.position + len(spdi.deleted_sequence)
        frequency_records = get(f'interval/{seq_id}:{min_pos}:{max_pos-min_pos}/overlapping_frequency_records')['results']
        for interval, interval_data in frequency_records.items():
            length, position = map(int, interval.split('@'))
            allele_counts = interval_data['counts']['PRJNA507278']['allele_counts']
            aaa_frequencies = compute_frequencies(allele_counts['SAMN10492703'])
            asn_frequencies = compute_frequencies(allele_counts['SAMN10492704'])
            for allele in asn_frequencies.keys():
                frequencies[Spdi(seq_id, position, interval_data['ref'], allele)] = (aaa_frequencies[allele], asn_frequencies[allele])
    return frequencies

def compute_frequencies(allele_counts):
    total = float(sum(allele_counts.values()))
    if total:
        return {allele: count / total for allele, count in allele_counts.items()}
    else:
        return {allele: 0.0 for allele in allele_counts.keys()}


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

# iterate over all variants, format them, query NCBI, and update the database
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

print("Finished updating allele frequencies.")