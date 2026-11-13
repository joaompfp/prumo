"""Read-only production evidence, run inside the deployed Prumo image."""
import hashlib
import json
import sqlite3
from collections import Counter
from pathlib import Path

root = Path('/data')
result = {}
with sqlite3.connect('file:/data/prumo.sqlite3?mode=ro', uri=True) as db:
    assert db.execute('PRAGMA integrity_check').fetchall() == [('ok',)]
    assert db.execute('PRAGMA foreign_key_check').fetchall() == []
    result['integrity'] = 'ok'
    result['migrations'] = db.execute('SELECT * FROM schema_migration').fetchall()
    result['source_rows'] = db.execute('''SELECT s.name, o.kind, r.state, COUNT(*)
      FROM observation o JOIN series se ON se.id=o.series_id
      JOIN source s ON s.id=se.source_id JOIN dataset_run r ON r.id=o.dataset_run_id
      GROUP BY s.name,o.kind,r.state ORDER BY 1,2,3''').fetchall()
    result['period_extents'] = db.execute('''SELECT s.name,o.kind,MIN(o.period),MAX(o.period)
      FROM observation o JOIN series se ON se.id=o.series_id
      JOIN source s ON s.id=se.source_id GROUP BY s.name,o.kind ORDER BY 1,2''').fetchall()
    result['served_by_source'] = db.execute('''SELECT s.name, o.kind, COUNT(*)
      FROM served_observation o JOIN series se ON se.id=o.series_id
      JOIN source s ON s.id=se.source_id GROUP BY s.name,o.kind ORDER BY 1,2''').fetchall()
    forbidden = db.execute('''SELECT COUNT(*) FROM served_observation o
      JOIN series se ON se.id=o.series_id JOIN source s ON s.id=se.source_id
      WHERE s.redistribution_ok=0''').fetchone()[0]
    assert forbidden == 0
    result['licence_violations'] = forbidden
    result['run_states'] = db.execute('''SELECT s.name,r.state,COUNT(*) FROM dataset_run r
      JOIN source s ON s.id=r.source_id GROUP BY s.name,r.state ORDER BY 1,2''').fetchall()
    result['verification_totals'] = db.execute('''SELECT s.name,v.passed,SUM(v.sample_size),COUNT(*)
      FROM verification v JOIN dataset_run r ON r.id=v.dataset_run_id
      JOIN source s ON s.id=r.source_id GROUP BY s.name,v.passed ORDER BY 1,2''').fetchall()
    result['quarantines'] = db.execute('''SELECT s.name,q.reason,COUNT(*) FROM quarantine q
      JOIN dataset_run r ON r.id=q.dataset_run_id JOIN source s ON s.id=r.source_id
      GROUP BY s.name,q.reason ORDER BY 1,2''').fetchall()
    legacy = hashlib.sha256()
    legacy_count = 0
    for row in db.execute('''SELECT series_id,period,value_text,fetched_at FROM observation
      WHERE kind='legacy-unverified' ORDER BY series_id,period,value_text,fetched_at'''):
        legacy.update((json.dumps(row, ensure_ascii=False, separators=(',', ':'))+'\n').encode())
        legacy_count += 1
    result['legacy_fingerprint'] = {'rows': legacy_count, 'sha256': legacy.hexdigest()}
    checked = {}
    receipts = Counter()
    for source, sha, filename, size in db.execute('''SELECT s.name,r.sha256,r.path,r.bytes
      FROM raw_fetch r JOIN source s ON s.id=r.source_id ORDER BY r.id'''):
        path = Path(filename).resolve()
        assert path.is_relative_to((root/'raw').resolve()), 'raw path outside archive'
        assert path.name == sha
        if filename not in checked:
            with path.open('rb') as f:
                actual = hashlib.file_digest(f, 'sha256').hexdigest()
            assert actual == sha and path.stat().st_size == size, 'raw archive mismatch'
            checked[filename] = size
        receipts[source] += 1
    result['raw_receipts_by_source'] = dict(receipts)
    result['raw_unique_files_checked'] = len(checked)
    result['raw_unique_bytes_checked'] = sum(checked.values())
    envelopes = set()
    comparisons = Counter()
    for source, sha in db.execute('''SELECT s.name,i.evidence_sha256 FROM verification_item i
      JOIN verification v ON v.id=i.verification_id JOIN dataset_run r ON r.id=v.dataset_run_id
      JOIN source s ON s.id=r.source_id WHERE i.evidence_sha256 IS NOT NULL'''):
        comparisons[source] += 1
        pair = (source, sha)
        if pair not in envelopes:
            path = root/'raw'/('verify-'+source)/sha[:2]/sha
            with path.open('rb') as f:
                assert hashlib.file_digest(f, 'sha256').hexdigest() == sha
            envelopes.add(pair)
    result['verification_comparisons_with_evidence'] = dict(comparisons)
    result['verification_unique_evidence_checked'] = len(envelopes)
    result['scheduler_state'] = db.execute('''SELECT source_name,group_label,last_attempt_at,
      last_attempt_state,last_success_at,failure_streak,last_finished_at
      FROM scheduler_state ORDER BY source_name,group_label''').fetchall()
old = root/'cae-data.duckdb'
with old.open('rb') as f:
    result['legacy_db_sha256'] = hashlib.file_digest(f, 'sha256').hexdigest()
assert result['legacy_db_sha256'] == '75506bce135f3feb6c6325673426f397892e0ed68aa0a014181934fa2be58e82'
print(json.dumps(result, indent=2, sort_keys=True))
