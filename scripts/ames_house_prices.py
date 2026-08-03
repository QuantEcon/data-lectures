"""
Builder for lectures/ames_house_prices.csv.

Subsets the Ames, Iowa housing data of De Cock (2011) down to the sale price
and a few characteristics of each house, and gives the columns lowercase names.

The upstream file is an 82-column Excel workbook assembled for a regression
exercise; the extract here keeps only what a lecture on observed distributions
needs.

Stages: fetch -> pre-process -> validate -> write.
"""

import os

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

SOURCE_URL = 'http://jse.amstat.org/v19n3/decock/AmesHousing.xls'

OUT_FILE = 'ames_house_prices.csv'

COLUMNS = {
    'SalePrice': 'price',
    'Bedroom AbvGr': 'bedrooms',
    'Gr Liv Area': 'living_area_sqft',
    'Year Built': 'year_built',
    'Neighborhood': 'neighborhood',
}


def fetch():
    return pd.read_excel(SOURCE_URL)


def pre_process(raw):
    return raw[list(COLUMNS)].rename(columns=COLUMNS)


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == list(COLUMNS.values())
    assert len(df) == 2930, f'expected 2930 sales, got {len(df)}'
    assert not df.isnull().values.any()
    assert df['price'].min() > 0
    assert df['year_built'].between(1800, 2010).all()


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    print(f'wrote {OUT_FILE}: {len(df)} rows, '
          f'median price {df["price"].median():,.0f}')


if __name__ == '__main__':
    run()
