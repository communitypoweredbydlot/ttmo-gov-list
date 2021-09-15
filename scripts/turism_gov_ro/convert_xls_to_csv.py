import argparse
from threading import ExceptHookArgs
import pandas as pd
import os
import re



from functools import reduce
from rich.console import Console
from pandas_schema import Schema, Column
from pandas_schema.validation import LeadingWhitespaceValidation, TrailingWhitespaceValidation, DateFormatValidation, CanConvertValidation, MatchesPatternValidation, CustomElementValidation

console = Console()


def validate_with(clean_function, column_value):
    cleaned_value = clean_function[0](column_value[0])
    return cleaned_value, column_value[1] if cleaned_value == column_value else column_value[1] + [clean_function[1]]


def clean_extra_quotes(column_value):
    return column_value.strip('" “')


def clean_conflicting_abbreviations(column_value):
    return column_value.replace('M-ţii', 'Munții').replace('M-ții', 'Munții')


def clean_em_dashes(column_value):
    return column_value.replace('–', '-')


def clean_sticky_dashes(column_value):
    return column_value.replace('-', ' - ')


def clean_multi_whitespaces(column_value):
    return ' '.join(column_value.split())


def clean_string_column(column_value):
    cleaning_functions = [
        (clean_extra_quotes, 'Had extra quotes'),
        (clean_conflicting_abbreviations, 'Had abbreviations'),
        (clean_em_dashes, 'Had em dashed'),
        (clean_sticky_dashes, 'Has sticky dashes'),
        (clean_multi_whitespaces, 'Had runny whitespaces')
    ]

    return reduce(lambda x, y: validate_with(y, x), cleaning_functions, (column_value, []))


def convert_xls_to_csv(xls_file, csv_file, sheet_name):
    console.print('Loading the xls file.')
    df = pd.read_excel(xls_file, sheet_name=sheet_name, header=5, parse_dates=[3], usecols=range(1, 8))

    console.print('Cleaning the data.')
    stats = {
        'original-rows': len(df.index),
        'rows': 0
    }
    df = df.dropna()

    stats['rows'] = len(df.index)
    errors = []
    def clean_pandas_row(row):
        col3_value, col3_errors = clean_string_column(row[3])
        col4_value, col4_errors = clean_string_column(row[4])
        col5_value, col5_errors = clean_string_column(row[5])
        col6_value, col6_errors = clean_string_column(row[6])

        if col3_errors or col4_errors or col5_errors or col6_errors:
            errors.append({
                'id': row[1],
                '3': col3_errors,
                '4': col4_errors,
                '5': col5_errors,
                '6': col6_errors
            })

        return int(row[0]), re.match(r'^(\d+)', str(row[1])).group() if str(row[1]) else row[1], row[2], col3_value, col4_value, col5_value, col6_value

    df = df.apply(clean_pandas_row, axis=1, result_type='expand')



    n_errors = len(errors)
    csv_file_name = os.path.splitext(os.path.basename(csv_file))[0]
    errors_file_name = f'{csv_file_name}.errors.txt'
    console.print(f' {n_errors} Errors found. Writing the {errors_file_name} errors file.')

    with open(errors_file_name, 'w') as f:
        f.write('\n'.join(map(lambda e: str(e), errors)))

    console.print('Converting the xls file to csv.')
    df.dropna().to_csv(csv_file, index=False, date_format='%Y-%m-%d')
    console.print(f'Conversion complete. Output file: {csv_file}')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Convert XLS to CSV.')
    parser.add_argument('xls_file', help='XLS file to convert.')
    parser.add_argument('csv_file', help='CSV file to create.')
    parser.add_argument('--sheet-name', help='Sheet name to convert.', default=0)
    args = parser.parse_args()

    convert_xls_to_csv(args.xls_file, args.csv_file, args.sheet_name)
