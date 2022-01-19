import click
import os
import requests

from bs4 import BeautifulSoup
from urllib.parse import urlparse

defaults = {
    'url': os.getenv('URL', 'http://turism.gov.ro/web/autorizare-turism/'),
    'link_text_prefix': os.getenv('LINK_TEXT_PREFIX', 'Trasee turistice montane omologate'),
    'user_agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, '
                                          'like Gecko) Chrome/72.0.3626.121 Safari/537.36'),
}


class FetchException(Exception):
    pass


def get_proxies() -> list[dict]:
    response = requests.get('https://free-proxy-list.net/')
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', attrs={'class': 'table table-striped table-bordered'})

    proxies = []
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) > 0:
            proxies.append({
                'ip': cols[0].text.strip(),
                'port': cols[1].text.strip()
            })
    return proxies


def get_proxies_geonode() -> list[dict]:
    response = requests.get('https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type=desc&filterLastChecked=30&protocols=http%2Chttps')
    # go through the response data field
    # and extract the ip and port
    proxies = []

    if response.status_code != 200:
        print(f'Fetching {response.url} failed with status code: {response.status_code}.')
        return []

    for proxy in response.json()['data']:
        proxies.append({
            'ip': proxy['ip'],
            'port': proxy['port']
        })
    return proxies


def get_the_download_link(page_text: str, link_text_prefix: str) -> str:
    soup = BeautifulSoup(page_text, 'html.parser')
    dataset_download_element = soup.find(lambda t: t.name == 'a' and t.text.startswith(link_text_prefix))
    return dataset_download_element['href'] if dataset_download_element else None


def fetch_dataset(url: str, link_text_prefix: str, user_agent: str, proxy: dict = None) -> dict:
    headers = {'User-Agent': user_agent}
    page = requests.get(url, allow_redirects=True, headers=headers, proxies=proxy)

    if page.status_code == 200:
        print('Link page fetched.')
    else:
        raise Exception(f'Fetching {url} failed with status code: {page.status_code}.')

    dataset_url = get_the_download_link(page.text, link_text_prefix)
    if dataset_url is None:
        raise Exception('The dataset download url could not be found.')
    else:
        print(f'Dataset download url found to be {dataset_url}.')

    # Get the original dataset file name
    dataset_url_obj = urlparse(dataset_url)
    dataset_name = os.path.basename(dataset_url_obj.path)

    download_request_result = requests.get(dataset_url, allow_redirects=True, headers=headers, proxies=proxy)
    if download_request_result.status_code != 200:
        raise FetchException(
            f'The dataset download request failed with status code {download_request_result.status_code}.')

    with open(dataset_name, 'wb') as dataset_file:
        dataset_file.write(download_request_result.content)

    if os.path.exists(dataset_name):
        print(f'The dataset was downloaded to {dataset_name}.')
    else:
        raise FetchException(f'[red]The dataset file {dataset_name} was not found. Fetch failed.')

    return {'downloaded_file_path': dataset_name, 'dataset_url': dataset_url}


def fetch_dataset_insistently(url: str, link_text_prefix: str, user_agent: str) -> dict:
    """Fetch the approved routes dataset."""
    proxies = get_proxies_geonode() + get_proxies()
    print(f'{len(proxies)} proxies found.')
    for i, proxy in enumerate(proxies):
        print(f'Fetching dataset, try with proxy [{i + 1}] {proxy}.')
        req_proxy = {
            'http': f'http://{proxy["ip"]}:{proxy["port"]}'
        }
        try:
            download_info = fetch_dataset(url, link_text_prefix, user_agent, req_proxy)
            return download_info
        except FetchException as e:
            raise
        except Exception as e:
            print(f'Fetching dataset try {proxy} failed with error: {e}')
            pass


@click.command()
@click.option('--url', '-u',
              default=defaults['url'],
              help='The url of the page with the approved routes dataset download link.')
@click.option('--link-text-prefix', '-l',
              default=defaults['link_text_prefix'],
              help='The text prefix of the dataset download link.')
@click.option('--user-agent', '-a',
              default=defaults['user_agent'],
              help='The user agent to use when fetching the dataset.')
def main(**args):
    fetch_dataset_insistently(**args)


if __name__ == '__main__':
    main()
