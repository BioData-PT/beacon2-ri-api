import requests

# Define genomic coordinates
chromosome = '22'
start = 16050075
end = 16050075

# Construct the URL to query dbSNP Batch API by genomic coordinates
url = f'https://api.ncbi.nlm.nih.gov/variation/v0/beta/human/{chromosome}:{start}-{end}'

# Make a GET request to the API
response = requests.get(url)

if response.status_code == 200:
    # Parse JSON response
    data = response.json()
    # Process the data as needed
    print(data)
else:
    print(f"Failed to retrieve data from dbSNP API. Status code: {response.status_code}")
