import requests

def convert_coordinates(chrom, start, end, allele, genome_from='GRCh37', genome_to='GRCh38'):
    """
    Convert genomic coordinates from GRCh37 to GRCh38 using Ensembl API.
    """
    server = "https://rest.ensembl.org"
    ext = f"/map/human/{genome_from}/{chrom}:{start}..{end}/{genome_to}"
    headers = {"Content-Type": "application/json"}
    
    response = requests.get(server + ext, headers=headers)
    
    if not response.ok:
        response.raise_for_status()
    
    converted = response.json()
    return converted

def fetch_sequence(chrom, start, end, genome='GRCh38'):
    """
    Fetch sequence for the given chromosome and position using Ensembl API.
    """
    server = "https://rest.ensembl.org"
    ext = f"/sequence/region/human/{chrom}:{start}..{end}:{genome}?"
    headers = {"Content-Type": "application/json"}
    
    response = requests.get(server + ext, headers=headers)
    
    if not response.ok:
        response.raise_for_status()
    
    seq_data = response.json()
    return seq_data['seq']

def main(chrom, start_hg19, end_hg19, ref_allele_hg19, alt_allele_hg19):
    # Convert hg19 coordinates to hg38
    converted_coords = convert_coordinates(chrom, start_hg19, end_hg19, ref_allele_hg19)
    mappings = converted_coords.get('mappings', [])
    
    if mappings:
        new_start = mappings[0]['mapped']['start']
        new_end = mappings[0]['mapped']['end']
        print(f"Converted coordinates to hg38: chr{chrom}:{new_start}-{new_end}")
        
        # Fetch reference allele for the new hg38 coordinates
        ref_allele_hg38 = fetch_sequence(chrom, new_start, new_start)
        
        # Fetch alternate allele for the new hg38 coordinates
        alt_allele_hg38 = fetch_sequence(chrom, new_start, new_start + len(alt_allele_hg19) - 1)
        
        print(f"Reference allele for hg38 chr{chrom}:{new_start} is {ref_allele_hg38}")
        print(f"Alternate allele for hg38 chr{chrom}:{new_start} is {alt_allele_hg38}")
        
        print(f"Variant in hg38: chr{chrom}:{new_start}{ref_allele_hg38}>{alt_allele_hg38}")
    else:
        print("Failed to convert coordinates to hg38.")

# Example coordinates and alleles
chrom = "22"
start_hg19 = 16050075
end_hg19 = 16050075
ref_allele_hg19 = "A"
alt_allele_hg19 = "G"

main(chrom, start_hg19, end_hg19, ref_allele_hg19, alt_allele_hg19)
