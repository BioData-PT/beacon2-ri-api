import requests

def liftover_37_to_38(chromosome, position, ref_allele, alt_allele):
    url = "http://genome.ucsc.edu/cgi-bin/hgLiftOver"
    data = {
        'hgsid': '351',  # This is a placeholder, you can get a valid session ID from UCSC website.
        'fromP': 'hg19',
        'toP': 'hg38',
        'submit': 'Submit',
        'pos': f'{chromosome}:{position}-{position}'
    }

    response = requests.post(url, data=data)
    if response.status_code == 200:
        converted = response.text
        # Parsing the result to extract the new position
        lines = converted.split('\n')
        if len(lines) > 1:
            new_position_line = lines[1].strip()
            parts = new_position_line.split()
            if len(parts) >= 2:
                new_position = parts[1]
                new_chromosome, new_start_end = new_position.split(':')
                new_start, new_end = map(int, new_start_end.split('-'))
                new_start += 1  # Convert from 0-based to 1-based coordinate
                print(f"GRCh38: {new_chromosome}:{new_start} {ref_allele}>{alt_allele}")
                return new_chromosome, new_start, ref_allele, alt_allele
            else:
                print("Error: Could not parse converted coordinates.")
        else:
            print("Error: Could not convert coordinates.")
    else:
        print(f"Error: UCSC LiftOver request failed with status code {response.status_code}")

# Example usage
chromosome = '22'
position = 16064513
ref_allele = 'A'
alt_allele = 'AAGAATGGCCTAATAC'

liftover_37_to_38(chromosome, position, ref_allele, alt_allele)
