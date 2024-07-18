import os
from pymongo import MongoClient

def get_genomic_variants_for_individual(biosample_id):
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

    # query to find all genomic variants for the given biosampleId = individualId
    query = {'caseLevelData.biosampleId': biosample_id}

    # find the genomic variants and sort by alleleFrequency (ascending order)
    genomic_variants = collection.find(query, {'variantInternalId': 1, 'alleleFrequency': 1}).sort('alleleFrequency', 1)

    # extract the id of those genomic variants
    variant_ids = [variant['variantInternalId'] for variant in genomic_variants]

    return variant_ids

def main():
    # ask which individual we will try to attack
    biosample_id = input("Enter the individualId to search: ")
    variant_ids = get_genomic_variants_for_individual(biosample_id)
    
    # try and query the all the variants starting with the lower frequency ones and see when the individual is removed from the output
    if variant_ids:
        print(f"The genomic variants for biosampleId {biosample_id} are (sorted by alleleFrequency):")
        for vid in variant_ids:
            print(vid)
    else:
        print(f"No genomic variants found for individualId {biosample_id}")

if __name__ == "__main__":
    main()
