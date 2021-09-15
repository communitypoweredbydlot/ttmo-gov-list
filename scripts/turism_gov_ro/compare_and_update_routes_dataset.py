import argparse
import filecmp
import json
import os

from rich.console import Console
from urllib.parse import urlparse

console = Console()

defaults = {
  'dest_file_name': 'ttmo_approved_list',
}


def compare_and_update_dataset(downloaded_file_path, dataset_url, dest_file_name):
    dataset_source_name = urlparse(dataset_url).netloc
    file_extension = os.path.splitext(downloaded_file_path)[1]
    datasource = dataset_source_name.replace(".", "_")
    destination_folder = os.path.join('data/original', datasource)
    dataset_destination_file_path = os.path.join(destination_folder, f'{dest_file_name}{file_extension}')

    if not os.path.isfile(downloaded_file_path):
        console.log(
            f'[red]File [bold blue]{downloaded_file_path}[/bold blue] does not exist.\nCannot update the dataset.')
        exit(1)

    if dataset_destination_file_path and os.path.isfile(dataset_destination_file_path) and filecmp.cmp(
            downloaded_file_path, dataset_destination_file_path, shallow=False):
        os.remove(downloaded_file_path)
        console.log('No update needed.')
    else:
        console.log(f'Updating the dataset.\nMoving downloaded file to {dataset_destination_file_path}.')
        os.makedirs(os.path.dirname(dataset_destination_file_path), exist_ok=True)
        os.replace(downloaded_file_path, dataset_destination_file_path)
        console.log(f'Updating info.json.')
        with open(os.path.join(destination_folder, 'info.json'), 'w') as info_json_file:
            json.dump({'download_url': f'{dataset_url}'}, info_json_file, indent=2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch the approved routes dataset.')
    parser.add_argument('downloaded_file_path', help='The downloaded file path.')
    parser.add_argument('dataset_source_name', help='The name of the source from which the dataset was downloaded.')
    parser.add_argument('--dest-file-name', help='The destination file name.', default=defaults['dest_file_name'])
    args = parser.parse_args()
    compare_and_update_dataset(args.downloaded_file_path, args.dataset_source_name, args.dest_file_name)
