import requests
import time

genomic_hgvs_id = '22:g.16050075A>G'
url = f'https://api.ncbi.nlm.nih.gov/variation/v0/refsnp/{genomic_hgvs_id}'

def query_dbsnp_api(url):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f'HTTP error occurred: {http_err}')
    except Exception as err:
        print(f'Other error occurred: {err}')

    return None

# Retry up to 3 times
retry_attempts = 3
retry_delay = 5  # seconds

for attempt in range(1, retry_attempts + 1):
    print(f"Attempt {attempt}...")
    data = query_dbsnp_api(url)
    
    if data:
        # Process the data as needed
        if 'primary_snapshot_data' in data:
            primary_data = data['primary_snapshot_data']
            if 'allele_annotations' in primary_data:
                allele_annotations = primary_data['allele_annotations']
                for annotation in allele_annotations:
                    if 'frequency' in annotation:
                        print(f"Allele Frequency: {annotation['frequency']}")
        
        break  # Exit loop if successful
    
    # If unsuccessful, wait and retry
    if attempt < retry_attempts:
        print(f"Waiting {retry_delay} seconds before retrying...")
        time.sleep(retry_delay)
    else:
        print(f"Failed after {retry_attempts} attempts. Check dbSNP API status.")

