import click
import filecmp
import json
import os

from urllib.parse import urlparse


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
        raise Exception(f'File {downloaded_file_path} does not exist.\nCannot update the dataset.')

    if dataset_destination_file_path and os.path.isfile(dataset_destination_file_path) and filecmp.cmp(
            downloaded_file_path, dataset_destination_file_path, shallow=False):
        os.remove(downloaded_file_path)
        print('No update needed.')
    else:
        print(f'Updating the dataset.\nMoving downloaded file to {dataset_destination_file_path}.')
        os.makedirs(os.path.dirname(dataset_destination_file_path), exist_ok=True)
        os.replace(downloaded_file_path, dataset_destination_file_path)
        print(f'Updating info.json.')
        with open(os.path.join(destination_folder, 'info.json'), 'w') as info_json_file:
            json.dump({'download_url': f'{dataset_url}'}, info_json_file, indent=2)


@click.command()
@click.argument('downloaded_file_path', type=click.Path(exists=True))
@click.argument('dataset_url', type=click.STRING)
@click.option('--dest-file-name', default=defaults['dest_file_name'], help='Name of the destination file.')
def main(**args):
    compare_and_update_dataset(**args)


if __name__ == '__main__':
    main()
