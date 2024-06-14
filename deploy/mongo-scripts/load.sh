	for collection in analyses biosamples individuals runs cohorts datasets genomicVariations
  do
    mongoimport --jsonArray \
    --uri "mongodb://root:${DB_PASSWD}@127.0.0.1:27017/beacon?authSource=admin" \
		--file input_data/cineca_with_datasetid/analyses*.json --collection $${collection} ;
	done
