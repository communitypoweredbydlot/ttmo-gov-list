import argparse

from jinja2 import Environment, FileSystemLoader
from original_file_properties import get_fingerprints


env = Environment(
    loader=FileSystemLoader("templates")
)


def update_readme(readme_output_path: str, fingerprints: dict):
    template = env.get_template('README.md.jinja')
    with open(readme_output_path, 'w') as readme_file:
        readme_file.write(template.render(**fingerprints))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Build badges for a project')
    parser.add_argument('--readme_output', type=str, help='Path to the readme output', default='README.md')
    parser.add_argument('--file_path', type=str, help='Path to the file to be processed')
    args = parser.parse_args()
    fingerprints = get_fingerprints(args.file_path)
    update_readme(args.readme_output, fingerprints)