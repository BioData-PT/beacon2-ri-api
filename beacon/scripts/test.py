import requests

def liftover_hg19_to_hg38(chrom, pos, ref_allele, alt_allele):
    """
    Convert genomic coordinates from hg19 to hg38 using the Broad Institute's LiftOver API.
    """
    url = f"https://liftover.broadinstitute.org/api/v1/liftover/hg19-to-hg38/{chrom}:{pos}-{pos}"
    response = requests.get(url)

    if response.status_code == 200:
        data = response.json()
        if "results" in data and data["results"]:
            result = data["results"][0]
            hg38_start = result["start"]
            hg38_end = result["end"]
            return hg38_start, hg38_end
    else:
        print(f"Error: {response.status_code}")
        print(response.text)
    
    return None, None

def fetch_reference_allele(chrom, start, end):
    """
    Fetch the reference allele for the given chromosome and position from the GRCh38 assembly.
    """
    url = f"https://rest.ensembl.org/sequence/region/human/{chrom}:{start}..{end}:1?content-type=text/plain"
    response = requests.get(url)
    
    if response.status_code == 200:
        return response.text.strip()
    else:
        print(f"Error fetching reference allele: {response.status_code}")
        print(response.text)
        return None

# Example coordinates
chrom = "22"
pos_hg19 = 16050075
ref_allele_hg19 = "A"
alt_allele_hg19 = "G"

# Step 1: Convert hg19 coordinates to hg38 using LiftOver
start_hg38, end_hg38 = liftover_hg19_to_hg38(chrom, pos_hg19, ref_allele_hg19, alt_allele_hg19)
if start_hg38 and end_hg38:
    print(f"Converted coordinates to hg38: chr{chrom}:{start_hg38}-{end_hg38}")
    
    # Step 2: Fetch the reference allele for the hg38 coordinates
    ref_allele_hg38 = fetch_reference_allele(chrom, start_hg38, end_hg38)
    if ref_allele_hg38:
        print(f"Reference allele at hg38 chr{chrom}:{start_hg38}-{end_hg38}: {ref_allele_hg38}")
        
        # Construct the variant notation for hg38
        alt_allele_hg38 = "C"  # Assume the alternate allele remains the same, if verified
        variant_hg38 = f"chr{chrom}:{start_hg38}{ref_allele_hg38}>{alt_allele_hg38}"
        print(f"Variant notation for hg38: {variant_hg38}")
else:
    print("Failed to convert coordinates to hg38.")
