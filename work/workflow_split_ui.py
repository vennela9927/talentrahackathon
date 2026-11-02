"""Add the mini/seed review view to the existing offline dashboard."""
from pathlib import Path
import json
import base64,re
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs/talentra_step22_mini_seed_v7'
source=(ROOT/'outputs/talentra_step22_mentor_v6/index.html').read_text(encoding='utf-8')
data=json.loads((ROOT/'work/workflow_split_v7/project.json').read_text(encoding='utf-8'))
match=re.search(r'(<script type="application/json" id="dataset">)(.*?)(</script>)',source,re.S)
legacy=json.loads(match.group(2))
for rel in ['Talentra_Combined.xlsx','steps/22_Integration_and_Source_Mapping/a_Output_Schema_Definition.xlsx','steps/22_Integration_and_Source_Mapping/b_Schema_Rating_Scorecard.xlsx','steps/22_Integration_and_Source_Mapping/c_Output_Document.xlsx','artifact_contracts/step_22_output.json']:
 legacy['downloads'][rel]=base64.b64encode((OUT/rel).read_bytes()).decode('ascii')
sections=json.loads((ROOT/'work/workflow_split_v7/added_sections.json').read_text(encoding='utf-8'))
for section in sections:
 legacy['steps'][21]['sections'].append({'name':'Mini Seed / '+section['title'],'columns':section['headers'],'rows':section['rows'],'priority':'P0','source':'Mini/seed v7. Proposed additions and portable fixtures only.'})
for i,section in enumerate(sections,1):
 parent=f'MS22.{i:02}'
 legacy['schema_nodes'].append([22,parent,None,1,section['title'],'P0','Mini/seed output section at its stated grain','v7 mini/seed catalogue'])
 for j,h in enumerate(section['headers'],1):
  node=parent+f'.P{j}';vals=[r[j-1] for r in section['rows']];nonnull=[v for v in vals if v is not None]
  typ='boolean' if nonnull and all(type(v)==bool for v in nonnull) else 'integer' if nonnull and all(type(v)==int for v in nonnull) else 'number' if nonnull and all(type(v) in [int,float] for v in nonnull) else 'string'
  nullable=any(v is None for v in vals)
  meaning=f'{h} at the declared grain of {section["title"]}. Read with its source, version and evidence boundary.'
  legacy['schema_fields'].append([22,section['title'],h,'Value contract;Meaning and lineage',typ,'Required property; null permitted' if nullable else 'Required non-null property','Declared scalar type and exact required field set',meaning,'Needed to interpret the smaller workflow set','P0','v7 mini/seed catalogue',node])
  legacy['schema_nodes'] += [[22,node,parent,2,h,'P0',meaning,'v7 mini/seed catalogue'],[22,node+'.C',node,3,'Value contract','P0','Declared value type and requiredness','v7 mini/seed catalogue'],[22,node+'.M',node,3,'Meaning and lineage','P0',meaning,'v7 mini/seed catalogue'],[22,node+'.T',node+'.C',4,typ,'P0','Scalar data type','v7 mini/seed catalogue'],[22,node+'.N',node+'.C',4,'Null permitted' if nullable else 'Non-null','P0','Required property and nullable value are distinct','v7 mini/seed catalogue'],[22,node+'.S',node+'.M',4,'catalogue/mini_seed_project.json','P0','Source lineage','v7 mini/seed catalogue']]
  legacy['schema_nodes'].append([22,node+'.R',node+'.C',4,'Required property','P0','Property must be present even when its value permits null','v7 mini/seed catalogue'])
legacy['steps'][21]['version']='7.0 mini and seed addendum; v6 ratings carried forward'
legacy['version']='7.0 mini and seed addendum'
payload=json.dumps(legacy,ensure_ascii=True,separators=(',',':')).replace('</','<\\/')
source=source[:match.start(2)]+payload+source[match.end(2):]
source=source.replace('<nav aria-label="Project views">','<nav aria-label="Project views"><button data-view="sets">Mini and seed</button>')
panel='''<section class="panel" id="sets"><div class="top"><div><div class="eyebrow">Step 22 · workflow-defined data sets · 1 November 2026</div><h1>Mini examples. Full seed data.</h1><p class="intro">Review the 27 actor contexts and 168 workflow steps, grouped into eight smaller business areas. Choose a version, workflow and actor to inspect its data, rules and results.</p></div><a class="button primary" href="README.md">Read the guide</a></div>
<div class="metrics"><div class="metric featured"><label>Actor contexts</label><strong>27</strong><p>18 retained + 9 proposed contexts</p></div><div class="metric"><label>Workflow operations</label><strong>168</strong><p>116 retained + 52 proposed steps</p></div><div class="metric"><label>Smaller workflow sets</label><strong>54</strong><p>27 workflows in each version</p></div><div class="metric"><label>Full seed journeys</label><strong>15,00,000</strong><p>Synthetic candidate-job journeys</p></div></div>
<div class="notice"><b>Two different uses.</b> Mini is a linked coverage sample for explaining and checking the design. Seed preserves the existing 15-lakh synthetic cohort. The 168 operations are workflow steps within the project, not 168 lifecycle stages. Added actors and steps remain proposals. Native SQL, endpoint authorization, providers and load tests remain open.</div>
<div class="filters"><select id="v7version" aria-label="Dataset version"><option value="mini">Mini version</option><option value="seed">Seed version</option></select><select id="v7group" aria-label="Workflow group"></select><select id="v7workflow" aria-label="Workflow set"></select><select id="v7actor" aria-label="Actor context"></select><button class="button" id="v7reset">Reset filters</button></div>
<div class="actions"><a class="button" href="steps/22_Integration_and_Source_Mapping/a_Output_Schema_Definition.xlsx" download>Updated schema Excel</a><a class="button" href="steps/22_Integration_and_Source_Mapping/b_Schema_Rating_Scorecard.xlsx" download>Updated scorecard Excel</a><a class="button" href="steps/22_Integration_and_Source_Mapping/c_Output_Document.xlsx" download>Updated output Excel</a><a class="button" href="Talentra_Combined.xlsx" download>Combined Excel</a></div>
<div class="actions" style="margin-top:14px"><a class="button" href="#v7actors">Actor catalogue</a><a class="button" href="#v7steps">Workflow steps</a><a class="button" href="#v7rules">Business rules</a><a class="button" href="#v7family">Business analytics</a><a class="button" href="catalogue/field_examples.json" download>Field examples</a></div>
<h2>Selected workflow and its data</h2><div class="card pad" id="v7detail"></div><div class="card scroll tablebox" id="v7setrows" style="margin-top:14px"></div>
<h2>Smaller workflow-set analytics</h2><p class="muted">Counts below describe portable example envelopes. Accepted means an example passed the envelope guard. It does not mean the business workflow ran in a database.</p><div class="card scroll tablebox" id="v7metrics"></div>
<h2>Business data files for this version</h2><div id="v7basis" class="notice"></div><div class="card scroll" id="v7files"></div>
<h2>Business analytics by job family</h2><div class="card scroll" id="v7family"></div><div class="actions" id="v7familylinks" style="margin-top:14px"></div><h2>Hiring and gig KPIs for this version</h2><div class="card scroll" id="v7kpis"></div>
<h2>27 actor contexts and access boundaries</h2><p class="muted">External providers and business subroles are contexts, not newly deployed RBAC roles. Requester is the existing gig requester persona.</p><div class="card scroll tablebox" id="v7actors"></div>
<h2>168 workflow steps and associated data elements</h2><div class="filters"><input id="v7search" aria-label="Search workflow steps" placeholder="Search a step, action, field or rule"><button class="button" id="v7export">Export visible steps CSV</button></div><div class="card scroll tablebox" id="v7steps"></div><p class="muted small" id="v7stepcount"></p>
<h2>Job-category and gig-fulfilment rules</h2><p class="muted">Collar, business branch and function resolve from the versioned family. Engagement is a separate axis. Gig applications run from worker to requester. The external provider owns fulfilment and earnings. Ratings require completed work and the owning requester.</p><div class="card scroll tablebox" id="v7rules"></div>
<h2>Validation and review status</h2><div class="card scroll" id="v7checks"></div><p class="muted">Prior Step 22 full score 82.9 and documentary score 97.7 are carried forward from v6. This extension has no new independent or human rating. The prior lifecycle and evidence views remain accessible above.</p></section>'''
source=source.replace('<main>','<main>'+panel,1)
# The full saved v6 files now live once, under seed/core. Small v6 summaries remain in scenario_data.
source=source.replace('href="scenario_data/${esc(v.file)}"','href="seed/core/${esc(v.file)}"')
source=source.replace('Mentor update 6.0 · Prepared 30 October 2026','Mini and seed update 7.0 · Prepared 1 November 2026')
encoded=json.dumps(data,ensure_ascii=True,separators=(',',':')).replace('</','<\\/')
script='''
const V7=__V7__,v7esc=esc;
function v7grid(cols,rows){return '<table><thead><tr>'+cols.map(c=>'<th>'+esc(c)+'</th>').join('')+'</tr></thead><tbody>'+rows.map(r=>'<tr>'+r.map(c=>'<td>'+esc(c===null?'Not applicable':c)+'</td>').join('')+'</tr>').join('')+'</tbody></table>'}
const vg=$('v7group'),vw=$('v7workflow'),va=$('v7actor'),vv=$('v7version');
vg.innerHTML='<option value="">All eight groups</option>'+[...new Set(V7.workflows.map(w=>w.group))].map(g=>'<option>'+esc(g)+'</option>').join('');
va.innerHTML='<option value="">All 27 actors</option>'+V7.actors.map(a=>'<option value="'+a.actor_id+'">'+esc(a.actor)+'</option>').join('');
function v7options(){const prior=vw.value;const list=V7.workflows.filter(w=>(!vg.value||w.group===vg.value)&&(!va.value||w.actor_ids.includes(va.value)));vw.innerHTML='<option value="">All matching workflows</option>'+list.map(w=>'<option value="'+w.workflow_id+'">'+w.workflow_id+' · '+esc(w.workflow)+'</option>').join('');if(list.some(w=>w.workflow_id===prior))vw.value=prior;v7render()}
function v7selected(){return V7.workflows.filter(w=>(!vg.value||w.group===vg.value)&&(!vw.value||w.workflow_id===vw.value)&&(!va.value||w.actor_ids.includes(va.value)))}
let v7visible=[];
function v7render(){const version=vv.value,selected=v7selected(),ids=new Set(selected.map(w=>w.workflow_id)),core=V7.core[version],metric=V7.analytics.filter(a=>a.version===version&&ids.has(a.workflow_id));
 const w=selected.length===1?selected[0]:null;
 $('v7detail').innerHTML=w?'<h3>'+w.workflow_id+' · '+esc(w.workflow)+'</h3><p>'+esc(w.business_sequence)+'</p><p class="muted">'+esc(w.status)+' · '+w.step_count+' defined steps · '+esc(w.group)+'</p><div class="actions"><a class="button" href="'+version+'/workflows/'+w.workflow_id+'/manifest.json" download>Set manifest</a><a class="button" href="'+version+'/workflows/'+w.workflow_id+'/cases.json" download>Generated cases</a><a class="button" href="'+version+'/workflows/'+w.workflow_id+'/step_examples.json" download>Step examples</a><a class="button" href="'+version+'/workflows/'+w.workflow_id+'/analytics.json" download>Set analytics</a></div>':'<h3>'+selected.length+' matching workflows</h3><p>Select one workflow for its sequence, generated cases, step examples and analytics downloads.</p>';
 $('v7setrows').innerHTML=v7grid(['Workflow','Business group','Defined steps','Origin'],selected.map(w=>[w.workflow_id+' '+w.workflow,w.group,w.step_count,w.status]));
 $('v7metrics').innerHTML=v7grid(['Set','Cases','Accepted examples','Refused / duplicate','Emitted step examples','Defined steps covered'],metric.map(m=>[m.set_id,m.case_count,m.accepted_examples,m.refused_or_duplicate,m.step_example_rows,m.covered_steps+'/'+m.defined_steps]));
 $('v7basis').textContent=core.selection_basis;
 const inventory=V7.inventory.filter(f=>f.version===version);$('v7files').innerHTML='<table><thead><tr><th>File</th><th>Saved rows</th><th>Grain</th></tr></thead><tbody>'+inventory.map(f=>'<tr><td><a href="'+f.file+'" download>'+esc(f.dataset)+'.csv.gz</a></td><td>'+fmt(f.rows)+'</td><td>'+esc(f.grain)+'</td></tr>').join('')+'</tbody></table>';
 $('v7family').innerHTML=v7grid(['Family','Journeys','Applied','Selected','Offered','Accepted','Onboarded'],Object.entries(core.families).map(([f,m])=>[f,...['journeys','applied','selected','offered','accepted','onboarded'].map(k=>fmt(m[k]||0))]));
 $('v7kpis').innerHTML=v7grid(['Metric','Numerator','Denominator','Result','Grain'],core.kpis.map(k=>[k.metric,k.numerator,k.denominator,k.value===null?'Not applicable':k.unit==='ratio'?(k.value*100).toFixed(1)+'%':k.value.toFixed(2)+' calendar days',k.grain]));
 $('v7actors').innerHTML=v7grid(['Actor ID','Actor','Kind','Purpose','Scope','Status'],V7.actors.filter(a=>!va.value||a.actor_id===va.value).map(a=>[a.actor_id,a.actor,a.kind,a.purpose,a.scope,a.status]));
 const query=$('v7search').value.toLowerCase();v7visible=V7.steps.filter(s=>ids.has(s.workflow_id)&&(!query||JSON.stringify(s).toLowerCase().includes(query)));
 $('v7steps').innerHTML=v7grid(['Step','Workflow','Primary actor','Action','Associated data elements','Rules','Status'],v7visible.map(s=>[s.step_id,s.workflow_id,s.actor,s.action,s.data_elements,s.rules,s.status]));$('v7stepcount').textContent=v7visible.length+' visible of 168 defined steps. Actor filtering shows participating workflows and preserves their primary owners. Native execution remains pending.';
 $('v7familylinks').innerHTML=Object.keys(core.families).map(f=>'<a class="button" href="'+version+'/sets/'+f+'/analytics.json" download>'+esc(f)+' set analytics</a>').join('');
 $('v7rules').innerHTML=v7grid(['Rule','Domain','Business condition','Predicate','Evidence scope'],V7.rules.map(r=>[r.rule_id,r.domain,r.rule,r.predicate,r.enforcement]));
 $('v7checks').innerHTML=v7grid(['Check','Observed','Result','Proof scope'],V7.checks.map(c=>[c.check,c.observed,c.result,c.scope]));
}
vg.onchange=v7options;va.onchange=v7options;vw.onchange=v7render;vv.onchange=v7render;$('v7search').oninput=v7render;
$('v7reset').onclick=()=>{vg.value='';va.value='';vw.value='';$('v7search').value='';v7options()};
$('v7export').onclick=()=>{const cols=['step_id','workflow_id','actor','action','data_elements','rules','status'];const quote=x=>'"'+String(x??'').replaceAll('"','""')+'"';const body=[cols,...v7visible.map(s=>cols.map(k=>s[k]))].map(r=>r.map(quote).join(',')).join('\\r\\n');const u=URL.createObjectURL(new Blob(['\\ufeff'+body],{type:'text/csv;charset=utf-8'}));const a=document.createElement('a');a.href=u;a.download='Talentra_workflow_steps_'+vv.value+'.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),1000)};
v7options();nav('sets');
'''.replace('__V7__',encoded)
source=source.replace('</script></body></html>',script+'</script></body></html>')
# Addendum workbook files use normal relative links. Preserve the original embedded snapshot downloads in the legacy views.
(OUT/'index.html').write_text(source,encoding='utf-8')
print('Built mini/seed UI with the original dashboard retained')
