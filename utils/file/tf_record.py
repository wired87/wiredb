import os
import gzip
import csv
import requests
import chardet  # Detects file encoding
import tensorflow as tf  # For parsing .tfrecord files


def detect_encoding(file_path, num_bytes=10000):
    """
    Detects the encoding of a file using `chardet`.
    Reads `num_bytes` from the file to infer the encoding.
    """
    with open(file_path, 'rb') as f:
        raw_data = f.read(num_bytes)
    encoding_info = chardet.detect(raw_data)
    print(f"Detected encoding for {file_path}: {encoding_info}")
    return encoding_info['encoding']


def extract_gz_file(gz_file_path, output_dir):
    """
    Extracts a .gz file to the specified output directory.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)

    file_name = os.path.basename(gz_file_path).replace('.gz', '')
    output_file_path = os.path.join(output_dir, file_name)

    print(f"Extracting {gz_file_path} to {output_file_path}...")
    with gzip.open(gz_file_path, 'rb') as gz_file:
        with open(output_file_path, 'wb') as out_file:
            out_file.write(gz_file.read())

    return output_file_path


def parse_vcf(vcf_file_path):
    """
    Parses a VCF file and yields variant information as dictionaries.
    """
    encoding = detect_encoding(vcf_file_path)  # Detect encoding dynamically
    print(f"Opening VCF file: {vcf_file_path} with encoding: {encoding}")

    with open(vcf_file_path, 'r', encoding=encoding, errors="replace") as f:
        for line in f:
            if line.startswith('#'):
                continue  # Skip header lines

            columns = line.strip().split('\t')
            if len(columns) < 8:
                print(f"Skipping malformed line: {line.strip()}")
                continue  # Skip malformed lines

            variant = {
                'chrom': columns[0],
                'pos': columns[1],
                'id': columns[2],
                'ref': columns[3],
                'alt': columns[4],
                'qual': columns[5],
                'filter': columns[6],
                'info': columns[7],
                'format': columns[8] if len(columns) > 8 else None,
                'sample': columns[9] if len(columns) > 9 else None
            }
            print(f"Parsed Variant: {variant}")
            yield variant


def parse_tfrecord(tfrecord_file_path):
    """
    Parses a TensorFlow .tfrecord file and yields variant information.
    """
    print(f"Parsing TFRecord file: {tfrecord_file_path}")

    raw_dataset = tf.data.TFRecordDataset(tfrecord_file_path)

    for raw_record in raw_dataset:
        example = tf.train.Example()
        example.ParseFromString(raw_record.numpy())

        # Extract variant fields (assuming schema follows TensorFlow VariantCall)
        variant = {
            'chrom': example.features.feature['CHROM'].bytes_list.value[0].decode('utf-8'),
            'pos': str(example.features.feature['POS'].int64_list.value[0]),
            'id': example.features.feature['ID'].bytes_list.value[0].decode('utf-8'),
            'ref': example.features.feature['REF'].bytes_list.value[0].decode('utf-8'),
            'alt': example.features.feature['ALT'].bytes_list.value[0].decode('utf-8'),
            'qual': str(example.features.feature['QUAL'].float_list.value[0]),
            'filter': example.features.feature['FILTER'].bytes_list.value[0].decode('utf-8'),
            'info': example.features.feature['INFO'].bytes_list.value[0].decode('utf-8'),
        }
        print(f"Parsed Variant from TFRecord: {variant}")
        yield variant


def annotate_variant(variant):
    """
    Annotates a variant using the Ensembl VEP REST API.
    """
    server = "https://rest.ensembl.org"
    ext = f"/vep/human/region/{variant['chrom']}:{variant['pos']}/{variant['ref']}/{variant['alt']}?"
    headers = {"Content-Type": "application/json"}

    print(f"Requesting annotation for variant: {variant}")
    response = requests.get(server + ext, headers=headers)

    if not response.ok:
        print(f"Warning: API call failed for variant {variant}, Status Code: {response.status_code}")
        return None

    try:
        annotation_data = response.json()
        print(f"Received Annotation: {annotation_data}")
        return annotation_data
    except requests.exceptions.JSONDecodeError:
        print(f"Warning: Failed to parse JSON for variant {variant}")
        return None


def save_annotations_to_csv(annotations, output_csv_path):
    """
    Saves the list of annotations to a CSV file.
    """
    if not annotations:
        print("No annotations to save.")
        return

    flattened_annotations = []
    for annotation in annotations:
        if isinstance(annotation, list):
            for item in annotation:
                flattened_annotations.append(item)
        else:
            flattened_annotations.append(annotation)

    keys = flattened_annotations[0].keys() if flattened_annotations else []
    print(f"Saving annotations to {output_csv_path}...")

    with open(output_csv_path, 'w', newline='', encoding="utf-8") as csv_file:
        dict_writer = csv.DictWriter(csv_file, fieldnames=keys)
        dict_writer.writeheader()
        dict_writer.writerows(flattened_annotations)

    print(f"Annotations saved successfully at {output_csv_path}!")


def main(input_file, output_dir):
    """
    Main function to process both VCF and TFRecord files.
    """
    output_csv_path = os.path.join(output_dir, "annotations.csv")
    annotations = []

    # Extract if the file is gzipped
    if input_file.endswith('.gz'):
        extracted_file = extract_gz_file(input_file, output_dir)
    else:
        extracted_file = input_file

    # Determine file format
    if extracted_file.endswith('.vcf'):
        print(f"Starting VCF processing: {extracted_file}")
        variants = parse_vcf(extracted_file)
    elif extracted_file.endswith('.tfrecord'):
        print(f"Starting TFRecord processing: {extracted_file}")
        variants = parse_tfrecord(extracted_file)
    else:
        print(f"Unsupported file format: {extracted_file}")
        return

    # Process each variant
    for variant in variants:
        annotation = annotate_variant(variant)
        if annotation:
            annotations.append(annotation)

    # Save the annotated variants
    save_annotations_to_csv(annotations, output_csv_path)
    print(f"Annotations process completed! Output saved to {output_csv_path}")


if __name__ == "__main__":
    input_file = "/uutils/models/deep_variant/admin_data/output\\intermediate_results_dir\\call_variants_output-00000-of-00001.tfrecord\\call_variants_output-00000-of-00001.tfrecord"
    output_file = "/uutils/models/deep_variant/admin_data/output\\intermediate_results_dir\\call_variants_output.json"

    main(input_file, output_file)
