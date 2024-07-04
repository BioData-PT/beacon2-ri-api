	for collection in analyses biosamples individuals runs cohorts datasets genomicVariations budget history
  do
    mongoimport --jsonArray \
    --uri "mongodb://root:${DB_PASSWD}@127.0.0.1:27017/beacon?authSource=admin" \
		--file input_data/cineca_with_datasetid/${collection}.json --collection ${collection} ;
	done

# Check if python3 is installed and in the PATH
PYTHON3_PATH=$(which python3)
if [ -z "$PYTHON3_PATH" ]; then
    echo "python3 is not installed or not in the PATH."
    exit 1
else
    echo "Found python3 at $PYTHON3_PATH"
fi

# python script to update allele frequencies in genomicVariantions collection
python3 update_allele_frequencies.py
