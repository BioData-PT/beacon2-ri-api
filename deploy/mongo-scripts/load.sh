	for collection in analyses biosamples individuals runs cohorts datasets genomicVariations budget history
  do
    mongoimport --jsonArray \
    --uri "mongodb://root:${DB_PASSWD}@127.0.0.1:27017/beacon?authSource=admin" \
		--file input_data/cineca_with_datasetid/${collection}.json --collection ${collection} ;
	done

# Check if python3 is installed
PYTHON3_PATH=$(which python3)
if [ -z "$PYTHON3_PATH" ]; then
    echo "python3 is not installed or not in the PATH."
    exit 1
fi

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# python script to update allele frequencies in genomicVariantions collection
python3 update_allele_frequencies.py

# Deactivate virtual environment if it was activated
if [ -d "venv" ]; then
    deactivate
fi