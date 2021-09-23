import click
import os
import pandas as pd


@click.command()
@click.option('--input-path', default='data/clean/turism_gov_ro/verification/ttmo_gov_list.csv')
@click.option('--output-path', default='data/clean/turism_gov_ro/ttmo_gov_list.csv')
def generate_validated_dataset(input_path, output_path):
    ver_df = pd.read_csv(input_path, header=0)
    validated_dataset = ver_df.loc[ver_df['verified']].drop(labels=['verified', 'source', 'commentary'], axis=1)
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    validated_dataset.to_csv(output_path, index=False)


if __name__ == '__main__':
    generate_validated_dataset()
