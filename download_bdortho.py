import requests
from bs4 import BeautifulSoup
import csv
import os
import py7zr
import argparse
import geopandas as gpd
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def fetch_download_links(url, csv_filename):
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise HTTPError for bad responses
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
        logging.info(f"Download links have been saved in '{csv_filename}'.")
    except requests.exceptions.RequestException as e:
        logging.error(f"HTTP request error: {e}")


def download_data_from_csv(csv_path, region):
    links = []
    try:
        with open(csv_path, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                if row['Code'] == region or row['Department'] == region:
                    links.append(row['Link'])
    except FileNotFoundError:
        logging.error(f"CSV file {csv_path} not found.")
        return

    region_dir = os.path.join('downloads', region)
    os.makedirs(region_dir, exist_ok=True)

    for link in links:
        filename = os.path.join(region_dir, os.path.basename(link))
        try:
            logging.info(f"Downloading {link} to {filename}")
            response = requests.get(link, stream=True)
            response.raise_for_status()
            with open(filename, 'wb') as f:
                for chunk in response.iter_content(1024):
                    f.write(chunk)
            logging.info(f"Successfully downloaded {filename}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Error downloading {link}: {e}")


def extract_and_merge_7z_files(region):
    region_dir = os.path.join('downloads', region)
    if not os.path.exists(region_dir):
        logging.error(f"Directory {region_dir} does not exist.")
        return
    
    files = sorted([os.path.join(region_dir, f) for f in os.listdir(region_dir) if f.endswith('.7z')])

    if not files:
        logging.info(f"No .7z files found in {region_dir}")
        return

    try:
        for file in files:
            with py7zr.SevenZipFile(file, mode='r') as archive:
                archive.extractall(path=region_dir)
        logging.info(f"Decompression completed for region {region}")
    except py7zr.ArchiveError as e:
        logging.error(f"Error during extraction: {e}")


def prepare_data_based_on_shapefiles(input_shapefile, department_geojson, csv_filename):
    """
    Downloads data for departments intersected with the input shapefile.

    :param input_shapefile: Path to the shapefile containing the entities
    :param department_geojson: Path to the GeoJSON of the departments
    :param csv_filename: Path to the CSV file containing the download links
    """
    try:
        departments = gpd.read_file(department_geojson)
        input_data = gpd.read_file(input_shapefile)
    except Exception as e:
        logging.error(f"Error reading shapefile or GeoJSON: {e}")
        return

    #I reproject everything to 2154 to avoid issues with the spatial intersection
    if departments.crs != 'EPSG:2154':
        departments = departments.to_crs('EPSG:2154')
    if input_data.crs != 'EPSG:2154':
        input_data = input_data.to_crs('EPSG:2154')

    try:
        intersected_departments = gpd.overlay(departments, input_data, how='intersection', keep_geom_type=False)
        department_codes = intersected_departments['code'].unique()
    except Exception as e:
        logging.error(f"Error during spatial intersection: {e}")
        return

    for code in department_codes:
        download_data_from_csv(csv_filename, code)


def filter_tiles_by_intersection(reference_shapefile, tiles_shapefile, data_directory):
    """
    Filters the tiles that intersect the reference shapefile and removes those that do not.

    :param reference_shapefile: Path to the reference shapefile
    :param tiles_shapefile: Path to the shapefile of the tiles
    :param data_directory: Path to the directory containing the tile images
    """
    try:
        reference = gpd.read_file(reference_shapefile)
        tiles = gpd.read_file(tiles_shapefile)
    except Exception as e:
        logging.error(f"Error reading shapefile: {e}")
        return

    #I reproject everything to 2154 to avoid issues with the spatial intersection
    if reference.crs != 'EPSG:2154':
        reference = reference.to_crs('EPSG:2154')
    if tiles.crs != 'EPSG:2154':
        tiles = tiles.to_crs('EPSG:2154')

    try:
        intersected_tiles = gpd.overlay(tiles, reference, how='intersection', keep_geom_type=False)
        intersected_tile_ids = intersected_tiles['NOM'].unique()  
    except Exception as e:
        logging.error(f"Error during spatial intersection: {e}")
        return

    all_tiles = set(tiles['NOM'].unique())
    tiles_to_remove = all_tiles - set(intersected_tile_ids)

    for tile_id in tiles_to_remove:
        tile_file = os.path.join(data_directory, f"{tile_id}")
        if os.path.exists(tile_file):
            os.remove(tile_file)
            logging.info(f"Removed tile {tile_file}")


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

    parser_filter = subparsers.add_parser('filter', help="Filters tiles by intersection with reference shapefile.")
    parser_filter.add_argument('reference_shapefile', type=str, help="Path to the reference shapefile")
    parser_filter.add_argument('tiles_shapefile', type=str, help="Path to the shapefile of the tiles")
    parser_filter.add_argument('data_directory', type=str, help="Path to the directory containing the tile images")

    args = parser.parse_args()

    if args.command == 'fetch':
        fetch_download_links(args.url, args.csv_filename)
    elif args.command == 'download':
        download_data_from_csv(args.csv_path, args.region)
    elif args.command == 'extract':
        extract_and_merge_7z_files(args.region)
    elif args.command == 'shapefile':
        prepare_data_based_on_shapefiles(args.input_shapefile, args.department_geojson, args.csv_filename)
    elif args.command == 'filter':
        filter_tiles_by_intersection(args.reference_shapefile, args.tiles_shapefile, args.data_directory)

if __name__ == "__main__":
    main()
