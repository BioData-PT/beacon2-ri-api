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
    chrom, pos, ref, alt = formatted_variant.split('-')
    print(chrom, pos, ref, alt)
    query_url = f"https://gnomad.broadinstitute.org/api"
    query = """
    {
      variant(chrom: "%s", pos: %d, ref: "%s", alt: "%s") {
        genome {
          ac
          an
          af
        }
        exome {
          ac
          an
          af
        }
      }
    }
    """ % (chrom, pos, ref, alt)
    headers = {"Content-Type": "application/json"}
    response = requests.post(query_url, json={"query": query}, headers=headers)
    if response.status_code == 200:
        return response.json()
    else:
        raise Exception(f"Query failed to run with a {response.status_code}.")


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
# iterate over all variants, format them, query gnomAD, and update the database
for variant in collection.find():
    formatted_variant = format_variant_for_search(variant)
    print("-----------")
    print(f"{formatted_variant}")
    allele_frequency = query_gnomad(formatted_variant)
    if allele_frequency is not None:
        collection.update_one(
            {"variantInternalId": variant["variantInternalId"]},
            {"$set": {"allele_frequency": allele_frequency}}
        )
        print(f"Updated variant {formatted_variant} with allele frequency {allele_frequency}")
    else:
       print(f"Failed to retrieve allele frequency for {formatted_variant}")

print("Finished updating allele frequencies.")