import requests

def get_sequence(server, region):
    """Fetch sequence for a given region."""
    ext = f"/sequence/region/human/{region}?"
    response = requests.get(server + ext, headers={"Content-Type": "application/json"})
    if not response.ok:
        response.raise_for_status()
    return response.json()['seq']

def convert_coordinates_grch37_to_grch38(chromosome, position, ref_allele, alt_allele):
    server = "https://rest.ensembl.org"
    ext = f"/map/human/GRCh37/{chromosome}:{position}..{position + len(ref_allele) - 1}/GRCh38?"
    response = requests.get(server + ext, headers={"Content-Type": "application/json"})
    if not response.ok:
        response.raise_for_status()
    data = response.json()
    if "mappings" in data and len(data["mappings"]) > 0:
        mapping = data["mappings"][0]["mapped"]
        grch38_chromosome = mapping["seq_region_name"]
        grch38_start = mapping["start"]
        grch38_end = grch38_start + len(ref_allele) - 1

        # Fetch sequences for verification
        grch37_region = f"{chromosome}:{position-10}-{position+10}"
        grch38_region = f"{grch38_chromosome}:{grch38_start-10}-{grch38_end+10}"
        grch37_seq = get_sequence(server, grch37_region)
        grch38_seq = get_sequence(server, grch38_region)

        print(f"GRCh37 region: {grch37_region} Sequence: {grch37_seq}")
        print(f"GRCh38 region: {grch38_region} Sequence: {grch38_seq}")

        # Adjust alleles based on sequences (for demonstration, you might need more sophisticated checks)
        adjusted_ref_allele = grch38_seq[10:10+len(ref_allele)]
        adjusted_alt_allele = alt_allele  # Assuming the alt allele doesn't change for this example

        print(f"GRCh37: {chromosome}:{position} {ref_allele}>{alt_allele}")
        print(f"GRCh38: {grch38_chromosome}:{grch38_start} {adjusted_ref_allele}>{adjusted_alt_allele}")
    else:
        print("No mappings found for the given coordinates.")

# Coordinates and allele change for GRCh37
chromosome = '22'
position = 16064513
ref_allele = 'A'
alt_allele = 'AAGAATGGCCTAATAC'

# Convert coordinates from GRCh37 to GRCh38
convert_coordinates_grch37_to_grch38(chromosome, position, ref_allele, alt_allele)
``
