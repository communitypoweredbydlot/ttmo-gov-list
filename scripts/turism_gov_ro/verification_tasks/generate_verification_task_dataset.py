import click
import os
import pandas as pd

from dataclasses import dataclass
from jinja2 import Environment, FileSystemLoader


@dataclass
class VerificationTask:
    nr: int
    certificate_number: int
    registration_date: str
    name: str
    administrator: str
    location: str
    county: str
    verified: bool
    source: int
    commentary: str


@click.command()
@click.option('--ttmo-gov-list-path',
              default='data/clean/turism_gov_ro/uniform/ttmo_gov_list.csv',
              type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--ttmo-gov-list-old-path',
              default='data/clean/turism_gov_ro/uniform/ttmo_gov_list.old.csv',
              type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option('--output-path',
              default='data/clean/turism_gov_ro/verification/ttmo_gov_list.csv',
              type=click.Path(exists=False, dir_okay=False, readable=True, writable=True))
@click.option('--issue-md-output-path', default='issue.md')
def generate_verification_tasks(ttmo_gov_list_path, ttmo_gov_list_old_path, output_path, issue_md_output_path):
    undf = pd.read_csv(ttmo_gov_list_path)

    if os.path.isfile(output_path):
        uodf = pd.read_csv(ttmo_gov_list_old_path)

        mudf = undf.merge(uodf, how='outer', on='certificate_number', suffixes=('_new', '_old'), indicator='merge')
        mudf['nr_new'] = mudf['nr_new'].astype('Int64')
        mudf['nr_old'] = mudf['nr_old'].astype('Int64')

        vtdf = pd.read_csv('data/clean/turism_gov_ro/verification/ttmo_gov_list.csv')

        nvts = []
        removed = []
        new = []
        modified = 0
        for row in mudf.itertuples():
            if row.merge == 'both':
                v_tasks = vtdf[vtdf['certificate_number'] == row.certificate_number]

                for v_task in v_tasks.itertuples():
                    changed = False
                    nr = v_task.nr
                    if row.nr_old != row.nr_new:
                        changed = True
                        nr = row.nr_new

                    registration_date = v_task.registration_date
                    if row.registration_date_old != row.registration_date_new:
                        changed = True
                        registration_date = row.registration_date_new

                    name = v_task.name
                    if row.name_old != row.name_new:
                        changed = True
                        name = row.name_new

                    administrator = v_task.administrator
                    if row.administrator_old != row.administrator_new:
                        changed = True
                        administrator = row.administrator_new

                    location = v_task.location
                    if row.location_old != row.location_new:
                        changed = True
                        location = row.location_new

                    county = v_task.county
                    if row.county_old != row.county_new:
                        changed = True
                        county = row.county_new

                    verified = v_task.verified and not changed

                    if changed:
                        modified += 1

                    nvts.append(VerificationTask(
                        nr=nr,
                        certificate_number=row.certificate_number,
                        registration_date=registration_date,
                        name=name,
                        administrator=administrator,
                        location=location,
                        county=county,
                        verified=verified,
                        source=row.certificate_number,
                        commentary=v_task.commentary
                    ))

            elif row.merge == 'left_only':
                new_task = VerificationTask(
                    nr=row.nr_new,
                    certificate_number=row.certificate_number,
                    registration_date=row.registration_date_new,
                    name=row.name_new,
                    administrator=row.administrator_new,
                    location=row.location_new,
                    county=row.county_new,
                    verified=False,
                    source=row.certificate_number,
                    commentary=''
                )

                new.append(undf[undf['certificate_number'] == row.certificate_number].iloc[0])
                nvts.append(new_task)
            else:
                removed.append(v_task)

        nvtdf = pd.DataFrame(nvts)
        write_verification_file(nvtdf, output_path)
        write_issue_markdown(pd.DataFrame(new), pd.DataFrame(removed), modified, issue_md_output_path)
    else:
        undf['verified'] = 'False'
        undf['source'] = undf['certificate_number']
        undf['commentary'] = None
        write_verification_file(undf, output_path)


def write_issue_markdown(ndf, rdf, n_modif, issue_md_output_path):
    template_env = Environment(loader=FileSystemLoader('templates'))
    template = template_env.get_template('NEW_VERIFICATION_TASKS_ISSUE_TEMPLATE.jinja.md')
    template_vars = {
        'modified_rows_count': n_modif
    }
    if not ndf.empty:
        template_vars['new_rows_table'] = ndf.to_markdown(index=False)
    
    if not rdf.empty:
        template_vars['removed_rows_table'] = rdf.to_markdown(index=False)

    if n_modif > 0 or not ndf.empty or not rdf.empty:
        with open(issue_md_output_path, 'w', encoding='utf-8') as issue_file:
            issue_file.write(template.render(**template_vars))


def write_verification_file(df, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.sort_values(by='certificate_number', kind='stable').to_csv(output_path, index=False)


if __name__ == '__main__':
    generate_verification_tasks()
