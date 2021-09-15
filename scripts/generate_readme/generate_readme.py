import argparse
import datefinder
import json
import magic
import os

from jinja2 import Environment, FileSystemLoader
from urllib.parse import urlparse


env = Environment(
    loader=FileSystemLoader("templates")
)

def get_source_file_properties(file_path: str) -> dict:
    file_header_info = magic.from_file(file_path)
    file_header_info.split(',')
    file_properties = dict([(kv[0].strip(),kv[1].strip())  for kv in map(lambda x: x.split(':', 1), file_header_info.split(',')) if len(kv) == 2])

    computed_properties = {}
    if 'Last Saved Time/Date' in file_properties:
        last_saved_at = list(datefinder.find_dates(file_properties['Last Saved Time/Date']))[0]
        computed_properties['last_updated_at'] = last_saved_at.strftime('%Y-%m-%d')
    
    if 'Create Time/Date' in file_properties:
        created_at = list(datefinder.find_dates(file_properties['Create Time/Date']))[0]
        computed_properties['created_at'] = created_at.strftime('%Y-%m-%d')
    
    return computed_properties


def get_download_url(file_path: str) -> str:
    info_file_path = os.path.join(os.path.dirname(file_path), 'info.json')
    if os.path.isfile(info_file_path):
        with open(info_file_path, 'r') as ifile:
            download_url = json.load(ifile).get('download_url')
            download_url_properties = { 'original_dataset_download_url': download_url }
            if download_url:
                original_filename = os.path.basename(urlparse(download_url).path)
                filename_date_claim = list(datefinder.find_dates(original_filename))
                if len(filename_date_claim) > 0:
                    return { **download_url_properties, 'claimed_fresh_at': filename_date_claim[0].strftime('%Y-%m-%d') }
    return {}


def get_fingerprints(file_path: str) -> dict:
    source_file_properties = get_source_file_properties(file_path)
    download_url = get_download_url(file_path)
    return {**source_file_properties, **download_url}


def update_readme(readme_output_path: str, fingerprints: dict):
    template = env.get_template('README.md.jinja')
    with open(readme_output_path, 'w') as readme_file:
        readme_file.write(template.render(**fingerprints))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build badges for a project')
    parser.add_argument('--readme_output', type=str, help='Path to the readme output', default='README.md')
    parser.add_argument('--file_path', type=str, help='Path to the file to be processed', default='data/original/turism_gov_ro/ttmo_approved_list.xls')
    args = parser.parse_args()
    fingerprints = get_fingerprints(args.file_path)
    update_readme(args.readme_output, fingerprints)