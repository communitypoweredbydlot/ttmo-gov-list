import click
import pandas as pd
import os
import re

from collections import namedtuple
from enum import Enum
from functools import reduce
from unidecode import unidecode
from typing import Callable, Tuple, Type, List

CLEANING_RULE = Enum('CLEANING_RULE', 'CONVERT_CHARS REMOVE_EXTRA_END_SPACES REMOVE_EXTRA_END_QUOTES '
                                      'REMOVE_SPACES_AFTER_QUOTES CORRECT_STICKY_DASHES REMOVE_MULTI_WHITESPACE '
                                      'EXPAND_ABBREVIATIONS CORRECT_WORDS CORRECT_NAMES FORMAT_PARENTHESIS '
                                      'ADD_SPACE_AFTER_DOT')

Cleaned = namedtuple('Cleaned', 'nr certificate_number registration_date name administrator location county')
Errors = namedtuple('Errors', 'certificate_number column correction')


def replace_through(text: str, lens: Callable[[str], str], pattern: str, new: str) -> str:
    t_l = list(text)
    n_t = []
    s_i = 0
    for match in re.finditer(pattern, lens(''.join(t_l)), flags=re.IGNORECASE if new is not None else 0):
        replacement = new if new is not None else f' {match[0]}'
        n_t = n_t + t_l[s_i:match.start()] + list(replacement) + t_l[match.end():s_i + 1]
        s_i = match.end()
    return ''.join(n_t + t_l[s_i:])


def replace(value: str, pattern_map: dict) -> str:
    new_value = value
    for pattern, new in pattern_map.items():
        new_value = replace_through(new_value, lambda x: unidecode(x), pattern, new)
    return new_value


def validate_with(clean_function: Tuple[Callable[[str], str], type(CLEANING_RULE)],
                  column_value: Tuple[str, List[Type[CLEANING_RULE]]]) -> Tuple[str, List[Type[CLEANING_RULE]]]:
    cleaned_value = clean_function[0](column_value[0])
    trace = column_value[1] if cleaned_value == column_value[0] else column_value[1] + [clean_function[1]]
    return cleaned_value, trace


def remove_extra_end_spaces(column_value: str) -> str:
    return column_value.strip(' ')


def remove_extra_end_quotes(value: str):
    while value.endswith('"') and value.startswith('"'):
        value = value[1:-1]
    return value


def remove_spaces_after_quotes(value: str):
    return value.replace('" ', '"')


def add_space_after_dot(value: str) -> str:
    return value.replace('.', '. ')


def format_parenthesis(value: str) -> str:
    return value.replace('( ', ' (').replace(' )', ') ').replace('(', ' (').replace(')', ') ')


def expand_abbreviations(value: str) -> str:
    return replace(value, {
        r'\bCurm\.': 'Curmătura',
        r'\bM - tii': 'Munții',
        r"\bcom\.": 'Comuna',
        r'\bcab\.': 'Cabana',
        r'\bIzv\.': 'Izvorul',
        r'\bV\.': 'Vârful',
        r'\bVf\.': 'Vârful',
        r'\bVf': 'Vârful',
        r'\bM\.': 'Muntele',
        r'\bdl\.': 'Dealul',
        r'\bPr\.': 'Pâraul',
        r'\bstr\.': 'Strada',
        r'\bref\.': 'Refugiul',
        r'\bP - na': 'Poiana',
        r'\bVal\.': 'Valea',
        r'\bVl\.': 'Valea',
        r'\bH\.': 'Hotel',
        r'\bDe\.': 'Dealul',
        r"\bloc\.": 'Localitatea',
        r'\bS - na': 'Stâna',
        r'\bjud\.': 'Județul',
        r'\bPens\.': 'Pensiunea',
        r'\bP\.': 'Poiana',
        r'\bStat\.': 'Stațiunea',
        r'\bMan\.': 'Mănastirea',
        r'\bCh\.': 'Cheile',
        r'\bacum\.': 'acumulare',
        r'\bst\.': 'Stație',
        r'\bDr\.': 'Drumul',
        r'\bRez\.': 'Rezervația',
        r'\B[A-Z][a-z]+': None,
        r'\({0,1}\d+ *m\){0,1}': ''
    })


def correct_sticky_dashes(column_value: str) -> str:
    return column_value.replace('-', ' - ')


def clean_loose_dashes(column_value: str) -> str:
    return column_value.replace(' - ', '-').replace(' -', '-').replace('- ', '-')


def remove_multi_whitespaces(column_value: str) -> str:
    return ' '.join(column_value.split())


def correct_names(value: str) -> str:
    return replace(value, {
        'Caras - Severin': 'Caraș-Severin',
        'Bistrita - Nasaud': 'Bistrița-Năsăud',
        'Satu - Mare': 'Satu Mare',
        'Cluj Napoca': 'Cluj-Napoca',
        'Cluj - Napoca': 'Cluj-Napoca'
    })


def convert_chars(columns_value: str):
    return columns_value.translate({
        ord('Ş'): 'Ș',
        ord('ş'): 'ș',
        ord('Ţ'): 'Ț',
        ord('ţ'): 'ț',
        ord('Ã'): 'Ă',
        ord('ã'): 'ă',
        ord('Ǎ'): 'Ă',
        ord('ǎ'): 'ă',
        ord('“'): '"',
        ord('”'): '"',
        ord('–'): '-',
    })


def correct_words(value: str) -> str:
    return replace(value, {
        'consiliull': 'Consiliul',
        'judetean': 'Județean',
        'primaria': 'Primăria',
        'saua': 'Șaua',
        'muntele': 'Muntele',
        'izvorul': 'Izvorul',
        'pasul': 'Pasul',
        'poiana': 'Poiana',
        'dealul': 'Dealul',
        'izbucul': 'Izbucul',
        'turnul': 'Turnul',
        'cascada': 'Cascada',
        'ascutit': 'Ascuțit',
        'valea': 'Valea',
        'belvedere': 'Belvedere',
        'malul': 'Malul',
        'paraul': 'Pârâul',
        'silvic': 'Silvic'
    })


def clean_string_column(value: str) -> Tuple[str, List[Type[CLEANING_RULE]]]:
    return clean_column([
        (convert_chars, CLEANING_RULE.CONVERT_CHARS),
        (add_space_after_dot, CLEANING_RULE.ADD_SPACE_AFTER_DOT),
        (format_parenthesis, CLEANING_RULE.FORMAT_PARENTHESIS),
        (remove_extra_end_spaces, CLEANING_RULE.REMOVE_EXTRA_END_SPACES),
        (remove_spaces_after_quotes, CLEANING_RULE.REMOVE_SPACES_AFTER_QUOTES),
        (remove_extra_end_quotes, CLEANING_RULE.REMOVE_EXTRA_END_QUOTES),
        (correct_sticky_dashes, CLEANING_RULE.CORRECT_STICKY_DASHES),
        (remove_multi_whitespaces, CLEANING_RULE.REMOVE_MULTI_WHITESPACE),
        (expand_abbreviations, CLEANING_RULE.EXPAND_ABBREVIATIONS),
        (correct_words, CLEANING_RULE.CORRECT_WORDS),
        (correct_names, CLEANING_RULE.CORRECT_NAMES),
        (remove_multi_whitespaces, CLEANING_RULE.REMOVE_MULTI_WHITESPACE),
        (remove_extra_end_spaces, CLEANING_RULE.REMOVE_EXTRA_END_SPACES),
    ], value)


def clean_column(cleaning_functions: Tuple[Callable[[str], str], Type[CLEANING_RULE]],
                 column_value: str) -> Tuple[str, List[Type[CLEANING_RULE]]]:
    return reduce(lambda x, y: validate_with(y, x), cleaning_functions, (column_value, []))


def clean(source_df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    print('Sanitizing the data.')

    errors = []
    cleaned_rows = []
    for row in source_df.dropna().itertuples(index=False):
        s_name, name_errors = clean_string_column(row.name)
        s_administrator, administrator_errors = clean_string_column(row.administrator)
        s_location, location_errors = clean_string_column(row.location)
        s_county, county_errors = clean_string_column(row.county)
        s_certificate_number = re.match(r'^(\d+)', str(row.certificate_number)).group() if str(
            row.certificate_number) else row.certificate_number

        for ne in name_errors:
            errors.append(Errors(certificate_number=row.certificate_number, column='name', correction=ne))

        for ae in administrator_errors:
            errors.append(Errors(certificate_number=row.certificate_number, column='administrator', correction=ae))

        for le in location_errors:
            errors.append(Errors(certificate_number=row.certificate_number, column='location', correction=le))

        for ce in county_errors:
            errors.append(Errors(certificate_number=row.certificate_number, column='county', correction=ce))

        cleaned_rows.append(Cleaned(
            nr=row.nr,
            certificate_number=s_certificate_number,
            registration_date=row.registration_date,
            name=s_name,
            administrator=s_administrator,
            location=s_location,
            county=s_county
        ))
    return pd.DataFrame(cleaned_rows), pd.DataFrame(errors)


@click.command()
@click.argument('xls_file',
                default='data/original/turism_gov_ro/ttmo_approved_list.xls',
                required=True,
                type=click.Path(exists=True, dir_okay=False, readable=True))
@click.argument('csv_file',
                default='data/clean/turism_gov_ro/uniform/ttmo_gov_list.csv',
                required=True,
                type=click.Path(exists=False, dir_okay=False, writable=True))
@click.option('--sheet-name', '-s', default=0, type=int, help="The name of the sheet to convert.")
def convert_and_clean(xls_file, csv_file, sheet_name):
    """
    Convert the the xls to csv and write a clean-ish copy to the destination folder.
    """
    print('Loading the xls file.')
    source_df = pd.read_excel(xls_file, sheet_name=sheet_name, header=5,
                              parse_dates=[3], usecols=range(1, 8),
                              dtype={
                                    'Denumire traseu': 'string',
                                    'Administrator': 'string',
                                    'Amplasare': 'string',
                                    'Judeţ': 'string'
                                },
                              converters={
                                    'Nr. crt.': lambda v: int(v),
                                }
                              ).dropna()

    source_csv_dest_path = f'{os.path.splitext(xls_file)[0]}.csv'
    print(f'Writing a CSV copy without modifications to {source_csv_dest_path}')
    source_df.to_csv(source_csv_dest_path, index=False, date_format='%Y-%m-%d')

    print('Cleaning the source dataset.')
    source_df.rename(columns={
        'Nr. crt.': 'nr',
        'Nr. Certificat': 'certificate_number',
        'Data emiterii': 'registration_date',
        'Denumire traseu': 'name',
        'Administrator': 'administrator',
        'Amplasare': 'location',
        'Judeţ': 'county'
    }, inplace=True)

    cleaned_df, errors_df = clean(source_df)

    errors_file_name = f'{os.path.splitext(csv_file)[0]}.error.csv'
    print(f'Writing the errors file to {errors_file_name}.')
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    errors_df.to_csv(errors_file_name, index=False)

    print(f'Writing the clean-ish csv file to {csv_file}')
    cleaned_df.to_csv(csv_file, index=False, date_format='%Y-%m-%d')


if __name__ == '__main__':
    convert_and_clean()
