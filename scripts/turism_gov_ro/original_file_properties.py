import datefinder
import magic
import os
import json

from datetime import date, datetime
import re


def get_fingerprint_from_file(file_path: str) -> dict:
    file_header_info = magic.from_file(file_path)
    return _get_fingerprint(file_path, file_header_info)


def get_fingerprint_from_buffer(file_name, buffer):
    file_header_info = magic.from_buffer(buffer)
    return _get_fingerprint(file_name, file_header_info)


def _get_fingerprint(file_path, file_header_info: str) -> dict:
    file_header_info.split(',')
    file_properties = dict(
        [(kv[0].strip(), kv[1].strip()) for kv in map(lambda x: x.split(':', 1), file_header_info.split(',')) if
         len(kv) == 2])

    computed_properties = {}
    if 'Last Saved Time/Date' in file_properties:
        last_saved_at = list(datefinder.find_dates(file_properties['Last Saved Time/Date']))[0]
        computed_properties['last_updated_at'] = last_saved_at

    if 'Create Time/Date' in file_properties:
        created_at = list(datefinder.find_dates(file_properties['Create Time/Date']))[0]
        computed_properties['created_at'] = created_at

    original_filename = os.path.basename(file_path)
    filename_date_claim = parse_filename_date(original_filename)
    if filename_date_claim:
        computed_properties['claimed_fresh_at'] = filename_date_claim

    return computed_properties


def parse_filename_date(filename: str) -> date | None:
    """
    Parses the date from the gov filename.
    The expected format is <day>.<month>.<year>

    We use this to determine the folder to store the file in.

    :param filename: The filename to parse.
    :return: The date if found, None otherwise.
    """
    filename_date_claim = re.search(r'\d{2}\.\d{2}\.\d{4}', filename)
    if filename_date_claim:
        return datetime.strptime(filename_date_claim[0], '%d.%m.%Y').date()
    else:
        return None


def get_original_file_info(path: str = None) -> dict:
    """
    Gets the contents of the info.json file corresponding to the given base folder.

    :param path: Base folder path. If None, it will try to find the most recent base folder.
    :return:
    """
    if path is None:
        path = find_most_recent_base_folder()

    info_file_path = os.path.join(path, 'original', 'info.json')
    if os.path.isfile(info_file_path):
        with open(info_file_path, 'r') as ifile:
            return json.load(ifile)
    else:
        return {}


def destination_base_folder(fingerprint: dict) -> str:
    """
    Returns the base folder where the file should be stored.
    :param fingerprint: Fingerprint of the file.
    :return:
    """
    last_update_date = fingerprint.get('last_updated_at', date.today())
    return os.path.join(os.path.normpath(
        fingerprint.get('claimed_fresh_at', last_update_date).strftime('%Y/%m/%d')
    ), last_update_date.strftime('%Y%m%d%H%M%S'))


def find_most_recent_base_folder(root_folder='data'):
    path = os.path.join(root_folder)

    max_year_folder = max(os.listdir(path), key=lambda x: int(x))
    path = os.path.join(path, max_year_folder)

    max_month_folder = max(os.listdir(path), key=lambda x: int(x))
    path = os.path.join(path, max_month_folder)

    max_day_folder = max(os.listdir(path), key=lambda x: int(x))
    path = os.path.join(path, max_day_folder)

    max_modified_folder = max(os.listdir(path), key=lambda x: int(x))
    path = os.path.join(path, max_modified_folder)

    return path
