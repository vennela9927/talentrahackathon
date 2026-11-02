"""Compare dictionary_v2.json with a psql --csv information_schema export."""
import csv,json,sys
from pathlib import Path
if len(sys.argv)!=3:raise SystemExit('Usage: python check_dictionary.py dictionary_v2.json metadata.csv')
dictionary=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'))
rows=list(csv.DictReader(Path(sys.argv[2]).read_text(encoding='utf-8-sig').splitlines()))
actual={(r['table_name'],r['column_name']):r for r in rows}
expected={(a['table'],a['column']):a for a in dictionary};issues=[]
for key,a in expected.items():
 r=actual.get(key)
 if r is None:issues.append([*key,'Missing physical column']);continue
 kind=a['type'].split('(')[0]
 types={'varchar':'character varying','char':'character','timestamptz':'timestamp with time zone','integer':'integer','bigint':'bigint','smallint':'smallint','boolean':'boolean','date':'date','text':'text','numeric':'numeric'}
 if r['data_type']!=types[kind]:issues.append([*key,'Type differs'])
 if (r['is_nullable']=='YES')!=a['nullable']:issues.append([*key,'Nullability differs'])
 if kind in ['varchar','char'] and r.get('character_maximum_length')!=a['type'].split('(')[1][:-1]:issues.append([*key,'Length differs'])
 if kind=='numeric':
  precision,scale=a['type'].split('(')[1][:-1].split(',')
  if r.get('numeric_precision')!=precision or r.get('numeric_scale')!=scale:issues.append([*key,'Precision or scale differs'])
for key in actual.keys()-expected.keys():issues.append([*key,'Unexpected physical column'])
print(json.dumps({'mismatches':issues,'expected_columns':len(expected),'actual_columns':len(actual)},indent=2))
raise SystemExit(bool(issues))
