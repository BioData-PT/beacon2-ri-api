import requests

def lift_over(positions):
    url = "https://api.genome.ucsc.edu/liftOver"
    data = {
        "positions": positions,
        "from": "hg19",
        "to": "hg38"
    }
    response = requests.post(url, json=data)
    if response.status_code == 200:
        result = response.json()
        return result
    else:
        print(f"Error: {response.status_code}, {response.text}")
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
