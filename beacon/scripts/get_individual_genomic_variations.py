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

    # Query to find all genomic variants for the given biosampleId
    query = {'caseLevelData.biosampleId': biosample_id}

    # Find the genomic variants
    genomic_variants = collection.find(query, {'id': 1})

    # Extract the IDs of the genomic variants
    variant_ids = [variant['variantInternalId'] for variant in genomic_variants]

    return variant_ids

def main():
    biosample_id = input("Enter the biosampleId: ")
    variant_ids = get_genomic_variants_for_individual(biosample_id)
    
    if variant_ids:
        print(f"The genomic variants for biosampleId {biosample_id} are:")
        for vid in variant_ids:
            print(vid)
    else:
        print(f"No genomic variants found for biosampleId {biosample_id}")

if __name__ == "__main__":
    main()
