import requests
import json

def lift_over(positions):
    url = "https://api.genome.ucsc.edu/liftOver"
    data = {
        "positions": positions,
        "from": "hg19",
        "to": "hg38"
    }
    
    try:
        response = requests.post(url, json=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Check if response contains JSON data
        if response.headers.get('content-type') == 'application/json':
            result = response.json()
            return result
        else:
            print(f"Unexpected response format: {response.headers.get('content-type')}")
            return None
    
    except requests.exceptions.RequestException as e:
        print(f"Error making LiftOver request: {e}")
        return None
    except json.JSONDecodeError as e:
        print(f"Error decoding JSON response: {e}")
        return None

def main():
    input_position = "22:16052394"
    input_change = "GAAAGCCAGAACCACTC>G"
    input_data = f"{input_position} {input_change}"
    positions = [{"position": input_data}]
    
    result = lift_over(positions)
    if result:
        lifted_over_position = result[0].get("position", "")
        print(f"Lifted over position: {lifted_over_position}")

if __name__ == "__main__":
    main()
