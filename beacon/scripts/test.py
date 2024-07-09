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
    
    # Perform coordinate conversion from GRCh37 to GRCh38
    grch37_region = f"{chromosome}:{position-1}..{position}"
    ext = f"/map/human/GRCh37/{grch37_region}/GRCh38?"
    response = requests.get(server + ext, headers={"Content-Type": "application/json"})
    if not response.ok:
        response.raise_for_status()
    data = response.json()

    if "mappings" in data and len(data["mappings"]) > 0:
        mapping = data["mappings"][0]["mapped"]
        grch38_chromosome = mapping["seq_region_name"]
        grch38_start = mapping["start"]

        # Fetch sequence around the mapped position in GRCh38
        grch38_region = f"{grch38_chromosome}:{grch38_start-1}..{grch38_start+len(alt_allele)-1}"
        grch38_seq = fetch_sequence(server, grch38_region)

        # Fetch sequence around the variant in GRCh37
        grch37_region_full = f"{chromosome}:{position-1}..{position+len(alt_allele)-1}"
        grch37_seq = fetch_sequence(server, grch37_region_full)

        # Print results
        print(f"GRCh37: {chromosome}:{position} {ref_allele}>{alt_allele}")
        print(f"GRCh37 Sequence: {grch37_seq}")
        print(f"GRCh38: {grch38_chromosome}:{grch38_start} {grch38_seq[0]}>{grch38_seq}")
    else:
        print("No mappings found for the given coordinates.")

# Coordinates and allele change for GRCh37
chromosome = '22'
position = 16064513
ref_allele = 'A'
alt_allele = 'AAGAATGGCCTAATAC'

# Convert coordinates from GRCh37 to GRCh38
convert_coordinates_grch37_to_grch38(chromosome, position, ref_allele, alt_allele)
