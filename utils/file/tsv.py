import csv
import io


def convert_tsv(path=None, content=None):
    lcontent = []
    if content is None:
        content = open(path, 'r', newline='', encoding='utf-8')
    else:
        content = io.StringIO(content)
    reader = csv.DictReader(content, delimiter='\t')
    for row in reader:
        lcontent.append(row)
    print("TSV content extracted")
    return lcontent
