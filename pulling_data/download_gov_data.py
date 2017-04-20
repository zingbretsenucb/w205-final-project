import requests
import re
# from postgres.PostgreSQL import PostgreSQL
import json
import pandas as pd
import os
from collections import defaultdict
from collections import namedtuple


# URL to pull all Pittsburgh datasets
search_url = 'https://catalog.data.gov/api/3/action/package_search?q=Allegheny%20County%20/%20City%20of%20Pittsburgh%20/%20Western%20PA%20Regional%20Data%20Center'
# name = ''
# arrest_url = 'https://data.wprdc.org/datastore/dump/e03a89dd-134a-4ee8-a2bd-62c40aeebc6f'

# In case we need to rename extensions
EXTENSIONS = {'CSV': 'csv', 'HTML': 'html'}

# Formats to download
download_formats = ('CSV',)

# Special tuple type to store rows of our metadata
FetchableData = namedtuple("data", ['name', 'metadata_modified', 'file_format', 'url', 'file_id', 'package_id', 'revision_id', 'resource_num'])

def fetch_metadata(url = search_url, rows = 1000):
    """Fetch daily or summary stats for a year in Pittsburgh"""
    url += '&rows={}'.format(rows)
    r = requests.post(url)
    my_json = json.loads(r.text)
    return my_json


def extract_metadata(md):
    assert md['success'] is True
    results = md['result']['results']
    output = []
    for result in results:
        resources = result['resources']
        parsed = {}
        parsed['name'] = result['name']
        parsed['metadata_modified'] = result['metadata_modified']
        parsed['resources'] = []
        for res in resources:
            parsed['resources'].append({
                'format': res['format'],
                'url': res['url'],
                'id': res['id'],
                'package_id': res['package_id'],
                'revision_id': res['revision_id'],
                })
        output.append(parsed)
    return output

def flatten_extracted_data(extracted):
    output = []
    for result in extracted:
        for i, resource in enumerate(result['resources']):
            row = FetchableData(
                name = result['name'],
                metadata_modified = result['metadata_modified'],
                file_format = resource['format'],
                url = resource['url'],
                file_id = resource['id'],
                package_id = resource['package_id'],
                revision_id = resource['revision_id'],
                resource_num = str(i),
                )
            output.append(row)
    return output


def needs_updating(flat_row):
    """Query the database to see if we should download new data"""
    # TODO: Hook up to database
    # Probably want to use id and and metadata_modified to check
    # database? Or maybe revision_id?
    return True


def fetch_file_by_url(url, basedir = "/tmp/pittsburgh", fname = None):
    r = requests.get(url)
    if fname is None:
        fname = os.path.basename(url)
    fpath = os.path.join(basedir, fname)
    with open (fpath, 'w') as f:
        try:
            f.write(r.text)
            print('Fetched: {}'.format(fname))
        except UnicodeEncodeError as e:
            print(e)
            print("Python 2 sucks at unicode")


def fetch_files_by_type(flat_results, data_formats = ("CSV", "KML"), basedir = '/data/pb_files'):
    urls = defaultdict(list)
    try:
        os.mkdir(basedir)
    except OSError as e:
        pass

    for result in flat_results:
        f_format  = result.file_format
        num       = result.resource_num
        url       = result.url
        name      = result.name

        try:
            ext = EXTENSIONS[f_format]
        except KeyError as e:
            ext = 'txt'

        subdir = os.path.join(basedir, f_format)

        try:
            os.mkdir(subdir)
        except OSError as e:
            pass

        # Only download if format is of specified type
        # or if no types specified
        good_format = data_formats is None or f_format in data_formats
        fname = '{}_{}.{}'.format(name, num, ext)

        if good_format and needs_updating(result):
            fetch_file_by_url(url, basedir = subdir, fname = fname)
        else:
            print("skipping {}".format(fname))


def update_file_in_db(basedir, fname):
    """Use new file to update database"""
    #TODO actually update DB
    # Pandas is good about inferring types
    f = pd.read_csv(os.path.join(basedir, fname), 'r')
    print(f.head())
    


def fetch_all_urls(urls, basedir = "/tmp/pittsburgh", fname = None):
    for url in urls:
        try:
            fetch_file_by_url(url, basedir, fname)
        except UnicodeEncodeError as e:
            print(e)
            print("Py2 problem, probably")

        update_file_in_db(basedir, fname)
    
    
def main():
    metadata = fetch_metadata()
    parsed = extract_metadata(metadata)
    flat = flatten_extracted_data(parsed)
    fetch_files_by_type(flat, download_formats, basedir = '/tmp/pb_files')

# with PostgreSQL(database = 'pittsburgh') as psql:
#     types = TYPES
#     psql.create_table(table = 'weather', cols = cols, types = types)

    # for year in years:
    #     print(year)
    #     rows = parse_year_table(fetch_year_of_weather(year), year)
    #     with PostgreSQL(table = 'weather', database = 'pittsburgh') as psql:
    #         psql.add_rows(rows, types = types, cols = cols)


if __name__ == '__main__':
    main()