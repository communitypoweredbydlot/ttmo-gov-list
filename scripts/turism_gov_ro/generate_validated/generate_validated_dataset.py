import click
import os
import pandas as pd

from unidecode import unidecode


@click.command()
@click.option('--input-path',
              type=click.Path(exists=True, dir_okay=False, readable=True),
              default=None)
@click.option('--output-path',
              type=click.Path(exists=False, dir_okay=False, readable=True),
              default=None)
def generate_validated_dataset(input_path, output_path):
    # When the values are none find the most recent dataset and generate in the corresponding path
    ver_df = pd.read_csv(input_path, header=0)
    validated_dataset = ver_df.loc[ver_df['verified']].drop(labels=['verified', 'source', 'commentary'], axis=1)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    validated_dataset.to_csv(output_path, index=False)

    validated_dataset_ascii = validated_dataset.applymap(lambda v: unidecode(str(v)))
    (root, ext) = os.path.splitext(output_path)
    validated_dataset_ascii.to_csv(f'{root}_ascii{ext}', index=False)


if __name__ == '__main__':
    generate_validated_dataset()
