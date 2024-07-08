import requests
from pyliftover import LiftOver

def convert_coordinates(chrom, start, end):
    """
    Convert genomic coordinates from hg19 to hg38 using pyLiftover.
    """
    lo = LiftOver('hg19', 'hg38')
    new_coords_start = lo.convert_coordinate(chrom, start)
    new_coords_end = lo.convert_coordinate(chrom, end)
    
    if new_coords_start and new_coords_end:
        new_start = new_coords_start[0][1]
        new_end = new_coords_end[0][1]
        return new_start, new_end
    return None, None

def fetch_sequence(chrom, start, end):
    """
    Fetch sequence for the given chromosome and position in GRCh38.
    """
    server = "https://rest.ensembl.org"
    ext = f"/sequence/region/human/{chrom}:{start}..{end}:1?"
    headers = {"Content-Type": "application/json"}
    
    response = requests.get(server + ext, headers=headers)
    
    if not response.ok:
        response.raise_for_status()
    
    seq_data = response.json()
    return seq_data['seq']

def main(chrom, start_hg19, end_hg19, ref_allele_hg19, alt_allele_hg19):
    # Convert hg19 coordinates to hg38
    start_hg38, end_hg38 = convert_coordinates(chrom, start_hg19, end_hg19)
    if start_hg38 and end_hg38:
        print(f"Converted coordinates to hg38: chr{chrom}:{start_hg38}-{end_hg38}")
        
        # Fetch sequences for the hg38 coordinates
        ref_allele_hg38 = fetch_sequence(chrom, start_hg38, start_hg38)
        alt_allele_hg38 = fetch_sequence(chrom, start_hg38, start_hg38 + len(alt_allele_hg19) - 1)
        
        if ref_allele_hg38 and alt_allele_hg38:
            print(f"Reference allele for hg38 chr{chrom}:{start_hg38} is {ref_allele_hg38}")
            print(f"Alternate allele for hg38 chr{chrom}:{start_hg38} is {alt_allele_hg38}")
            
            print(f"Variant in hg38: chr{chrom}:{start_hg38}{ref_allele_hg38}>{alt_allele_hg38}")
        else:
            print("Failed to fetch alleles for the new coordinates.")
    else:
        print("Failed to convert coordinates to hg38.")

# Example coordinates and alleles
chrom = "22"
start_hg19 = 16050075
end_hg19 = 16050075
ref_allele_hg19 = "A"
alt_allele_hg19 = "G"

main(chrom, start_hg19, end_hg19, ref_allele_hg19, alt_allele_hg19)
