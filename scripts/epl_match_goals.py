"""
Builder for lectures/epl_match_goals.csv.

Collects full-time scores for ten completed English Premier League seasons,
2015-16 through 2024-25, from the openfootball football.json release.

Upstream publishes one JSON file per league-season. The extract keeps the date,
the two teams and the two full-time scores, which is what a lecture fitting a
Poisson distribution to goals per match needs.

Stages: fetch -> pre-process -> validate -> write.
"""

import json
import os
import urllib.request

import pandas as pd

CURRENT_FILE_DIR = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT = os.path.dirname(CURRENT_FILE_DIR)
PUBLISHED_DIR = os.path.join(REPO_ROOT, 'lectures')

BASE_URL = ('https://raw.githubusercontent.com/openfootball/football.json/'
            'master/{season}/en.1.json')

SEASONS = [f'{year}-{str(year + 1)[2:]}' for year in range(2015, 2025)]

OUT_FILE = 'epl_match_goals.csv'

MATCHES_PER_SEASON = 380      # 20 teams, home and away


def fetch():
    """One JSON file per season."""
    return {s: json.load(urllib.request.urlopen(BASE_URL.format(season=s)))
            for s in SEASONS}


def pre_process(raw):
    """Flatten to one row per match, dropping any match without a full-time score."""
    rows = []
    for season, payload in raw.items():
        for match in payload['matches']:
            full_time = (match.get('score') or {}).get('ft')
            if full_time is None:
                continue
            rows.append({
                'season': season,
                'date': match['date'],
                'home_team': match['team1'],
                'away_team': match['team2'],
                'home_goals': full_time[0],
                'away_goals': full_time[1],
            })
    return pd.DataFrame(rows).sort_values(['season', 'date']).reset_index(drop=True)


def validate(df):
    """Refuse to write anything that is not the shape we expect."""
    assert list(df.columns) == ['season', 'date', 'home_team', 'away_team',
                                'home_goals', 'away_goals']
    assert not df.isnull().values.any()
    counts = df['season'].value_counts()
    assert len(counts) == len(SEASONS), f'expected {len(SEASONS)} seasons'
    assert (counts == MATCHES_PER_SEASON).all(), f'incomplete season:\n{counts}'
    assert df[['home_goals', 'away_goals']].min().min() >= 0
    assert df[['home_goals', 'away_goals']].max().max() < 15


def run():
    df = pre_process(fetch())
    validate(df)
    df.to_csv(os.path.join(PUBLISHED_DIR, OUT_FILE), index=False)
    goals = df['home_goals'] + df['away_goals']
    print(f'wrote {OUT_FILE}: {len(df)} matches, '
          f'mean {goals.mean():.3f} goals per match')


if __name__ == '__main__':
    run()
