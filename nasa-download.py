import os
import re
import string
import time
import click
import hashlib
import requests
from pathlib import Path
from tqdm import tqdm

CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])


data_path = {
    # 'MYD17A2': ['h27v04', 'h27v05', 'h28v05'],
    'MCD12Q1': ['h27v04', 'h27v05', 'h28v05'],
    # 'MCD12Q2': ['h27v04', 'h27v05', 'h28v05'],
    # 'MOD17A3': ['h27v04', 'h27v05', 'h28v05'],
    # 'MCD15A2': ['h27v04', 'h27v05', 'h28v05'],
    # 'MOD44B': ['h27v04', 'h27v05', 'h28v05'],
    # 'MOD13Q1': ['h27v04', 'h27v05', 'h28v05'],
    # 'MOD17A2HGF': ['h27v04', 'h27v05', 'h28v05'],
}

year_limit = 2010

root_by_types = {
    'MOD':	'https://e4ftl01.cr.usgs.gov/MOLT/',
    'MYD':	'https://e4ftl01.cr.usgs.gov/MOLA/',
    'MCD':	'https://e4ftl01.cr.usgs.gov/MOTA/',
    'MODIS':	'https://e4ftl01.cr.usgs.gov/MOLT/',
}

URLS = [
    # 'http://ipv4.download.thinkbroadband.com/512MB.zip',
    'https://e4ftl01.cr.usgs.gov/MOLT/MOD13Q1.061/2023.06.10/MOD13Q1.A2023161.h30v11.061.2023177233745.hdf',
]
"""List: Contains urls of files which need to be downloaded.
Make sure that you add a hash in the same position in ``HASHES`` so that the
integrity of the file can be verified. The hash has to be a lowercase sha265.
The has can be computed in Powershell with ``Get-FileHash <file>``. Notice
that Powershell returns uppercase letters and Python lowercase."""

HASHES = []
"""List: Contains sha265 hashes calculated for the files in ``URLS``."""

DOWNLOAD_FOLDER = Path('./downloads')
if not Path.exists(DOWNLOAD_FOLDER):
    os.mkdir(DOWNLOAD_FOLDER)
"""pathlib.Path: Points to the target directory of downloads."""

username='kkuk628'
password='C%ChP4K8n$*LEeY'

class SessionWithHeaderRedirection(requests.Session):
    AUTH_HOST = 'urs.earthdata.nasa.gov'

    def __init__(self, username, password):
        super().__init__()
        self.auth = (username, password)

    # Overrides from the library to keep headers when redirected to or from the NASA auth host.
    def rebuild_auth(self, prepared_request, response):
        headers = prepared_request.headers
        url = prepared_request.url
        if 'Authorization' in headers:
            original_parsed = requests.utils.urlparse(response.request.url)
            redirect_parsed = requests.utils.urlparse(url)
            if (original_parsed.hostname != redirect_parsed.hostname) and \
               redirect_parsed.hostname != self.AUTH_HOST and \
               original_parsed.hostname != self.AUTH_HOST:
                del headers['Authorization']
        return

session = SessionWithHeaderRedirection(username, password)

def downloader(url: string, resume_byte_pos: int = None):
    """Download url in ``URLS[position]`` to disk with possible resumption.
    Parameters
    ----------
    position: int
        Position of url.
    resume_byte_pos: int
        Position of byte from where to resume the download
    """
    # Get size of file
    r = session.head(url)
    file_size = int(r.headers.get('content-length', 0))

    # Append information to resume download at specific byte position
    # to header
    resume_header = ({'Range': f'bytes={resume_byte_pos}-'}
                     if resume_byte_pos else None)

    # Establish connection
    r = session.get(url, stream=True, headers=resume_header)

    # Set configuration
    block_size = 1024
    initial_pos = resume_byte_pos if resume_byte_pos else 0
    mode = 'ab' if resume_byte_pos else 'wb'
    file = DOWNLOAD_FOLDER / url.split('/')[-1]

    with open(file, mode) as f:
        with tqdm(total=file_size, unit='B',
                  unit_scale=True, unit_divisor=1024,
                  desc=file.name, initial=initial_pos,
                  ascii=True, miniters=1) as pbar:
            for chunk in r.iter_content(32 * block_size):
                f.write(chunk)
                pbar.update(len(chunk))


def download_file(url: string) -> None:
    """Execute the correct download operation.
    Depending on the size of the file online and offline, resume the
    download if the file offline is smaller than online.
    Parameters
    ----------
    position: int
        Position of url.
    """
    # Establish connection to header of file
    r = session.head(url)

    # Get filesize of online and offline file
    file_size_online = int(r.headers.get('content-length', 0))
    file = DOWNLOAD_FOLDER / url.split('/')[-1]

    if file.exists():
        file_size_offline = file.stat().st_size
    else:
        click.echo(f'Start downloading file {file}.')
        file_size_offline = 0

    while file_size_online > file_size_offline:
        try:
            if file.exists(): 
                click.echo(f'File {file} is incomplete. Resume download.')                
            downloader(url, file_size_offline)
            file_size_offline = file.stat().st_size
        except Exception as ex:
            click.echo(f'Error in downloading {url}.')
            click.echo(ex)
            time.sleep(2)

    click.echo(f'File {file} is complete.')


def download_dataset(dataset_name: string, root_url: string, path):
    try:
        # submit the request using the session
        response = session.get(root_url)
        print(response.status_code)

        # raise an exception in case of http errors
        response.raise_for_status()
        pattern = f'<a +href=[\\"\']+(.+)[\\"\']+>{dataset_name}.*</a>'
        m = re.search(pattern, response.content.decode())
        if m == None:
            print(response.content)
        else:
            second_url = root_url + m.group(1)
            response.close()
            response = session.get(second_url)
            response.raise_for_status()
            pattern2 = re.compile('<a +href=[\\"\']+(.+)[\\"\']+>(20\\d+)\\.\\d+.\\d+/?</a>')
            response.close()
            for (url_part, year) in re.findall(pattern2, response.content.decode()):
                if int(year) < year_limit:
                    continue
                third_url = second_url + url_part
                response = session.get(third_url)
                response.raise_for_status()
                for p in path:
                    pattern3 = f'<a +href=[\\"\']+(.+)[\\"\']+>{dataset_name}\\w*\\.\\w+\\.{p}\\.\\w+\\.\\w+\\.hdf</a>'
                    mm = re.search(pattern3, response.content.decode())
                    if mm ==None:
                        print(response.content)
                    else:
                        download_url = third_url + mm.group(1)
                        download_file(download_url)
                        download_file(download_url + '.xml')

    except requests.exceptions.HTTPError as e:
        # handle any errors here
        print(e)

@click.group(context_settings=CONTEXT_SETTINGS, chain=True)
def cli():
    """Program for downloading and validating files.
    
    It is possible to run both operations consecutively with
    
    .. code-block:: shell
    
        $ python python-downloader.py download validate
    To download a file, add the link to ``URLS`` and its hash to ``HASHES`` if
    you want to validate downloaded files.
    """
    pass


@cli.command()
def download():
    """Download files specified in ``URLS``."""
    click.echo('\n### Start downloading required files.\n')
    for dset in data_path:
        d = dset[0:3]
        download_dataset(dset, root_by_types[d], data_path[dset])
    click.echo('\n### End\n')


@cli.command()
def validate():
    """Validate downloads with hashes in ``HASHES``."""
    click.echo('### Start validating required files.\n')
    for position in range(len(URLS)):
        validate_file(position)
    click.echo('\n### End\n')

def validate_file(position: int) -> None:
    """Validate a given file with its hash.
    The downloaded file is hashed and compared to a pre-registered
    has value to validate the download procedure.
    Parameters
    ----------
    position: int
        Position of url and hash.
    """
    file = DOWNLOAD_FOLDER / URLS[position].split('/')[-1]
    try:
        hash = HASHES[position]
    except IndexError:
        click.echo(f'File {file.name} has no hash.')
        return 0

    sha = hashlib.sha256()
    with open(file, 'rb') as f:
        while True:
            chunk = f.read(1000 * 1000)  # 1MB so that memory is not exhausted
            if not chunk:
                break
            sha.update(chunk)
    try:
        assert sha.hexdigest() == hash
    except AssertionError:
        file = URLS[position].split("/")[-1]
        click.echo(f'File {file} is corrupt. '
                   'Delete it manually and restart the program.')
    else:
        click.echo(f'File {file} is validated.')


if __name__ == '__main__':
    download()