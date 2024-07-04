	for collection in analyses biosamples individuals runs cohorts datasets genomicVariations budget history
  do
    mongoimport --jsonArray \
    --uri "mongodb://root:${DB_PASSWD}@127.0.0.1:27017/beacon?authSource=admin" \
		--file input_data/cineca_with_datasetid/${collection}.json --collection ${collection} ;
	done


pip3 install python3

# Run the Python script to update allele frequencies
python3 update_allele_frequencies.py