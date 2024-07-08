import requests

def ensembl_liftover(chrom, pos, from_assembly, to_assembly):
    # Ensembl REST API endpoint for genomic coordinate mapping
    map_url = f"https://rest.ensembl.org/map/human/{from_assembly}/{to_assembly}/{chrom}:{pos}..{pos}:1"

    # Make GET request to Ensembl REST API for liftover mapping
    headers = {"Content-Type": "application/json"}
    response = requests.get(map_url, headers=headers)

    if response.ok:
        data = response.json()

        # Extract mapped coordinates
        mapped = data[0]['mapped']
        if mapped:
            mapped_info = mapped[0]
            new_chrom = mapped_info['assembly_name']
            new_start = mapped_info['start']
            new_end = mapped_info['end']
            strand = mapped_info['strand']

            # Ensembl REST API endpoint for fetching sequence region
            seq_url = f"https://rest.ensembl.org/sequence/region/human/{new_chrom}:{new_start}..{new_end}:{strand}?content-type=application/json"

            # Make GET request to Ensembl REST API for sequence data
            response_seq = requests.get(seq_url, headers=headers)

            if response_seq.ok:
                seq_data = response_seq.json()
                seq = seq_data['seq']
                ref = seq[0]  # Reference allele
                alt = seq[-1]  # Alternate allele

                return new_chrom, new_start, new_end, strand, ref, alt
            else:
                response_seq.raise_for_status()
        else:
            raise ValueError(f"No mapping found for {chrom}:{pos} from {from_assembly} to {to_assembly}")
    else:
        response.raise_for_status()

# Example usage:
chrom = "8"
pos = "140300615"
from_assembly = "GRCh37"
to_assembly = "GRCh38"

try:
    result = ensembl_liftover(chrom, pos, from_assembly, to_assembly)
    print(f"Converted from {from_assembly} to {to_assembly}:")
    print(f"Chromosome: {result[0]}")
    print(f"Start: {result[1]}")
    print(f"End: {result[2]}")
    print(f"Strand: {result[3]}")
    print(f"Reference allele: {result[4]}")
    print(f"Alternate allele: {result[5]}")
except Exception as e:
    print(f"Error: {e}")
