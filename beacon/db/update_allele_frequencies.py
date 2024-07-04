import requests
from pymongo import MongoClient
import os

from beacon.db.g_variants import get_variants
from beacon.request.model import RequestParams, QueryParams, Pagination

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


qparams = RequestParams(
        query=QueryParams(
            request_parameters={},  # no filters applied
            pagination=Pagination(skip=0, limit=100)  # adjust limit as needed
        )
    )

    # Call the get_variants function
schema, count, docs = get_variants(None, qparams)
print(f"{count}")

# iterate over all variants, format them, query gnomAD, and update the database
#for variant in docs:
 #   formatted_variant = format_variant_for_search(variant)
  #  print(formatted_variant)
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
