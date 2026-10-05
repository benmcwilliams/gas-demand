"""Monthly EU/Europe aggregates, with country-sector input completeness."""
from calendar import monthrange
from functools import lru_cache

import numpy as np
import pandas as pd

SECTORS = ('total', 'industry', 'household', 'power', 'industry-household')
AREAS = ('EU', 'EU+UK')
# The tracker covers these EU members, not all EU27 countries.
EU_COUNTRIES = set('AT BE BG HR CZ DK EE FI FR DE GR HU IT LV LT LU NL PL PT RO SK SI ES SE'.split())
CALCULATED_TOTAL_COUNTRIES = {'BE', 'FR', 'HU', 'IT', 'LU', 'NL', 'PT', 'RO'}
SUBTRACT_POWER_COUNTRIES = {'HU', 'LU', 'PT', 'RO'}
MONTHLY_SOURCES = {'eurostat', 'bundesnetzagentur', 'CBS'}
KEY = ['country', 'type', 'year', 'month']


def daily_coverage(daily: pd.DataFrame) -> pd.DataFrame:
    """Count distinct valid calendar days, not rows (THE timestamps include hours)."""
    daily = daily.copy()
    if 'is_calculated' in daily:
        daily = daily[~daily.is_calculated.astype(bool)]
    daily['date'] = pd.to_datetime(daily.date.astype(str).str[:10], errors='coerce')
    value_column = 'demand' if 'demand' in daily else 'value'
    daily[value_column] = pd.to_numeric(daily[value_column], errors='coerce')
    daily = daily[daily.date.notna() & np.isfinite(daily[value_column])]
    daily['year'] = daily.date.dt.year
    daily['month'] = daily.date.dt.month
    return daily.groupby(KEY + ['source'], as_index=False).agg(observed_days=('date', 'nunique'))


def normalize_monthly(monthly: pd.DataFrame) -> pd.DataFrame:
    monthly = monthly.copy()
    if 'demand' not in monthly:
        monthly = monthly.rename(columns={'value': 'demand'})
    monthly['demand'] = pd.to_numeric(monthly.demand, errors='coerce')
    monthly = monthly[np.isfinite(monthly.demand)]
    monthly = monthly[monthly.country.isin(EU_COUNTRIES | {'UK'})]
    if monthly.duplicated(KEY).any():
        raise ValueError('Multiple monthly records for a country/sector/month; resolve sources before aggregating.')
    return monthly


def completeness(monthly: pd.DataFrame, coverage: pd.DataFrame) -> pd.DataFrame:
    """A derived value is complete only when every dependency is complete.

    Monthly publications need a finite record. Daily-backed publications need
    every calendar day for each source contributing to the selected record.
    """
    monthly = normalize_monthly(monthly)
    records = {tuple(row[k] for k in KEY): row for row in monthly.to_dict('records')}
    counts = {tuple(row[k] for k in KEY + ['source']): int(row['observed_days'])
              for row in coverage.to_dict('records')}

    @lru_cache(None)
    def check(country, sector, year, month):
        row = records.get((country, sector, year, month))
        if row is None:
            return False, f'{sector}: missing monthly record'
        dependencies = []
        if sector == 'industry-household':
            dependencies = ['total', 'power']
        elif sector == 'industry' and country == 'DE':
            dependencies = ['total', 'household', 'power']
        elif sector == 'industry' and country in SUBTRACT_POWER_COUNTRIES:
            dependencies = ['industry-power', 'power']
        elif sector == 'total' and country in CALCULATED_TOTAL_COUNTRIES:
            dependencies = ['industry', 'household', 'power']
        if dependencies:
            problems = [reason for dep in dependencies
                        for valid, reason in [check(country, dep, year, month)] if not valid]
            return not problems, '; '.join(problems)
        # NL industry's source label includes CBS even after the CBS history ends.
        if country == 'NL' and sector == 'industry':
            sources = ['entsog']
            power = records.get((country, 'power', year, month))
            if power and 'CBS' in power['source'].split(', '):
                valid, reason = check(country, 'power', year, month)
                if not valid:
                    return False, reason
        else:
            sources = str(row['source']).split(', ')
        problems = []
        expected = monthrange(int(year), int(month))[1]
        for source in sources:
            if source in MONTHLY_SOURCES:
                continue
            observed = counts.get((country, sector, year, month, source), 0)
            if observed != expected:
                problems.append(f'{sector}/{source}: {observed}/{expected} days')
        return not problems, '; '.join(problems)

    result = monthly.copy()
    outcomes = [check(*key) for key in result[KEY].itertuples(index=False, name=None)]
    result['is_complete'] = [x[0] for x in outcomes]
    result['incomplete_reason'] = [x[1] for x in outcomes]
    return result


def build_aggregates(monthly: pd.DataFrame, coverage: pd.DataFrame, *,
                     imputation_reference: str, weight_year: int = 2025,
                     missing_share_limit: float = 0.20,
                     reference_date=None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return publishable rows and an audit row for every area/sector/month.

    Annual weights use the recorded 2025 values (indicative size, independent
    of strict reporting checks). References use recorded prior-year monthly
    values; estimates never become inputs to another estimate.
    No missing country is silently removed from the expected contributor set.
    """
    if imputation_reference not in {'year-on-year', 'month-on-month'}:
        raise ValueError('Select year-on-year or month-on-month imputation')
    if not 0 < missing_share_limit <= 1:
        raise ValueError('missing_share_limit must lie in (0, 1]')
    checked = completeness(monthly, coverage)
    checked = checked[checked.type.isin(SECTORS)]
    baseline = checked[checked.year == weight_year]
    if baseline.empty:
        raise ValueError(f'No country data for weight year {weight_year}')
    now = pd.Timestamp(reference_date or pd.Timestamp.today()).normalize()
    latest_month = now.replace(day=1) - pd.Timedelta(days=1)
    periods = sorted({(int(y), int(m)) for y, m in checked[['year', 'month']].itertuples(index=False, name=None)
                      if pd.Timestamp(int(y), int(m), 1) <= latest_month})
    records = {tuple(row[k] for k in KEY): row for row in checked.to_dict('records')}
    published, audit = [], []
    for area in AREAS:
        allowed = EU_COUNTRIES | ({'UK'} if area == 'EU+UK' else set())
        for sector in SECTORS:
            sector_baseline = baseline[(baseline.type == sector) & baseline.country.isin(allowed)]
            countries = sorted(set(sector_baseline.country))
            if not countries:
                raise ValueError(f'No {weight_year} weights for {area}/{sector}')
            sizes = sector_baseline.groupby('country').demand.sum()
            month_counts = sector_baseline.groupby('country').month.nunique()
            if (month_counts != 12).any() or (sizes < 0).any() or sizes.sum() <= 0:
                raise ValueError(f'Need 12 months of nonnegative annual weights for {area}/{sector}')
            # Refuse to silently omit a new country's sector when it has no weights.
            observed = set(checked[(checked.type == sector) & checked.country.isin(allowed)].country)
            if observed - set(countries):
                raise ValueError(f'Countries without {weight_year} weights: {sorted(observed - set(countries))}')
            weights = (sizes / sizes.sum()).to_dict()
            for year, month in periods:
                current = {c: records.get((c, sector, year, month)) for c in countries}
                reporting = [c for c in countries if current[c] and current[c]['is_complete']]
                missing = sorted(set(countries) - set(reporting))
                share = float(sum(weights[c] for c in missing))
                reported_sum = float(sum(current[c]['demand'] for c in reporting))
                metadata = {
                    'aggregation_method': 'sum', 'is_imputed': False,
                    'weight_year': weight_year, 'share_missing_countries': share,
                    'country_weights': {c: float(weights[c]) for c in countries},
                    'expected_countries': countries, 'reporting_countries': reporting,
                    'missing_countries': missing,
                    'missing_reasons': {c: (current[c]['incomplete_reason'] if current[c]
                                           else 'missing monthly record') for c in missing},
                    'reported_demand_twh': reported_sum, 'imputed_demand_twh': 0.0,
                    'imputation_reference': imputation_reference,
                }
                status, value = 'complete', reported_sum
                if missing:
                    if share >= missing_share_limit or np.isclose(share, missing_share_limit, rtol=0, atol=1e-12):
                        status, value = 'withheld_missing_share', None
                    elif not reporting:
                        status, value = 'withheld_no_reporting_countries', None
                    else:
                        reference = (pd.Timestamp(year, month, 1) -
                                     pd.DateOffset(years=1 if imputation_reference == 'year-on-year' else 0,
                                                   months=1 if imputation_reference == 'month-on-month' else 0))
                        refs = {c: records.get((c, sector, reference.year, reference.month)) for c in countries}
                        reference_missing = [c for c in countries if refs[c] is None]
                        metadata['reference_missing_countries'] = reference_missing
                        valid = not reference_missing
                        reference_reported = sum(refs[c]['demand'] for c in reporting) if valid else 0
                        if not valid or reference_reported <= 0:
                            # Without a usable change reference, assume missing
                            # countries retain their fixed baseline demand shares.
                            value = reported_sum / (1 - share)
                            estimates = {c: float(value * weights[c]) for c in missing}
                            status = 'imputed'
                            metadata.update(
                                aggregation_method='demand_share_fallback', is_imputed=True,
                                imputed_demand_twh=float(sum(estimates.values())),
                                imputed_country_demand_twh=estimates,
                                fallback_reason=('missing_reference' if not valid
                                                 else 'nonpositive_reference_reporting_sum'),
                            )
                        else:
                            factor = reported_sum / reference_reported
                            estimates = {c: float(refs[c]['demand'] * factor) for c in missing}
                            imputed = sum(estimates.values())
                            value = reported_sum + imputed
                            status = 'imputed'
                            metadata.update(aggregation_method='imputed', is_imputed=True,
                                            imputed_demand_twh=float(imputed),
                                            imputed_country_demand_twh=estimates,
                                            reporting_change_pct=float((factor - 1) * 100),
                                            reference_year=int(reference.year), reference_month=int(reference.month))
                metadata['status'] = status
                audit.append({'country': area, 'type': sector, 'year': year, 'month': month,
                              'status': status, 'demand': value,
                              'missing_share_pct': share * 100,
                              'missing_countries': ', '.join(missing), 'aggregate_metadata': metadata})
                if value is not None:
                    published.append({'country': area, 'type': sector, 'year': year, 'month': month,
                                      'demand': round(value, 2), 'source': 'calculated',
                                      'should_plot': True, 'aggregate_metadata': metadata})
    return (pd.DataFrame(published, columns=KEY + ['demand', 'source', 'should_plot', 'aggregate_metadata']),
            pd.DataFrame(audit, columns=KEY + ['status', 'demand', 'missing_share_pct',
                                             'missing_countries', 'aggregate_metadata']))


def compare_legacy(aggregates: pd.DataFrame, monthly: pd.DataFrame) -> pd.DataFrame:
    """Compare by area/sector/month, never sum legacy and newly calculated rows."""
    legacy = monthly[monthly.country.isin(AREAS) & monthly.type.isin(SECTORS)].copy()
    if 'demand' not in legacy:
        legacy = legacy.rename(columns={'value': 'demand'})
    if legacy.duplicated(KEY).any():
        raise ValueError('Duplicate legacy aggregate keys')
    result = aggregates[KEY + ['demand']].merge(
        legacy[KEY + ['demand']].rename(columns={'demand': 'legacy_demand'}),
        on=KEY, how='outer')
    current = normalize_monthly(monthly)
    sums = []
    for area in AREAS:
        allowed = EU_COUNTRIES | ({'UK'} if area == 'EU+UK' else set())
        part = current[current.country.isin(allowed) & current.type.isin(SECTORS)]
        summed = part.groupby(['type', 'year', 'month'], as_index=False).demand.sum()
        summed['country'] = area
        sums.append(summed.rename(columns={'demand': 'current_country_sum'}))
    result = result.merge(pd.concat(sums), on=KEY, how='left')
    result['difference_twh'] = result.demand - result.legacy_demand
    result['difference_pct'] = result.difference_twh / result.legacy_demand.replace(0, np.nan) * 100
    return result.sort_values(KEY)
