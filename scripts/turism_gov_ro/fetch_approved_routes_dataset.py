import aiohttp
import asyncio
import click
import json
import os
import sys

from aiohttp import ClientSession
from bs4 import BeautifulSoup
from datetime import datetime
from urllib.parse import urlparse
from original_file_properties import get_fingerprint_from_buffer, destination_base_folder, \
    find_most_recent_base_folder, get_original_file_info


class FetchException(Exception):
    pass


def compare_and_update_dataset(dataset: dict, dest_file_name: str | None = None):
    file_fingerprint = get_fingerprint_from_buffer(dataset['name'], dataset['content'])
    destination_folder = os.path.join('data', destination_base_folder(file_fingerprint), 'original')

    if dest_file_name is None:
        dest_file_name = dataset['name']

    most_recent_base_folder = find_most_recent_base_folder()
    most_recent_file_info = get_original_file_info(most_recent_base_folder)
    most_recent_file_path = os.path.join(
        most_recent_base_folder,
        'original',
        most_recent_file_info['file_name']
    )

    most_recent_file_content = None
    if most_recent_file_path and os.path.isfile(most_recent_file_path):
        with open(most_recent_file_path, 'rb') as f:
            most_recent_file_content = f.read()

    if most_recent_file_content and dataset['content'] == most_recent_file_content:
        print('We already have the most recent dataset. No update needed.')
    else:
        dataset_destination_file_path = os.path.join(destination_folder, dest_file_name)
        os.makedirs(os.path.dirname(dataset_destination_file_path), exist_ok=True)
        with open(os.path.join(destination_folder, dest_file_name), 'wb') as f:
            f.write(dataset['content'])
        print(f'Dataset saved to {dataset_destination_file_path}.')

        with open(os.path.join(destination_folder, 'info.json'), 'w', encoding='utf-8') as info_json_file:
            info = {
                'download_url': f"{dataset['url']}",
                'file_name': dest_file_name,
                'fetch_date': datetime.today().strftime('%Y-%m-%d %H:%M:%S'),
            }

            if file_fingerprint.get('last_updated_at'):
                info['last_updated_at'] = file_fingerprint['last_updated_at'].strftime('%Y-%m-%d %H:%M:%S')

            if file_fingerprint.get('created_at'):
                info['created_at'] = file_fingerprint['created_at'].strftime('%Y-%m-%d %H:%M:%S')

            if file_fingerprint.get('claimed_fresh_at'):
                info['claimed_fresh_at'] = file_fingerprint['claimed_fresh_at'].strftime('%Y-%m-%d')

            json.dump(info, info_json_file, indent=2)


async def fetch_proxies_fpl(session: ClientSession) -> list[dict]:
    """
    Gets a list of proxies from free-proxy-list.net.
    :return: list of ip,port dicts
    """
    async with session.get('https://free-proxy-list.net/') as response:
        response_text = await response.text()
        soup = BeautifulSoup(response_text, 'html.parser')
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


async def fetch_proxies_geonode(session: ClientSession) -> list[dict]:
    """
    Gets a list of http and https proxies from geonode that were last checked at least 30 minutes ago.
    :return: list of ip,port dicts
    """

    async with session.get('https://proxylist.geonode.com/api/proxy-list?limit=50&page=1&sort_by=lastChecked&sort_type'
                            '=desc&filterLastChecked=30&protocols=http%2Chttps') as response:
        if response.status != 200:
            print(f'Fetching {response.url} failed with status code: {response.status}.')
            return []

        content = await response.json()
        if content.get('data') is None:
            print(f'Response from {response.url} doest not have the expected format.')
            return []

        return [{'ip': proxy['ip'], 'port': proxy['port']} for proxy in content['data']]


def get_the_download_link(page_text: str, link_text_prefix: str) -> str:
    soup = BeautifulSoup(page_text, 'html.parser')
    dataset_download_element = soup.find(lambda t: t.name == 'a' and t.text.startswith(link_text_prefix))
    return dataset_download_element['href'] if dataset_download_element else None


async def fetch_dataset(session: ClientSession, url: str, link_text_prefix: str,
                        user_agent: str, proxy: str = None) -> dict:
    headers = {'User-Agent': user_agent}
    async with session.get(url, allow_redirects=True, headers=headers, proxy=proxy) as page:
        if page.status != 200:
            raise Exception(f'Fetching {url} failed with status code: {page.status}.')

        page_text = await page.text()

        dataset_url = get_the_download_link(page_text, link_text_prefix)
        if dataset_url is None:
            raise Exception('The dataset download url could not be found.')

        dataset_url_obj = urlparse(dataset_url)
        dataset_name = os.path.basename(dataset_url_obj.path)

        async with session.get(dataset_url, allow_redirects=True, headers=headers, proxy=proxy) as dataset:
            if dataset.status != 200:
                raise FetchException(
                    f'The dataset download request failed with status code {dataset.status}.')

            content = await dataset.read()
            return {'name': dataset_name, 'url': dataset_url, 'content': content}


async def fetch_dataset_insistently(url: str, link_text_prefix: str, user_agent: str) -> dict | None:
    """
    Fetch the approved routes dataset.
    """
    async with aiohttp.ClientSession() as session:
        proxies_geonode = await fetch_proxies_geonode(session)
        proxies_fpl = await fetch_proxies_fpl(session)
        print(f'{len(proxies_geonode)} geonode proxies found.')
        print(f'{len(proxies_fpl)} free-proxy-list.net proxies found.')
        proxies = proxies_geonode + proxies_fpl
        tasks = []
        for i, proxy in enumerate(proxies):
            req_proxy = f'http://{proxy["ip"]}:{proxy["port"]}'
            tasks.append(asyncio.ensure_future(fetch_dataset(session, url, link_text_prefix, user_agent, req_proxy)))

        while tasks:
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)

            for dt in done:
                if dt.exception() is None:
                    for pt in pending:
                        pt.cancel()
                    await asyncio.wait(pending)
                    return dt.result()
                else:
                    print(f'Fetching {url} failed with exception: {dt.exception()}.')
            tasks = pending

        return None


async def fetch_and_save_dataset(**args):
    dataset = await fetch_dataset_insistently(**args)

    if dataset:
        compare_and_update_dataset(dataset)
    else:
        print(f'Dataset could not be fetched.')


@click.command()
@click.option('--url', '-u',
              default='http://turism.gov.ro/web/autorizare-turism/',
              help='The url of the page with the approved routes dataset download link.')
@click.option('--link-text-prefix', '-l',
              default='Trasee turistice montane omologate',
              help='The text prefix of the dataset download link.')
@click.option('--user-agent', '-a',
              default='Mozilla/5.0 (Macintosh; Intel Mac OS X 10_14_3) AppleWebKit/537.36 (KHTML, '
                      'like Gecko) Chrome/72.0.3626.121 Safari/537.36',
              help='The user agent to use when fetching the dataset.')
def main(**args):
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    asyncio.run(fetch_and_save_dataset(**args))


if __name__ == '__main__':
    main(auto_envvar_prefix='TTMO_GOV_LIST')
