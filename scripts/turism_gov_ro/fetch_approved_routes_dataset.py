import argparse
import os
import requests

from bs4 import BeautifulSoup
from rich.console import Console
from urllib.parse import urlparse


defaults = {
    'url': os.getenv('URL', 'http://turism.gov.ro/web/autorizare-turism/'),
    'link_text_prefix': os.getenv('LINK_TEXT_PREFIX', 'Trasee turistice montane omologate'),
    'user_agent': os.getenv('USER_AGENT', 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, '
                                          'like Gecko) Chrome/72.0.3626.121 Safari/537.36'), 
}

console = Console()


def get_proxies() -> dict:
    response = requests.get('https://scrapingant.com/free-proxies/')
    soup = BeautifulSoup(response.text, 'html.parser')
    table = soup.find('table', attrs={'class': 'proxies-table'})

    proxies = []
    for row in table.find_all('tr'):
        cols = row.find_all('td')
        if len(cols) > 0 and cols[2].text.strip().lower() == 'http':
            proxies.append({
                'ip': cols[0].text.strip(),
                'port': cols[1].text.strip(),
                'protocol': cols[2].text.strip().lower()
            })
    return proxies



def get_the_download_link(page_text: str, link_text_prefix: str) -> str:
      soup = BeautifulSoup(page_text, 'html.parser')

      dataset_download_element = soup.find(lambda t: t.name == 'a' and t.text.startswith(link_text_prefix))

      if dataset_download_element:
          return dataset_download_element['href']

      return None


def fetch_dataset(url: str, link_text_prefix: str, user_agent: str, proxy: dict = None) -> dict:
    headers = {'User-Agent': user_agent}

    with console.status('[dark green]Fetching link page'):
        page = requests.get(url, allow_redirects=True, headers=headers, proxies=proxy)

        if page.status_code == 200:
            console.log('Link page fetched.')
        else:
            console.log(f'[red]Fetching link page failed with status code: {page.status_code}.')
            return None

        dataset_url = get_the_download_link(page.text, link_text_prefix)
        if dataset_url is None:
            console.log('[red]The dataset download url could not be found.')
            return None
        else:
            console.log(f'Dataset download url found to be {dataset_url}.')

        # Get the original dataset file name
        dataset_url_obj = urlparse(dataset_url)
        dataset_name = os.path.basename(dataset_url_obj.path)

    with console.status('[dark green]Downloading dataset...'):
        download_request_result = requests.get(dataset_url, allow_redirects=True, headers=headers, proxies=proxy)
        if download_request_result.status_code != 200:
            console.log(
                f'The dataset download request failed with status code {download_request_result.status_code}.')
            return None
        with open(dataset_name, 'wb') as dataset_file:
            dataset_file.write(download_request_result.content)

        if os.path.exists(dataset_name):
            console.log(f'The dataset was downloaded to [green]{dataset_name}[/green].')
        else:
            console.log(f'[red]The dataset file [green]{dataset_name}[/green] was not found. Fetch failed.')
            return None
        return { 'downloaded_file_path': dataset_name , 'dataset_url': dataset_url }


def fetch_dataset_insistently(url: str, link_text_prefix: str, user_agent: str) -> dict:
    proxies = get_proxies()
    console.log(f'[dark green]{len(proxies)} proxies found.')
    for i,  proxy in enumerate(proxies):
        console.log(f'[dark green]Fetching dataset, try with proxy [{i+1}] {proxy}.')
        req_proxy = {
            proxy['protocol']: f'{proxy["protocol"]}://{proxy["ip"]}:{proxy["port"]}'
        }
        try:
            download_info = fetch_dataset(url, link_text_prefix, user_agent, req_proxy)
            if download_info is not None:
                return download_info
        except Exception as e:
            console.log(f'[red]Fetching dataset try {proxy} failed with error: {e}.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Fetch the approved routes dataset.')
    parser.add_argument('--url',
                        help='url of the page containing the approved routes dataset',
                        default=defaults['url'])
    parser.add_argument('--link-text-prefix',
                        help='string with which the text of the link starts',
                        default=defaults['link_text_prefix'])
    parser.add_argument('--user-agent',
                        help='user agent used for the requests',
                        default=defaults['user_agent'])
    args = parser.parse_args()
    fetch_dataset_insistently(args.url, args.link_text_prefix, args.user_agent)
