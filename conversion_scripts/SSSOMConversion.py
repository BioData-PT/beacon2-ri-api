import pandas as pd
from sssom.parsers import parse_sssom_table

def load_metadata(file_path):
    return pd.read_json(file_path)

def save_metadata(metadata, output_path):
    metadata.to_json(output_path, orient='records', indent=4)

def transform_metadata(metadata, mapping_df):
    transformed = {}
    mapping_dict = {row['subject_id'].split('#')[-1]: row['object_id'].split('#')[-1]
                    for _, row in mapping_df.iterrows()}

    for source_field, target_field in mapping_dict.items():
        if source_field in metadata:
            transformed[target_field] = metadata[source_field]
        else:
            print(f"Warning: '{source_field}' not found in metadata.")
    return transformed

def main(metadata_file, mapping_file, output_file):
    # Load metadata
    metadata = load_metadata(metadata_file)

    # Load SSSOM mapping
    mapping = parse_sssom_table(mapping_file)
    mapping_df = mapping.mapping_df

    # Transform metadata
    transformed_metadata = transform_metadata(metadata, mapping_df)

    # Save transformed metadata
    save_metadata(pd.DataFrame([transformed_metadata]), output_file)
    print(f"Transformed metadata saved to {output_file}")

if __name__ == "__main__":
    # Input paths
    metadata_file = 'metadata.json'
    mapping_file = 'mapping.sssom.tsv'
    output_file = 'transformed_metadata.json'

    # Run the script
    main(metadata_file, mapping_file, output_file)
