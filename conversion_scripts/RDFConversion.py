# Requirements: pip install rdflib

# Example input: 
# {
#  "gender": "male",
#  "birth_date": "1990-01-01"
# }

# RDF Mapping: Use the example RDFMapping file


import xml.etree.ElementTree as ET
import json
import sys

def load_alignment_mapping(mapping_file):
    """
    Parse the Alignment API XML file and extract mappings.
    """
    tree = ET.parse(mapping_file)
    root = tree.getroot()
    
    # Namespace adjustment for your RDF structure
    ns = {'alignment': 'http://knowledgeweb.semanticweb.org/heterogeneity/alignment'}

    mappings = {}
    for cell in root.findall('.//alignment:map/alignment:Cell', ns):
        entity1 = cell.find('alignment:entity1', ns)
        entity2 = cell.find('alignment:entity2', ns)

        # Ensure <entity1> and <entity2> are not None and have 'rdf:resource'
        if entity1 is not None and entity2 is not None:
            entity1_resource = entity1.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')
            entity2_resource = entity2.get('{http://www.w3.org/1999/02/22-rdf-syntax-ns#}resource')

            if entity1_resource and entity2_resource:
                source_field = entity1_resource.split('#')[-1]
                target_field = entity2_resource.split('#')[-1]
                mappings[source_field] = target_field

    return mappings

def transform_metadata(metadata, mappings):
    """
    Transform metadata based on the extracted mapping.
    """
    transformed = {}
    for source_field, target_field in mappings.items():
        if source_field in metadata:
            transformed[target_field] = metadata[source_field]
    return transformed

def main(metadata_file, mapping_file, output_file):
    """
    Main function to transform metadata using Alignment API mapping.
    """
    # Load metadata
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)

    # Load alignment mapping
    mappings = load_alignment_mapping(mapping_file)

    # Transform metadata
    transformed_metadata = transform_metadata(metadata, mappings)

    # Save transformed metadata
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(transformed_metadata, f, indent=4, ensure_ascii=False)

    print(f"Transformed metadata saved to: {output_file}")

if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Use: python alignment_transform.py <metadata_file.json> <mapping_file.xml> <output_file.json>")
        sys.exit(1)
    metadata_file = sys.argv[1]
    mapping_file = sys.argv[2]
    output_file = sys.argv[3]
    main(metadata_file, mapping_file, output_file)
