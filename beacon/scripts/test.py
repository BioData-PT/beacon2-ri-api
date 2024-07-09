import requests

def fetch_sequence(server, region):
    """Fetch sequence for a given region."""
    ext = f"/sequence/region/human/{region}?"
    response = requests.get(server + ext, headers={"Content-Type": "application/json"})
    if not response.ok:
        response.raise_for_status()
    return response.json()['seq']

def convert_coordinates_grch37_to_grch38(chromosome, position, ref_allele, alt_allele):
    server = "https://rest.ensembl.org"
    ext = f"/map/human/GRCh37/{chromosome}:{position}..{position}/GRCh38?"
    response = requests.get(server + ext, headers={"Content-Type": "application/json"})
    if not response.ok:
        response.raise_for_status()
    data = response.json()

    if "mappings" in data and len(data["mappings"]) > 0:
        mapping = data["mappings"][0]["mapped"]
        grch38_chromosome = mapping["seq_region_name"]
        grch38_start = mapping["start"]

        # Fetch sequences for verification
        grch37_seq = fetch_sequence(server, f"{chromosome}:{position-1}..{position}")
        grch38_seq = fetch_sequence(server, f"{grch38_chromosome}:{grch38_start-1}..{grch38_start}")

        # Check if the sequences match the expected alleles
        if grch37_seq == ref_allele and grch38_seq == alt_allele:
            print(f"GRCh37: {chromosome}:{position} {ref_allele}>{alt_allele}")
            print(f"GRCh38: {grch38_chromosome}:{grch38_start} {grch38_seq}>{ref_allele}")
        else:
            print("Sequence verification failed. Please check alleles and sequences.")
    else:
        print("No mappings found for the given coordinates.")

# Coordinates and allele change for GRCh37
chromosome = '22'
position = 16064513
ref_allele = 'A'
alt_allele = 'AAGAATGGCCTAATAC'

# Convert coordinates from GRCh37 to GRCh38
convert_coordinates_grch37_to_grch38(chromosome, position, ref_allele, alt_allele)
