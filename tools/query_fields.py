"""Read saved Jet query field order without executing SQL or using COM."""
import argparse
import hashlib
import json
import logging
from pathlib import Path

from client.catalogue import validated_rows


def inspect_query(path, name):
    from access_parser import AccessParser
    # Query definitions are intentionally omitted from the parser's public
    # catalogue. Locate the system table by its parsed MSysObjects identity.
    class PropertyDiagnostics(logging.Filter):
        def filter(self, record):
            return record.getMessage() != 'Error while parsing MSysObjects table chunk.'
    logger = logging.getLogger('access_parser')
    diagnostics = PropertyDiagnostics()
    logger.addFilter(diagnostics)
    try:
        database = AccessParser(str(path))
    finally:
        logger.removeFilter(diagnostics)
    table = database.get_table('MSysObjects')
    objects = validated_rows('MSysObjects', table.parse(), table.table_header.number_of_rows, 'Id')
    queries = [row for row in objects if row['Name'] == name and row['Type'] == 5]
    systems = [row for row in objects if row['Name'] == 'MSysQueries' and row['Type'] == 1]
    if len(queries) != 1 or len(systems) != 1:
        raise ValueError('missing or ambiguous saved query/system table')
    database.catalog['MSysQueries'] = systems[0]['Id']
    table = database.get_table('MSysQueries')
    rows = validated_rows('MSysQueries', table.parse(), table.table_header.number_of_rows)
    matched = [row for row in rows if row['ObjectId'] == queries[0]['Id']]
    fields = [row for row in matched if row['Attribute'] == 6]
    if (not fields or any(not isinstance(row['Order'], bytes) or len(row['Order']) != 4
                         or not isinstance(row['Expression'], str) for row in fields) or
            len({row['Order'] for row in fields}) != len(fields)):
        raise ValueError('incomplete or ambiguous saved selection order')
    fields.sort(key=lambda row: row['Order'])
    for row in matched:
        if row['Order'] is not None:
            row['Order'] = row['Order'].hex()
    return dict(source_sha256=hashlib.sha256(database.db_data).hexdigest(),
        query_name=name, query_id=queries[0]['Id'],
        declared_query_table_rows=table.table_header.number_of_rows,
        parsed_query_table_rows=len(rows),
        selected_fields=[dict(zero_based_index=i, expression=row['Expression'], order_hex=row['Order'])
                         for i, row in enumerate(fields)], query_rows=matched)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('database', type=Path)
    parser.add_argument('query')
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    result = json.dumps(inspect_query(args.database, args.query), indent=2)
    if args.output:
        args.output.write_text(result+'\n', encoding='utf-8')
    else:
        print(result)


if __name__ == '__main__':
    main()
