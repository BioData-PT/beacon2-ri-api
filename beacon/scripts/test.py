import requests

# Define the genomic HGVS identifier of your variant
genomic_hgvs_id = '22:g.16050075A>G'

# Construct the URL to query dbSNP API
url = f'https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/{genomic_hgvs_id}'

# Make a GET request to the API
response = requests.get(url)

if response.status_code == 200:
    # Parse JSON response
    data = response.json()
    
    if 'primary_snapshot_data' in data:
        primary_data = data['primary_snapshot_data']
        
        # Extract allele frequency information if available
        if 'allele_annotations' in primary_data:
            allele_annotations = primary_data['allele_annotations']
            
            for annotation in allele_annotations:
                if 'frequency' in annotation:
                    print(f"Allele Frequency: {annotation['frequency']}")

    else:
        print("Variant information not found in dbSNP.")
else:
    print(f"Failed to retrieve data from dbSNP API. Status code: {response.status_code}")
