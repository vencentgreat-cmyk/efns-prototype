"""Offline recovery rehearsal; emit counts/hashes only, never business values."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.migration import MigrationSourceFile, analyze_migration_files, load_mapping
from data.historical_corrections import build_historical_correction_preview
from data.migration_identity import scoped_raw_rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--destination', type=Path, default=ROOT / '.local/company-20261019/recovery_preview.json')
    args = parser.parse_args()
    mapping = load_mapping()
    evidence_path = ROOT / '.local/continuity-20261014/before.json'
    saved = json.loads(evidence_path.read_text(encoding='utf-8')) if evidence_path.exists() else {}
    hashes = {row['SOURCE_FILENAME']: row['FILE_HASH'] for row in saved.get('historical_files', [])}
    files, inventory = [], []
    for entity in mapping['entity_order']:
        spec = mapping['entities'][entity]
        path = args.source / spec['filename']
        content = path.read_bytes()
        with path.open(encoding='utf-8-sig', newline='') as handle:
            reader = csv.reader(handle)
            headers = next(reader)
            if not headers or any(not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*', name) for name in headers):
                raise ValueError(f'{path.name}: logical column header check failed')
            rows = sum(1 for row in reader if any(value.strip() for value in row))
        digest = hashlib.sha256(content).hexdigest()
        inventory.append({'entity': entity, 'filename': path.name, 'columns': len(headers),
                          'source_rows': rows, 'bytes': len(content), 'sha256': digest,
                          'matches_old_recorded_hash': digest == hashes[path.name] if path.name in hashes else None})
        files.append(MigrationSourceFile(path.name, content))
    analysis = analyze_migration_files(files)
    existing = {entity: {str(row[mapping['entities'][entity]['id_field']]) for row in records}
                for entity, records in analysis.records.items()}
    owners = {str(row['QUOTA_ID']): str(row['ACCOUNT_ID'])
              for row in analysis.records.get('QUOTA_REGISTRATION', [])}
    staged_rows = scoped_raw_rows(analysis.batch_id, analysis.raw_rows, allow_unassigned=True)
    corrections = build_historical_correction_preview(analysis.batch_id, staged_rows,
                                                     existing, quota_accounts=owners, mapping=mapping)
    orphan_counts = []
    for entity, records in analysis.records.items():
        for field, (parent, _) in mapping['entities'][entity].get('foreign_keys', {}).items():
            missing = sum(row.get(field) is not None and str(row[field]) not in existing[parent] for row in records)
            if missing:
                orphan_counts.append({'entity': entity, 'field': field, 'parent_entity': parent, 'count': missing})
    prior_path = Path.home() / 'Downloads/EIMS_rejected_record_corrections_2026-10-05/historical_correction_preview_271.csv'
    prior_comparison = {}
    transitioned_parent_dispositions = {}
    if prior_path.exists():
        by_source = {(row['SOURCE_ENTITY'], int(row['SOURCE_ROW_NUMBER'])): row for row in staged_rows}
        with prior_path.open(encoding='utf-8-sig', newline='') as handle:
            prior_rows = list(csv.DictReader(handle))
        prior_by_id = {(row['SOURCE_ENTITY'], row['ORIGINAL_GUID'].casefold()): row['DISPOSITION'] for row in prior_rows}
        for prior in prior_rows:
            current = by_source.get((prior['SOURCE_ENTITY'], int(prior['EXCEL_ROW_NUMBER_INCLUDING_HEADER'])))
            label = prior['DISPOSITION'] + ' -> ' + (current['VALIDATION_STATUS'] if current else 'MISSING')
            if prior['DISPOSITION'] == 'PENDING_CONFIRMATION' and current and current['VALIDATION_STATUS'] == 'READY':
                normalized = current['NORMALIZED_DATA'] or {}
                label += '; ' + prior['SOURCE_ENTITY'] + '; related_transaction=' + ('present' if normalized.get('RELATED_TRANSACTION_ID') is not None else 'null')
                parent = normalized.get('RELATED_TRANSACTION_ID')
                if parent is not None:
                    disposition = prior_by_id.get(('QUOTA_TRANSACTION', str(parent).casefold()), 'Not in prior rejection list')
                    transitioned_parent_dispositions[disposition] = transitioned_parent_dispositions.get(disposition, 0) + 1
            prior_comparison[label] = prior_comparison.get(label, 0) + 1
    summary = {
        'scope': 'Offline rehearsal against original source files, not company database state',
        'business_writes': 0, 'files': inventory,
        'source_rows': len(analysis.raw_rows), 'ready_rows': analysis.ready_count,
        'rejected_rows': analysis.rejected_count,
        'prospective_original_target_rows': sum(len(rows) for rows in analysis.records.values()),
        'reconciliation': analysis.reconciliation.to_dict('records'),
        'prospective_correction_core_rows': len(corrections.core_rows),
        'prospective_pending_rows': len(corrections.pending_rows),
        'correction_summary': corrections.summary.to_dict('records'),
        'prospective_orphan_relationships': orphan_counts,
        'prior_correction_disposition_comparison': prior_comparison,
        'transitioned_related_parent_old_dispositions': transitioned_parent_dispositions,
    }
    args.destination.parent.mkdir(parents=True, exist_ok=True)
    args.destination.write_text(json.dumps(summary, default=str, indent=2), encoding='utf-8')
    print(json.dumps({key: value for key, value in summary.items() if key not in ('files', 'reconciliation', 'correction_summary')}))


if __name__ == '__main__':
    main()
