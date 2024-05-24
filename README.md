# BD ORTHO Data Downloader

This Python script allows you to fetch, download, and process BD ORTHO data. It includes functionalities to retrieve download links, download files for specified regions, decompress the downloaded files, download data based on spatial intersections with shapefiles, and filter downloaded tiles based on spatial intersections.

## Features

- **Fetch Download Links**: Retrieve download links from the BDORTHO webpage (https://geoservices.ign.fr/bdortho) and save them in a CSV file.
- **Download Data**: Download files from the links present in the CSV file for a specified region.
- **Extract Files**: Decompress the downloaded .7z files for a specified region.
- **Spatial Intersection**: Download data for departments intersected with a given shapefile.
- **Filter Tiles**: Remove tiles that do not intersect with the reference shapefile from the downloaded data.

## Installation

First, clone the repository:

```bash
git clone https://github.com/r-wenger/Download-BDOrtho21.git
cd Download-BDOrtho21
```

- Python 3.x
- `requests`
- `beautifulsoup4`
- `py7zr`
- `geopandas`
- `multivolumefile`

You can install the required packages using:

```bash
pip install requests beautifulsoup4 py7zr geopandas multivolumefile
```

## Usage

The script uses argparse to handle different commands. Below are the available commands and their usage.

### Fetch Download Links

Fetches download links from a specified webpage and saves them in a CSV file using this link: https://geoservices.ign.fr/bdortho

```bash
python download_bdortho.py fetch <url> <csv_filename>
```

**Arguments**:
- `url`: URL of the webpage to parse (https://geoservices.ign.fr/bdortho)
- `csv_filename`: Name of the CSV file to create.

### Download Data

Downloads files from the links present in the CSV for the specified region (For example, 01 or Ain).

```bash
python download_bdortho.py download <csv_path> <region>
```

**Arguments**:
- `csv_path`: Path to the CSV file.
- `region`: Code or name of the region.

### Extract Files

Decompresses the downloaded .7z files for the specified region.

```bash
python download_bdortho.py extract <region>
```

**Arguments**:
- `region`: Code or name of the region.

### Spatial Intersection

Downloads data for departments intersected with a given shapefile.

```bash
python download_bdortho.py shapefile <input_shapefile> <department_geojson> <csv_filename>
```

**Arguments**:
- `input_shapefile`: Path to the shapefile containing the entities.
- `department_geojson`: Path to the GeoJSON of the departments (contour-des-departements.geojson).
- `csv_filename`: Path to the CSV file containing the download links.

### Filter Tiles

Removes tiles that do not intersect with the reference shapefile from the downloaded data.

```bash
python download_bdortho.py filter <reference_shapefile> <tiles_shapefile> <data_directory>
```

**Arguments**:
- `reference_shapefile`: Path to the reference shapefile.
- `tiles_shapefile`: Path to the shapefile of the tiles (e.g., dalles.shp).
- `data_directory`: Path to the directory containing the tile images.

## Example

1. Fetch download links and save them in a CSV file:

    ```bash
    python download_bdortho.py fetch https://geoservices.ign.fr/bdortho bdortho_download_links.csv
    ```

2. Download data for a specific region (e.g., region code `01`):

    ```bash
    python download_bdortho.py download bdortho_download_links.csv 01
    ```

3. Extract the downloaded .7z files for the region:

    ```bash
    python download_bdortho.py extract 01
    ```

4. Download data for departments intersected with a shapefile:

    ```bash
    python download_bdortho.py shapefile input.shp departments.geojson bdortho_download_links.csv
    ```

5. Filter downloaded tiles to keep only those intersecting with the reference shapefile:

    ```bash
    python download_bdortho.py filter reference.shp dalles.shp /path/to/data_directory
    ```

## Acknowledgments

- Thanks to the IGN for providing the data.
