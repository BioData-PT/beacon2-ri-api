import pyensembl
from pyensembl import EnsemblRelease

# Load the Ensembl releases
grch37 = EnsemblRelease(75)  # GRCh37 (hg19)
grch38 = EnsemblRelease(95)  # GRCh38 (hg38)

# Coordinates and allele change for GRCh37
chromosome = '22'
position = 16064513
reference_allele = 'A'
new_allele = 'AAGAATGGCCTAATAC'

# Get the gene and transcript information from GRCh37
gene = grch37.genes_at_locus(contig=chromosome, position=position)

if not gene:
    print("Gene not found in GRCh37 at the specified locus.")
else:
    gene = gene[0]
    print(f"Gene in GRCh37: {gene}")

    # Assuming the gene ID is the same in both assemblies, you can find it in GRCh38
    gene_in_grch38 = grch38.gene_by_id(gene.gene_id)
    print(f"Gene in GRCh38: {gene_in_grch38}")

    # Map position to GRCh38 using the start and end positions of the gene
    grch38_start = gene_in_grch38.start + (position - gene.start)
    grch38_end = grch38_start + len(new_allele) - 1

    # Retrieve the corresponding sequence in GRCh38
    grch38_sequence = grch38.sequence(region=(chromosome, grch38_start, grch38_end))
    print(f"GRCh38 Sequence: {grch38_sequence}")

    # Print the mapped coordinates and sequence change
    print(f"GRCh37: {chromosome}:{position} {reference_allele}>{new_allele}")
    print(f"GRCh38: {chromosome}:{grch38_start} {grch38_sequence[0]}>{new_allele}")
