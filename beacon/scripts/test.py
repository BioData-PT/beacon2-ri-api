import requests

# Function to get the reverse complement of a base
def reverse_complement(base):
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return complement[base]

# Function to convert coordinates using UCSC liftOver API
def liftOver_hg19_to_hg38(chrom, position, ref_base, alt_base):
    url = "http://genome.ucsc.edu/cgi-bin/hgLiftOver"
    params = {
        'db': 'hg19',
        'g': 'hgFixed',
        'hgLiftOver.fromDb': 'hg19',
        'hgLiftOver.toDb': 'hg38',
        'position': f'{chrom}:{position}-{position}',
        'format': 'json'
    }

    response = requests.get(url, params=params)
    result = response.json()

    if result and 'over' in result:
        new_chrom = result['over'][0]['chrom']
        new_pos = result['over'][0]['chromStart'] + 1  # UCSC API returns 0-based start
        strand = result['over'][0]['strand']

        if strand == '-':
            # If on reverse strand, get the reverse complement of the alleles
            new_ref_base = reverse_complement(ref_base)
            new_alt_base = reverse_complement(alt_base)
        else:
            new_ref_base = ref_base
            new_alt_base = alt_base

        return f"hg38: chr{new_chrom}:{new_pos} {new_ref_base}>{new_alt_base}"
    else:
        return "Conversion failed"

# Define the hg19 coordinate and alleles
chrom = '22'
position = 16050319
ref_base = 'C'
alt_base = 'T'

# Perform the conversion
result = liftOver_hg19_to_hg38(chrom, position, ref_base, alt_base)
print(result)
