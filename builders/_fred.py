#!/usr/bin/env python3
"""
Shared FRED fetch library for builders -- the `Fred` class.

One place for the things every FRED read has to get right, so a builder's
fetch stage is a line or two and its validate() is the only thing worth
reading. Plain HTTP GET against `fredgraph.csv`, no `pandas_datareader` (the
decision on QuantEcon/data-lectures#26: a wrapper library in the builder
re-creates the single-point fragility Phase 5 exists to remove).

    from _fred import Fred
    fred = Fred()
    unrate = fred.series('UNRATE')                          # full history
    yields = fred.frame(['GS1', 'GS10'], start='1953-04-01', end='2024-12-01')
    tips   = fred.series('DFII5', freq='Monthly', agg='avg') # daily -> monthly

What it normalises:

- the date column, which fredgraph titles `observation_date` today and
  `DATE` in older exports -- every Series/DataFrame comes back with a
  DatetimeIndex named `DATE`, so committed files keep the header the
  lectures expect
- FRED's `.` for a missing observation -> NaN
- the User-Agent: NONE by default, deliberately. Measured 2026-09-01 from a
  GitHub-hosted runner (data-lectures#115): FRED's edge answers
  `Python-urllib/3.12` (urllib's own default) and `curl/8.5.0` in ~50 ms,
  and STALLS `qeld-builder` and even `Mozilla/5.0` until the read times
  out. The same requests all succeed from a workstation, which is how the
  custom agent survived local testing. Pass `user_agent=` only if you have
  measured that it works from where the builder will actually run
- one series per request, aligned with an outer join in frame(), so a
  series that starts later is simply empty before its first observation

Not a builder: the leading underscore keeps it out of any manifest's
`builder:` field. Import it as `from _fred import Fred` (builders run with
their own directory as sys.path[0]).
"""
import io
import urllib.parse
import urllib.request

import pandas as pd

FREDGRAPH = 'https://fred.stlouisfed.org/graph/fredgraph.csv'


class Fred:
    def __init__(self, user_agent=None, timeout=60):
        self.user_agent = user_agent      # None -> urllib's default, see above
        self.timeout = timeout

    def _get(self, params):
        query = urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})
        headers = {'User-Agent': self.user_agent} if self.user_agent else {}
        request = urllib.request.Request(f'{FREDGRAPH}?{query}', headers=headers)
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            return response.read()

    def series(self, sid, start=None, end=None, freq=None, agg=None):
        """One FRED series as a pd.Series named `sid`, indexed by DATE.

        `start`/`end` are ISO dates (fredgraph's `cosd`/`coed`); `freq` and
        `agg` request a server-side frequency change, e.g. freq='Monthly',
        agg='avg' for the monthly mean of a daily series (fredgraph's
        `fq`/`fam`)."""
        payload = self._get({'id': sid, 'cosd': start, 'coed': end, 'fq': freq, 'fam': agg})
        frame = pd.read_csv(io.BytesIO(payload), index_col=0, parse_dates=True, na_values='.')
        if frame.shape[1] != 1:
            raise ValueError(f'{sid}: expected one value column, got {list(frame.columns)}')
        s = frame.iloc[:, 0].rename(sid)
        s.index.name = 'DATE'
        return s

    def frame(self, sids, start=None, end=None):
        """Several series on one DATE index (outer join, sorted)."""
        out = pd.concat([self.series(sid, start, end) for sid in sids], axis=1).sort_index()
        out.index.name = 'DATE'
        return out
