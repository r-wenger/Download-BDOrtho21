import requests
from bs4 import BeautifulSoup
import csv
import os
import py7zr
import argparse
import geopandas as gpd


def fetch_download_links(url, csv_filename):
    response = requests.get(url)
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, 'html.parser')
        with open(csv_filename, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow(['Department', 'Code', 'Link'])
            title = soup.find('h3', id='bd-ortho-dernière-édition')
            if title:
                for sibling in title.find_next_siblings():
                    if sibling.name == 'p' and 'Département' in sibling.get_text():
                        department_info = sibling.get_text(strip=True)
                        department_name = department_info.split(' - ')[1]
                        department_code = department_info.split(' - ')[0].split()[-1]
                    elif sibling.name == 'ul':
                        for link in sibling.find_all('a', href=True):
                            download_link = link['href']
                            writer.writerow([department_name, department_code, download_link])
        print(f"[INFO] Download links have been saved in '{csv_filename}'.")
    else:
        print(f"[INFO] HTTP request error: {response.status_code}")


def download_data_from_csv(csv_path, region):
    links = []
    with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        for row in reader:
            if row['Code'] == region or row['Department'] == region:
                links.append(row['Link'])
    
    region_dir = os.path.join('downloads', region)
    if not os.path.exists(region_dir):
        os.makedirs(region_dir)

    for link in links:
        filename = os.path.join(region_dir, os.path.basename(link))
        print(f"[INFO] Downloading {link} to {filename}")
        response = requests.get(link, stream=True)
        if response.status_code == 200:
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
        else:
            print(f"[INFO] Error downloading {link}")

    print(f"[INFO] Download completed for region {region}")


def extract_and_merge_7z_files(region):
    region_dir = os.path.join('downloads', region)
    if not os.path.exists(region_dir):
        print(f"[INFO] Directory {region_dir} does not exist.")
        return
    
    files = sorted([os.path.join(region_dir, f) for f in os.listdir(region_dir) if f.endswith('.7z')])

    if not files:
        print(f"No .7z files found in {region_dir}")
        return

    with py7zr.SevenZipFile(files[0], mode='r') as archive:
        archive.extractall(path=region_dir)

    print(f"[INFO] Decompression completed for region {region}")


def prepare_data_based_on_shapefiles(input_shapefile, department_geojson, csv_filename):
    """
    Downloads data for departments intersected with the input shapefile.

    :param input_shapefile: Path to the shapefile containing the entities
    :param department_geojson: Path to the GeoJSON of the departments
    :param csv_filename: Path to the CSV file containing the download links
    """
    # Load department GeoJSON data
    departments = gpd.read_file(department_geojson)

    # Load input shapefile data
    input_data = gpd.read_file(input_shapefile)

    # Check projections and reproject to EPSG:2154 if necessary
    if departments.crs != 'EPSG:2154':
        departments = departments.to_crs('EPSG:2154')
    if input_data.crs != 'EPSG:2154':
        input_data = input_data.to_crs('EPSG:2154')

    # Perform spatial intersection with keep_geom_type=False
    intersected_departments = gpd.overlay(departments, input_data, how='intersection', keep_geom_type=False)

    # Extract codes of intersected departments
    department_codes = intersected_departments['code'].unique()

    # Download data for intersected departments
    for code in department_codes:
        download_data_from_csv(csv_filename, code)


def main():
    parser = argparse.ArgumentParser(description="Download and process BD ORTHO data.")
    subparsers = parser.add_subparsers(dest='command')

    parser_fetch = subparsers.add_parser('fetch', help="Fetches download links and saves them in a CSV file.")
    parser_fetch.add_argument('url', type=str, help="URL of the webpage to parse")
    parser_fetch.add_argument('csv_filename', type=str, help="Name of the CSV file to create")

    parser_download = subparsers.add_parser('download', help="Downloads files from the links in the CSV for the specified region.")
    parser_download.add_argument('csv_path', type=str, help="Path to the CSV file")
    parser_download.add_argument('region', type=str, help="Code or name of the region")

    parser_extract = subparsers.add_parser('extract', help="Decompresses the downloaded .7z files for the specified region.")
    parser_extract.add_argument('region', type=str, help="Code or name of the region")

    parser_shapefile = subparsers.add_parser('shapefile', help="Downloads data for departments intersected with a shapefile.")
    parser_shapefile.add_argument('input_shapefile', type=str, help="Path to the shapefile containing the entities")
    parser_shapefile.add_argument('department_geojson', type=str, help="Path to the GeoJSON of the departments")
    parser_shapefile.add_argument('csv_filename', type=str, help="Path to the CSV file containing the download links")

    args = parser.parse_args()

    if args.command == 'fetch':
        fetch_download_links(args.url, args.csv_filename)
    elif args.command == 'download':
        download_data_from_csv(args.csv_path, args.region)
    elif args.command == 'extract':
        extract_and_merge_7z_files(args.region)
    elif args.command == 'shapefile':
        prepare_data_based_on_shapefiles(args.input_shapefile, args.department_geojson, args.csv_filename)


if __name__ == "__main__":
    main()
