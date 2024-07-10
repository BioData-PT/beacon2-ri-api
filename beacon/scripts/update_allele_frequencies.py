import requests
import sys
from pymongo import MongoClient, UpdateOne
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import hashlib

# Lock for threading
lock = threading.Lock()

# Function to compute the complement of a sequence
def complement(sequence):
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return ''.join(complement[base] for base in sequence)

# Function to query 1000 Genomes for allele frequency
def query_1000_genomes(chrom, start, end, ref, alt, type):
    server = "https://rest.ensembl.org"
    ext = f"/map/human/GRCh37/{chrom}:{start}..{end}:1/GRCh38?"
    
    r = requests.get(server + ext, headers={"Content-Type": "application/json"})
    
    if not r.ok:
        return None

    decoded = r.json()
    mappings = decoded['mappings']
    mapped_data = mappings[0]['mapped']
    mapped_start = mapped_data['start']
    mapped_end = mapped_data['end']
    
    ex = f"/sequence/region/human/{chrom}:{mapped_start}-{mapped_start}?"
    re = requests.get(server + ex, headers={"Content-Type": "application/json"})
    j = re.json()
    check = j['seq']
    
    if type == 'INDEL':
        hgvs_notation = f"{chrom}:g.{mapped_start}_{mapped_end}del{complement(ref)}ins{complement(alt)}"
    elif check == complement(alt):
        hgvs_notation = f"{chrom}:g.{mapped_start}{complement(ref)}>{complement(alt)}"
    elif 'most_severe_consequence' in mapped_data and mapped_data['most_severe_consequence'] == 'downstream_gene_variant':
        hgvs_notation = f"{chrom}:g.{mapped_start}{complement(alt)}>{complement(ref)}"
    else:
        hgvs_notation = f"{chrom}:g.{mapped_start}{complement(ref)}>{complement(alt)}"
    
    url = f"https://rest.ensembl.org/vep/human/hgvs/{hgvs_notation}?"
    
    response = requests.get(url, headers={"Content-Type": "application/json"})
    
    if response.status_code == 200:
        return response.json()
    else:
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

# Function to process a single variant
def process_variant(variant):
    chromosome = variant["_position"]["refseqId"]
    start_position = variant["_position"]["startInteger"]
    end_position = variant["_position"]["endInteger"]
    reference_base = variant["variation"]["referenceBases"]
    alternate_base = variant["variation"]["alternateBases"]
    variant_type = variant["variation"]['variantType']
    
    with lock:
    
        formatted_variant = f"{chromosome}-{start_position}-{end_position}-{reference_base}-{alternate_base}"
        print("------------------------------------")
        print(f"Variant + {formatted_variant}")
        
        allele_frequency = query_1000_genomes(chromosome, start_position, end_position, reference_base, alternate_base, variant_type)
        
        if allele_frequency is not None:
            total_frequency = 0.0
            if "colocated_variants" in allele_frequency[0]:
                if "frequencies" in allele_frequency[0]['colocated_variants'][0]:
                    data = allele_frequency[0]['colocated_variants'][0]['frequencies']
                    for key in data:
                        if "gnomadg" in data[key] and "af" in data[key]:
                            total_frequency = data[key]["gnomadg"] + data[key]["af"]
                        elif "gnomadg" in data[key] and not "af" in data[key]:
                            total_frequency = data[key]["gnomadg"]
                        elif "gnomadg" not in data[key] and "af" in data[key]:
                            total_frequency = data[key]["af"]
                        else:
                            total_frequency = 1 / collection.count_documents({})
                        if total_frequency == 0:
                            total_frequency = 1 / collection.count_documents({})
                    
                        print(f"Updated variant {formatted_variant} with allele frequency {total_frequency}")
                    
                        return UpdateOne(
                            {"variantInternalId": variant["variantInternalId"]},
                            {"$set": {"alleleFrequency": total_frequency}}
                        )
    
    return None

# Main script to process all variants
def main():
    update_requests = []
    futures = []

    with ThreadPoolExecutor(max_workers=10) as executor:
        for variant in collection.find():
            future = executor.submit(process_variant, variant)
            futures.append(future)
        
        for future in as_completed(futures):
            update_request = future.result()
            if update_request:
                update_requests.append(update_request)
    
    if update_requests:
        collection.bulk_write(update_requests)
    print("Finished updating allele frequencies.")

if __name__ == "__main__":
    main()
