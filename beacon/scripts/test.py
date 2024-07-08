from pyliftover import LiftOver

# Function to get the reverse complement of a base
def reverse_complement(base):
    complement = {'A': 'T', 'T': 'A', 'C': 'G', 'G': 'C'}
    return complement[base]

# Initialize LiftOver object with chain file for hg19 to hg38
lo = LiftOver('hg19', 'hg38')

# Define the hg19 coordinate and alleles
chrom = '22'
position = 16050319
ref_base = 'C'
alt_base = 'T'

# Convert the coordinate
converted = lo.convert_coordinate(chrom, position)

if converted:
    # Retrieve the new coordinate and strand
    new_chrom, new_pos, strand, _ = converted[0]

    if strand == '-':
        # If on reverse strand, get the reverse complement of the alleles
        new_ref_base = reverse_complement(ref_base)
        new_alt_base = reverse_complement(alt_base)
    else:
        new_ref_base = ref_base
        new_alt_base = alt_base

    print(f"hg38: chr{new_chrom}:{new_pos} {new_ref_base}>{new_alt_base}")
else:
    print("Conversion failed")
