"""Read-only validation of the delivered contract subset and workbook changes."""
import json,zipfile,xml.etree.ElementTree as E,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'outputs/talentra_step22_mini_seed_v7';BASE=ROOT/'outputs/talentra_step22_mentor_v6'
def load(p):return json.loads(Path(p).read_text(encoding='utf-8'))
def contract(record,spec):
 if not isinstance(record,dict):return False
 if set(record)!=set(spec['required']):return False
 for k,p in spec['properties'].items():
  v=record[k];t='null' if v is None else 'boolean' if type(v)==bool else 'integer' if type(v)==int else 'number' if type(v)==float else 'object' if type(v)==dict else 'array' if type(v)==list else 'string'
  types=p['type'] if isinstance(p['type'],list) else [p['type']]
  if t not in types:return False
 return True
def xmlbook(p):
 ns={'a':'http://schemas.openxmlformats.org/spreadsheetml/2006/main','r':'http://schemas.openxmlformats.org/officeDocument/2006/relationships'}
 z=zipfile.ZipFile(p);strings=[]
 if 'xl/sharedStrings.xml' in z.namelist():
  for e in E.fromstring(z.read('xl/sharedStrings.xml')).findall('a:si',ns):strings.append(''.join(t.text or '' for t in e.iter('{'+ns['a']+'}t')))
 rel={e.attrib['Id']:e.attrib['Target'] for e in E.fromstring(z.read('xl/_rels/workbook.xml.rels'))}
 result={}
 for s in E.fromstring(z.read('xl/workbook.xml')).findall('a:sheets/a:sheet',ns):
  target=rel[s.attrib['{'+ns['r']+'}id']];target=target.lstrip('/') if target.startswith('/') else 'xl/'+target
  cells={}
  for c in E.fromstring(z.read(target)).iter('{'+ns['a']+'}c'):
   f=c.find('a:f',ns);v=c.find('a:v',ns);typ=c.attrib.get('t')
   if f is not None:value=('formula',f.text)
   elif typ=='s':value=('string',strings[int(v.text)]) if v is not None else None
   elif typ=='inlineStr':value=('string',''.join(t.text or '' for t in c.iter('{'+ns['a']+'}t')))
   elif v is not None:
    try:value=('number',float(v.text)) if typ!='b' else ('bool',v.text=='1')
    except (TypeError,ValueError):value=('string',v.text)
   else:value=None
   if value is not None:cells[c.attrib['r']]=value
  result[s.attrib['name']]=cells
 z.close();return result
def main():
 d=load(OUT/'catalogue/mini_seed_project.json');checks=[]
 for kind,key in [('actor','actors'),('workflow_step','steps')]:
  spec=load(OUT/'contracts'/f'{kind}.schema.json')
  for row in d[key]:assert contract(row,spec)
  missing=dict(d[key][0]);del missing[spec['required'][0]];assert not contract(missing,spec)
  wrong={**d[key][0],spec['required'][0]:123};assert not contract(wrong,spec)
  extra={**d[key][0],'undeclared':True};assert not contract(extra,spec)
  checks.append({'contract':kind,'records':len(d[key]),'negative_checks':3,'result':'PASS','scope':'Complete declared subset: exact required keys, additional-properties refusal and scalar type unions'})
 files=['steps/22_Integration_and_Source_Mapping/'+n for n in ['a_Output_Schema_Definition.xlsx','b_Schema_Rating_Scorecard.xlsx','c_Output_Document.xlsx']]+['Talentra_Combined.xlsx']
 for rel in files:
  if rel=='Talentra_Combined.xlsx':
   new=xmlbook(OUT/rel);count=sum(1 for a in new['All Outputs'] if a.startswith('A'))-2
   assert count>=20231,(count,len(new['All Outputs']))
   assert len(new)==13
   assert hashlib.sha256((BASE/rel).read_bytes()).digest()==hashlib.sha256((OUT/'prior_v6'/rel).read_bytes()).digest()
   source=load(ROOT/'work/release_v6/dashboard_data.json');expected=[(s['number'],sec['name'],i+1,sec['columns'],r) for s in source['steps'] for sec in s['sections'] for i,r in enumerate(sec['rows'])]
   for i,(number,section,record,columns,row) in enumerate(expected,6):
    assert new['All Outputs'][f'A{i}'][1]==number and new['All Outputs'][f'B{i}'][1]==section and new['All Outputs'][f'C{i}'][1]==record
    assert json.loads(new['All Outputs'][f'D{i}'][1])==columns and json.loads(new['All Outputs'][f'E{i}'][1])==row
   checks.append({'file':rel,'concatenated_records':count,'archived_original_sha256_match':True,'new_tabs':len(new),'result':'PASS'})
   continue
  old=xmlbook(BASE/rel);new=xmlbook(OUT/rel);same=0
  for name,cells in old.items():
   assert name in new
   for address,value in cells.items():
    if name=='Artifact Contracts' and address in ['D8','E8'] and rel.endswith('a_Output_Schema_Definition.xlsx'):continue
    if name=='Artifact Contracts' and address in ['D71','E71'] and rel=='Talentra_Combined.xlsx':continue
    assert new[name].get(address)==value,(rel,name,address,value,new[name].get(address))
    same+=1
  checks.append({'file':rel,'preserved_cells':same,'old_tabs':len(old),'new_tabs':len(new),'result':'PASS'})
  if rel.endswith('c_Output_Document.xlsx'):assert len([k for k in new if k.startswith('30_')])==1 and len(new['30_Workflow steps'])>168*10
 for f in (BASE/'steps').glob('*/*.xlsx'):
  if not f.parent.name.startswith('22_'):assert hashlib.sha256(f.read_bytes()).digest()==hashlib.sha256((OUT/f.relative_to(BASE)).read_bytes()).digest()
 assert all(any(a['actor_id'] in w['actor_ids'] for w in d['workflows']) for a in d['actors'])
 (OUT/'evidence/mini_seed_saved_artifacts.json').write_text(json.dumps(checks,indent=2),encoding='utf-8')
 print(json.dumps(checks,indent=2))
if __name__=='__main__':main()
