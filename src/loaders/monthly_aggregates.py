"""Read-only by default: audit aggregates against legacy MongoDB records."""
import argparse
import os
from pathlib import Path

import pandas as pd
from pymongo import MongoClient

from src.utils.mongo import MongoMonthlySeriesWriter
from src.utils.config import Config
from src.analyzers.monthly_aggregates import completeness, build_aggregates, compare_legacy


def read_snapshot(directory: Path):
    writer = MongoMonthlySeriesWriter()
    if not writer.enabled:
        raise ValueError('MONGO_URI is not configured')
    # Do not call writer._get_collection: even its index creation is a mutation.
    with MongoClient(writer.mongo_uri, serverSelectionTimeoutMS=10000,
                     socketTimeoutMS=30000) as client:
        db = client[writer.database_name]
        monthly = pd.DataFrame(list(db[writer.collection_name].find(
            {}, {'_id': 0, 'country': 1, 'type': 1, 'source': 1, 'year': 1,
                 'month': 1, 'value': 1, 'should_plot': 1})))
        pipeline = [
            {'$match': {'is_calculated': False, 'value': {'$type': 'number'}}},
            {'$group': {'_id': {'country': '$country', 'type': '$type', 'source': '$source',
                               'year': {'$year': '$date'}, 'month': {'$month': '$date'}},
                        'days': {'$addToSet': {'$dayOfMonth': '$date'}}}},
        ]
        coverage = pd.DataFrame([{**r['_id'], 'observed_days': len(r['days'])}
                                for r in db[os.getenv('MONGO_DAILY_COLLECTION', 'daily_series')]
                                .aggregate(pipeline, maxTimeMS=60000)])
    directory.mkdir(parents=True, exist_ok=True)
    monthly.rename(columns={'value': 'demand'}).to_csv(directory / 'monthly_snapshot.csv', index=False)
    coverage.to_csv(directory / 'daily_coverage_snapshot.csv', index=False)
    return monthly, coverage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=Path('src/data/analyzed/aggregate_audit'))
    parser.add_argument('--snapshot-dir', type=Path, help='Reuse a read-only snapshot, without MongoDB access')
    parser.add_argument('--snapshot-only', action='store_true')
    parser.add_argument('--imputation-reference', choices=['year-on-year', 'month-on-month'],
                        help='Required to calculate aggregates')
    parser.add_argument('--publish', action='store_true', help='Explicitly publish after saving comparison')
    args = parser.parse_args()
    if args.snapshot_dir:
        monthly = pd.read_csv(args.snapshot_dir / 'monthly_snapshot.csv')
        coverage = pd.read_csv(args.snapshot_dir / 'daily_coverage_snapshot.csv')
    else:
        monthly, coverage = read_snapshot(args.output_dir)
    if args.snapshot_only:
        print(f'Snapshot saved to {args.output_dir}')
        return
    checked = completeness(monthly, coverage)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    checked.to_csv(args.output_dir / 'country_completeness.csv', index=False)
    print(f'Checked {len(checked)} country-sector records')
    if not args.imputation_reference:
        if args.publish:
            parser.error('--publish requires --imputation-reference')
        return
    options = Config().config_data.get('monthly_aggregates', {})
    aggregates, audit = build_aggregates(
        monthly, coverage, imputation_reference=args.imputation_reference,
        weight_year=options.get('weight_year', 2025),
        missing_share_limit=options.get('missing_share_limit', 0.20))
    comparison = compare_legacy(aggregates, monthly)
    aggregates.to_json(args.output_dir / 'aggregates.json', orient='records', indent=2)
    audit.to_json(args.output_dir / 'aggregate_audit.json', orient='records', indent=2)
    comparison.to_csv(args.output_dir / 'legacy_comparison.csv', index=False)
    print(audit[(audit.year == 2026) & audit.month.isin([7, 8, 9])]
          .drop(columns=['aggregate_metadata']).sort_values(['country', 'type', 'month']).to_string(index=False))
    matched = comparison.dropna(subset=['demand', 'legacy_demand'])
    print(f'Legacy overlap: {len(matched)} values; '
          f'{int((matched.difference_twh.abs() > 0.01).sum())} differ by more than 0.01 TWh')
    print(f'Reports saved to {args.output_dir}')
    if args.publish:
        count = MongoMonthlySeriesWriter().publish_aggregates(aggregates, audit)
        print(f'Published {count} aggregate records')
    else:
        print('Dry run: no MongoDB records changed')


if __name__ == '__main__':
    main()
