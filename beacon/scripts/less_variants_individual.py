import os
import subprocess
from pymongo import MongoClient

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

def get_all_individuals():
    # Find all distinct biosampleIds in the genomicVariations collection
    return collection.distinct('caseLevelData.biosampleId')

def count_genomic_variants_for_individual(biosample_id):
    # Query to count all genomic variants for the given biosampleId = individualId
    query = {'caseLevelData.biosampleId': biosample_id}
    return collection.count_documents(query)

def get_individual_with_least_variants():
    individuals = get_all_individuals()
    if not individuals:
        return None, 0

    min_variants = float('inf')
    min_individual = None

    for individual in individuals:
        variant_count = count_genomic_variants_for_individual(individual)
        if variant_count < min_variants:
            min_variants = variant_count
            min_individual = individual

    return min_individual, min_variants

def get_genomic_variants_for_individual(biosample_id):
    # Query to find all genomic variants for the given biosampleId = individualId
    query = {'caseLevelData.biosampleId': biosample_id}

    # Find the genomic variants and sort by alleleFrequency (ascending order)
    genomic_variants = collection.find(query, {'variantInternalId': 1, 'alleleFrequency': 1}).sort('alleleFrequency', 1)

    # Extract the id of those genomic variants
    variant_ids = [variant['variantInternalId'] for variant in genomic_variants]

    return variant_ids

def main():
    min_individual, min_variants = get_individual_with_least_variants()

    if min_individual is not None:
        print(f"The individual with the least genomic variants is {min_individual} with {min_variants} variants.")
    else:
        print("No individuals found in the database.")

if __name__ == "__main__":
    main()
