import click
import os
import pandas as pd

from io import StringIO
from jinja2 import Environment, FileSystemLoader
from pydriller import Repository


@click.command()
@click.option('--commit-hash')
@click.option('--repo-path', default='.')
@click.option('--ttmo-gov-list-path', default='data/clean/turism_gov_ro/uniform/ttmo_gov_list.csv')
@click.option('--output-path', default='data/clean/turism_gov_ro/verification/ttmo_gov_list.csv')
@click.option('--issue-md-output-path', default='issue.md')
@click.option('--column-names', default="nr,certificate_number,registration_date,name,administrator,location,county")
def generate_verification_tasks(commit_hash, repo_path, ttmo_gov_list_path, output_path, issue_md_output_path, column_names):
    if not commit_hash:
        click.echo('No hash provided. Using the ttmo-gov-list-path as input.')
        df = pd.read_csv(ttmo_gov_list_path)
        add_new_verification_tasks(df, output_path)
        return

    repo = Repository(repo_path, single=commit_hash)
    commits = list(repo.traverse_commits())
    if len(commits) != 1:
        raise Exception('Commit hash not found in repository')

    modified_files = list(filter(lambda f: os.path.samefile(ttmo_gov_list_path, f.new_path), commits[0].modified_files))
    if len(modified_files) != 1:
        raise Exception('TTMO gov list file not modified in this commit')

    modified_file = modified_files[0]
    added_df = diff_to_df(modified_file.diff_parsed['added'], column_names)
    deleted_df = diff_to_df(modified_file.diff_parsed['deleted'], column_names)

    merge_df = added_df.merge(deleted_df, how='outer', on='certificate_number', suffixes=('_new', '_old'), indicator=True)
    merge_df['nr_new'] = merge_df['nr_new'].astype('Int64')
    merge_df['nr_old'] = merge_df['nr_old'].astype('Int64')

    new_df = merge_df[merge_df['_merge'] == 'left_only'].filter(regex='(certificate_number|_new)', axis=1).rename(columns=lambda x: x.removesuffix('_new'))
    if not new_df.empty:
        add_new_verification_tasks(new_df, output_path)

    deleted_df = merge_df[merge_df['_merge'] == 'right_only'].filter(like='_old', axis=1).rename(columns=lambda x: x.removesuffix('_old'))
    modified_df = merge_df[merge_df['_merge'] == 'both'].drop('_merge', axis=1)
    if not (deleted_df.empty and modified_df.empty):
        write_issue_markdown(modified_df, deleted_df, issue_md_output_path)


def write_issue_markdown(modified_df, deleted_df, issue_md_output_path):
    template_env = Environment(loader=FileSystemLoader('templates'))
    template = template_env.get_template('NEW_VERIFICATION_TASKS_ISSUE_TEMPLATE.md.jinja')
    template_vars = {}
    if not modified_df.empty:
        template_vars['modified_rows_table'] = modified_df.to_markdown(index=False)
    
    if not deleted_df.empty:
        template_vars['deleted_rows_table'] = deleted_df.to_markdown(index=False)

    with open(issue_md_output_path, 'w', encoding='utf-8') as issue_file:
        issue_file.write(template.render(**template_vars))


def add_new_verification_tasks(df, output_path):
    df['verified'] = 'False'
    df['source'] = df['certificate_number']
    df['commentary'] = None
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    if os.path.isfile(output_path):
        # We don't want to insert duplicates or overwrite if any are there
        current_df = pd.read_csv(output_path)
        if not current_df['certificate_number'].isin(df['certificate_number']).any():
            df.to_csv(output_path, index=False, mode='a', header=False)
        else:
            click.echo('Rows already in dataset')
    else:
        df.to_csv(output_path, index=False)


def diff_to_df(diff, header_names: str):
    rows = list(map(lambda p: p[1], diff))
    if len(rows) == 0:
        return pd.DataFrame(columns=header_names.split(','))

    has_header = None
    if rows[0] == header_names:
        has_header = 0

    with StringIO('\n'.join(rows)) as f:
        return pd.read_csv(f, header=has_header, names=header_names.split(','))


if __name__ == '__main__':
    generate_verification_tasks()
