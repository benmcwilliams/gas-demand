import unittest
from unittest.mock import Mock, patch
import pandas as pd

from src.analyzers.monthly_aggregates import completeness, daily_coverage, build_aggregates, SECTORS


def monthly(country, sector, source, demand=1, year=2026, month=8):
    return dict(country=country, type=sector, source=source, demand=demand,
                year=year, month=month)


def coverage(country, sector, source, days=31, year=2026, month=8):
    return dict(country=country, type=sector, source=source,
                observed_days=days, year=year, month=month)


class CompletenessTests(unittest.TestCase):
    def test_one_missing_day_invalidates_direct_and_derived(self):
        rows = [monthly('PT', 'power', 'energy-charts'),
                monthly('PT', 'industry-power', 'entsog'),
                monthly('PT', 'household', 'entsog'),
                monthly('PT', 'industry', 'calculated'),
                monthly('PT', 'total', 'calculated')]
        counts = [coverage('PT', 'power', 'energy-charts', 30),
                  coverage('PT', 'industry-power', 'entsog'),
                  coverage('PT', 'household', 'entsog')]
        result = completeness(pd.DataFrame(rows), pd.DataFrame(counts)).set_index('type')
        self.assertTrue(result.loc['household', 'is_complete'])
        for sector in ['power', 'industry', 'total']:
            self.assertFalse(result.loc[sector, 'is_complete'])

    def test_missing_german_household_does_not_invalidate_total(self):
        rows = [monthly('DE', 'total', 'the'), monthly('DE', 'power', 'energy-charts'),
                monthly('DE', 'industry', 'calculated')]
        counts = [coverage('DE', 'total', 'the'), coverage('DE', 'power', 'energy-charts')]
        result = completeness(pd.DataFrame(rows), pd.DataFrame(counts)).set_index('type')
        self.assertTrue(result.loc['total', 'is_complete'])
        self.assertFalse(result.loc['industry', 'is_complete'])

    def test_monthly_source_and_zero_are_valid(self):
        rows = pd.DataFrame([monthly('DE', 'household', 'bundesnetzagentur', 0)])
        self.assertTrue(completeness(rows, pd.DataFrame()).is_complete.iloc[0])

    def test_days_not_rows_and_null_demand(self):
        rows = pd.DataFrame(dict(country='DE', type='total', source='the', date=d, demand=v)
                            for d, v in [('2026-08-01 06:00:00', 1),
                                         ('2026-08-01 07:00:00', 2),
                                         ('2026-08-02', None)])
        self.assertEqual(daily_coverage(rows).observed_days.iloc[0], 1)

    def test_duplicate_country_month_rejected(self):
        row = monthly('DE', 'total', 'the')
        with self.assertRaises(ValueError):
            completeness(pd.DataFrame([row, row]), pd.DataFrame())


class AggregateTests(unittest.TestCase):
    def fixture(self, missing_weight=0.1):
        rows, counts = [], []
        for year, months in [(2025, range(1, 13)), (2026, [8])]:
            for month in months:
                days = pd.Timestamp(year, month, 1).days_in_month
                for country, base in [('AT', 100 * (1-missing_weight)),
                                      ('BG', 100 * missing_weight), ('UK', 50)]:
                    for sector in SECTORS:
                        source = 'test-daily'
                        rows.append(monthly(country, sector, source,
                                            base * (1.1 if year == 2026 else 1), year, month))
                        counts.append(coverage(country, sector, source,
                                               days, year, month))
        return pd.DataFrame(rows), pd.DataFrame(counts)

    def build(self, rows, counts):
        return build_aggregates(rows, counts, imputation_reference='year-on-year',
                                reference_date='2026-10-04')

    def test_full_sum_and_uk_inclusion(self):
        result, _ = self.build(*self.fixture())
        recent = result[(result.year == 2026) & (result.type == 'total')].set_index('country')
        self.assertEqual(recent.loc['EU', 'demand'], 110)
        self.assertEqual(recent.loc['EU+UK', 'demand'], 165)
        self.assertFalse(recent.loc['EU', 'aggregate_metadata']['is_imputed'])

    def test_partial_month_is_imputed_not_added(self):
        rows, counts = self.fixture()
        counts.loc[(counts.country == 'BG') & (counts.year == 2026), 'observed_days'] = 30
        rows.loc[(rows.country == 'BG') & (rows.year == 2026), 'demand'] = 999
        result, audit = self.build(rows, counts)
        recent = result[(result.year == 2026) & (result.type == 'total')].set_index('country')
        self.assertEqual(recent.loc['EU', 'demand'], 110)
        meta = recent.loc['EU', 'aggregate_metadata']
        self.assertAlmostEqual(meta['share_missing_countries'], 0.1)
        self.assertEqual(meta['missing_countries'], ['BG'])
        self.assertTrue(meta['is_imputed'])
        self.assertAlmostEqual(meta['imputed_demand_twh'], 11)

    def test_exact_20_percent_withheld_eu_but_europe_can_publish(self):
        rows, counts = self.fixture(0.2)
        rows = rows[~((rows.country == 'BG') & (rows.year == 2026))]
        result, audit = self.build(rows, counts)
        recent = audit[(audit.year == 2026) & (audit.type == 'total')].set_index('country')
        self.assertEqual(recent.loc['EU', 'status'], 'withheld_missing_share')
        self.assertEqual(recent.loc['EU+UK', 'status'], 'imputed')
        self.assertTrue(result[(result.year == 2026) & (result.country == 'EU')].empty)

    def test_partial_historical_reference_still_allows_imputation(self):
        rows, counts = self.fixture()
        rows = rows[~((rows.country == 'BG') & (rows.year == 2026))]
        counts.loc[(counts.country == 'BG') & (counts.year == 2025) & (counts.month == 8), 'observed_days'] = 30
        _, audit = self.build(rows, counts)
        recent = audit[(audit.year == 2026) & (audit.type == 'total')]
        self.assertTrue((recent.status == 'imputed').all())
        self.assertAlmostEqual(recent[recent.country == 'EU'].demand.iloc[0], 110)

    def test_absent_historical_reference_uses_demand_share_fallback(self):
        rows, counts = self.fixture()
        rows = rows[~((rows.country == 'BG') & ((rows.year == 2026) |
                     ((rows.year == 2025) & (rows.month == 8))))]
        # Use another complete baseline year so this specifically tests reference absence.
        baseline = rows[rows.year == 2025].copy()
        missing_baseline_month = baseline[(baseline.country == 'BG') & (baseline.month == 7)].copy()
        missing_baseline_month['month'] = 8
        baseline = pd.concat([baseline, missing_baseline_month], ignore_index=True)
        baseline['year'] = 2024
        rows = pd.concat([rows, baseline], ignore_index=True)
        _, audit = build_aggregates(rows, counts, imputation_reference='year-on-year',
                                    weight_year=2024, reference_date='2026-10-04')
        recent = audit[(audit.year == 2026) & (audit.type == 'total')]
        self.assertTrue((recent.status == 'imputed').all())
        self.assertAlmostEqual(recent[recent.country == 'EU'].demand.iloc[0], 110)
        for meta in recent.aggregate_metadata:
            self.assertEqual(meta['aggregation_method'], 'demand_share_fallback')
            self.assertEqual(meta['fallback_reason'], 'missing_reference')

    def test_missing_weight_month_fails_instead_of_silently_omitting_country(self):
        rows, counts = self.fixture()
        rows = rows[~((rows.country == 'BG') & (rows.year == 2025) & (rows.month == 1))]
        with self.assertRaises(ValueError):
            self.build(rows, counts)


class PublicationTests(unittest.TestCase):
    def test_withheld_hides_existing_record_without_upserting(self):
        from src.utils.mongo import MongoMonthlySeriesWriter
        writer = MongoMonthlySeriesWriter()
        client, collection = Mock(), Mock()
        audit = pd.DataFrame([dict(country='EU', type='industry', year=2026, month=9,
                                   status='withheld_missing_share', aggregate_metadata={'is_imputed': False})])
        with patch.object(writer, '_get_collection', return_value=(client, collection)), \
             patch.object(writer, 'upsert_dataframe', return_value=0) as upsert:
            writer.publish_aggregates(pd.DataFrame(), audit)
        operation = collection.bulk_write.call_args.args[0][0]
        self.assertFalse(operation._upsert)
        self.assertFalse(operation._doc['$set']['should_plot'])
        upsert.assert_called_once()
        client.close.assert_called_once()

    def test_published_record_keeps_imputation_metadata(self):
        from src.utils.mongo import MongoMonthlySeriesWriter
        writer = MongoMonthlySeriesWriter()
        client, collection = Mock(), Mock()
        collection.bulk_write.return_value.upserted_count = 1
        collection.bulk_write.return_value.modified_count = 0
        meta = {'is_imputed': True, 'status': 'imputed', 'missing_countries': ['PT']}
        rows = pd.DataFrame([dict(country='EU', type='industry', year=2026, month=8,
                                  demand=48.7, source='calculated', should_plot=True,
                                  aggregate_metadata=meta)])
        with patch.object(writer, '_get_collection', return_value=(client, collection)):
            writer.upsert_dataframe(rows)
        payload = collection.bulk_write.call_args.args[0][0]._doc['$set']
        self.assertEqual(payload['aggregate_metadata'], meta)
        self.assertEqual(payload['aggregation_status'], 'imputed')
        self.assertTrue(payload['should_plot'])


if __name__ == '__main__':
    unittest.main()
