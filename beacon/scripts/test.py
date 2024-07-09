import requests

def convert_coordinates_grch37_to_grch38(chromosome, position, reference_allele, new_allele):
    server = "https://rest.ensembl.org"
    ext = f"/map/human/GRCh37/{chromosome}:{position}..{position}/GRCh38?"

    # Make the GET request to the Ensembl REST API
    response = requests.get(server + ext, headers={"Content-Type": "application/json"})

    # Check for a successful response
    if not response.ok:
        response.raise_for_status()

    # Parse the response JSON
    data = response.json()

    # Get the mapped position in GRCh38
    if "mappings" in data and len(data["mappings"]) > 0:
        mapped_position = data["mappings"][0]["mapped"]["start"]
        mapped_chromosome = data["mappings"][0]["mapped"]["seq_region_name"]
        grch38_start = mapped_position
        grch38_end = grch38_start + len(new_allele) - 1

        # Print the mapped coordinates and sequence change
        print(f"GRCh37: {chromosome}:{position} {reference_allele}>{new_allele}")
        print(f"GRCh38: {mapped_chromosome}:{grch38_start} {reference_allele}>{new_allele}")

    else:
        print("No mappings found for the given coordinates.")

# Coordinates and allele change for GRCh37
chromosome = '22'
position = 16064513
reference_allele = 'A'
new_allele = 'AAGAATGGCCTAATAC'

# Convert coordinates from GRCh37 to GRCh38
convert_coordinates_grch37_to_grch38(chromosome, position, reference_allele, new_allele)
