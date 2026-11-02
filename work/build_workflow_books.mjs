import fs from 'node:fs/promises';
import path from 'node:path';
import {createHash} from 'node:crypto';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'outputs/talentra_step22_mini_seed_v7'),base=path.join(root,'outputs/talentra_step22_mentor_v6'),work=path.join(root,'work/workflow_split_v7');
const d=JSON.parse(await fs.readFile(path.join(work,'project.json'),'utf8'));
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const scalar=v=>v===null?null:typeof v==='object'?JSON.stringify(v):typeof v==='string'&&/^[=+@]/.test(v)?"'"+v:v;
const sections=[];
const add=(name,title,headers,rows)=>sections.push({name,title,headers,rows});
add('27_Mini seed versions','Two dataset versions',['Version','Purpose','Hiring journeys','Applications','Gig applications','Workflow sets','Scope'],['mini','seed'].map(v=>[v,v==='mini'?'Coverage sample for explanation':'Full saved v6 synthetic seed',d.inventory.find(f=>f.version===v&&f.dataset==='journey').rows,d.inventory.find(f=>f.version===v&&f.dataset==='application').rows,d.inventory.find(f=>f.version===v&&f.dataset==='gig').rows,27,d.core[v].selection_basis]));
add('28_Actor catalogue','27 actor contexts',['Actor ID','Actor','Kind','Parent context','Purpose','Scope','Source','Status'],d.actors.map(a=>[a.actor_id,a.actor,a.kind,a.parent_context,a.purpose,a.scope,a.source,a.status]));
add('29_Workflow catalogue','27 smaller workflows',['Workflow ID','Workflow','Group','Primary actor','Trigger','Business sequence','Step count','Participating actor IDs','Source','Status'],d.workflows.map(w=>[w.workflow_id,w.workflow,w.group,w.primary_actor,w.trigger,w.business_sequence,w.step_count,w.actor_ids.join(';'),w.source,w.status]));
add('30_Workflow steps','168 workflow operations',['Step ID','Workflow ID','Sequence','Actor ID','Actor','Action','Associated data elements','Target entity or context','Rules','Failure treatment','Source','Status','Native proof'],d.steps.map(s=>[s.step_id,s.workflow_id,s.sequence,s.actor_id,s.actor,s.action,s.data_elements,s.target_entity,s.rules,s.failure,s.source,s.status,s.native_proof]));
add('31_Category and gig rules','25 scoped business rules',['Rule ID','Rule','Domain','Predicate','Enforcement status','Source'],d.rules.map(r=>[r.rule_id,r.rule,r.domain,r.predicate,r.enforcement,r.source]));
add('32_Mini seed inventory','Saved data files',['Version','Dataset','File','Rows','Bytes','SHA256','Grain'],d.inventory.map(f=>[f.version,f.dataset,f.file,f.rows,f.bytes,f.sha256,f.grain]));
add('33_Workflow set analytics','Analytics for every workflow set',['Version','Set ID','Workflow ID','Workflow','Group','Cases','Accepted examples','Refused or duplicate','Step example rows','Defined steps','Covered steps','Proof scope'],d.analytics.map(a=>[a.version,a.set_id,a.workflow_id,a.workflow,a.group,a.case_count,a.accepted_examples,a.refused_or_duplicate,a.step_example_rows,a.defined_steps,a.covered_steps,a.scope]));
add('34_Mini seed business KPIs','Saved-file business KPIs',['Version','Metric','Numerator','Denominator','Value','Unit','Grain','Selection scope'],['mini','seed'].flatMap(v=>d.core[v].kpis.map(k=>[v,k.metric,k.numerator,k.denominator,k.value,k.unit,k.grain,d.core[v].selection_basis])));
add('35_Rule test outcomes','50 portable rule cases',['Test ID','Rule ID','Case','Expected','Actual','Result','Proof layer'],d.tests.map(t=>[t.test_id,t.rule_id,t.case,t.expected,t.actual,t.result,t.layer]));
add('36_Mini seed validation','Current split validation',['Check','Observed','Result','Proof scope'],d.checks.map(c=>[c.check,c.observed,c.result,c.scope]));
const previews=[];let tid=0;
async function sheet(wb,s){
 const sh=wb.worksheets.add(s.name);sh.showGridLines=false;sh.getRange('A2').values=[[s.title]];sh.getRange('A2').format.font={name:'Arial',size:14,color:'#203B63',bold:true};
 const last=5+s.rows.length,end=col(s.headers.length-1),rg=sh.getRange(`A5:${end}${last}`);
 rg.values=[s.headers,...s.rows.map(r=>r.map(scalar))];rg.format={font:{name:'Arial',size:10,color:'#182B43'},rowHeight:48,verticalAlignment:'top',wrapText:true};
 sh.getRange(`A5:${end}5`).format={fill:'#203B63',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},horizontalAlignment:'center',verticalAlignment:'center',rowHeight:38,wrapText:true};
 const widths=s.headers.map(h=>/^Sequence$|cases|rows|bytes|value|numerator|denominator|count|Observed|steps$|Expected|Actual/i.test(h)?18:/purpose|scope|source|predicate|action|elements|sequence|failure|proof|status|grain/i.test(h)?55:28);
 widths.forEach((w,i)=>sh.getRange(`${col(i)}5:${col(i)}${last}`).format.columnWidth=w);
 for(let i=0;i<s.rows.length;i++){
  const ht=Math.min(220,Math.max(38,...s.rows[i].map((v,j)=>Math.ceil(String(scalar(v)??'').length/(widths[j]*.9))*14+12)));
  sh.getRange(`A${i+6}:${end}${i+6}`).format.rowHeight=ht;
 }
 if(s.rows.length){const t=sh.tables.add(`A5:${end}${last}`,true,'MiniSeed_'+(++tid));t.showBandedRows=true;sh.freezePanes.freezeRows(5);if(s.headers.length>6)sh.freezePanes.freezeColumns(2);}
 for(let j=0;j<s.headers.length;j++)if(s.rows.every(r=>typeof r[j]==='number'||r[j]===null))sh.getRange(`${col(j)}6:${col(j)}${last}`).setNumberFormat(s.rows.some(r=>r[j]!==null&&!Number.isInteger(r[j]))?'0.0000':'#,##0');
 return sh;
}
async function render(wb,sh,label){const p=await wb.render({sheetName:sh.name,range:`A1:${col(Math.min(sh.getUsedRange().values[4]?.length||6,6)-1)}9`,scale:1,format:'png'});const file=path.join(work,'previews',label+'.png');await fs.writeFile(file,new Uint8Array(await p.arrayBuffer()));previews.push(file);}
await fs.mkdir(path.join(work,'previews'),{recursive:true});
const definition=[],hierarchy=[];
for(let k=0;k<sections.length;k++){
 const s=sections[k],parent='MS22.'+String(k+1).padStart(2,'0');hierarchy.push([parent,null,1,s.title,'P0','Named output section']);
 for(let j=0;j<s.headers.length;j++){
  const vals=s.rows.map(r=>r[j]),types=[...new Set(vals.filter(v=>v!==null).map(v=>typeof v==='number'?(Number.isInteger(v)?'integer':'number'):typeof v))];const type=types.length===1?types[0]:types.every(t=>['integer','number'].includes(t))?'number':'string';
  definition.push([s.title,s.headers[j],type,true,vals.some(v=>v===null),'P0','One value at the declared row grain','catalogue/mini_seed_project.json']);
  const param=parent+'.P'+(j+1);hierarchy.push([param,parent,2,s.headers[j],'P0','Parameter at declared row grain']);hierarchy.push([param+'.C',param,3,'Value contract','P0','Typed value and required property']);hierarchy.push([param+'.M',param,3,'Meaning and lineage','P0','Source and interpretation recorded']);for(const [code,value] of [['type',type],['required','Required property'],['null',vals.some(v=>v===null)?'Null permitted':'Non-null'],['source','catalogue/mini_seed_project.json']])hierarchy.push([param+'.'+code,param+(code==='source'?'.M':'.C'),4,value,'P0','Atomic property']);
 }
}
const additions={schema:[{name:'Mini Seed Definition',title:'Mini/seed output schema extension',headers:['L1 Section','L2 Parameter','Type','Required','Nullable','Priority','Meaning','Source'],rows:definition},{name:'Mini Seed Hierarchy',title:'Mini/seed L1 to L4',headers:['Node ID','Parent ID','Level','Name or value','Priority','Definition'],rows:hierarchy}],scorecard:[{name:'Mini Seed Evidence',title:'Observed coverage with unchanged prior ratings',headers:['Measure','Observed','Required','Coverage','Evidence boundary'],rows:[['Actor contexts',27,27,null,'18 retained + 9 proposed'],['Workflow steps',168,168,null,'116 retained + 52 proposed'],['Workflow sets',54,54,null,'27 per version'],['Portable rule examples',50,50,null,'25 valid + 25 refusal'],['Unique step example coverage',168,168,null,'Documentary payload examples, not native execution'],['Seed fingerprints',5,5,null,'Match prior v6 bytes'],['Independent reviewer',0,1,null,'Pending, no acceptance claim'],['Human interview',0,1,null,'Pending, no acceptance claim']]}]};
const contract=JSON.parse(await fs.readFile(path.join(out,'artifact_contracts/step_22_output.json'),'utf8'));
for(const s of sections){const properties={};s.headers.forEach((h,j)=>{const vals=s.rows.map(r=>r[j]),types=[...new Set(vals.map(v=>v===null?'null':typeof v==='number'?(Number.isInteger(v)?'integer':'number'):typeof v==='object'?'string':typeof v))];properties[h]={type:types};});contract.properties[s.title]={type:'array',items:{type:'object',properties,required:s.headers,additionalProperties:false}};if(!contract.required.includes(s.title))contract.required.push(s.title);}
const contractText=JSON.stringify(contract,null,2),contractHash=createHash('sha256').update(contractText).digest('hex');
await fs.writeFile(path.join(out,'artifact_contracts/step_22_output.json'),contractText);
const files=[['schema','steps/22_Integration_and_Source_Mapping/a_Output_Schema_Definition.xlsx'],['scorecard','steps/22_Integration_and_Source_Mapping/b_Schema_Rating_Scorecard.xlsx'],['output','steps/22_Integration_and_Source_Mapping/c_Output_Document.xlsx'],['combined','Talentra_Combined.xlsx']];
const report=[];
for(const [kind,rel] of files){
 if(process.argv.includes('--combined-only')&&kind!=='combined')continue;
 console.log('Opening '+kind);const wb=kind==='combined'?Workbook.create():await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(base,rel)));
 console.log('Loaded '+kind);
 if(kind==='combined'){
  const old=JSON.parse(await fs.readFile(path.join(root,'work/release_v6/dashboard_data.json'),'utf8'));
  await fs.mkdir(path.join(out,'prior_v6'),{recursive:true});await fs.copyFile(path.join(base,'Talentra_Combined.xlsx'),path.join(out,'prior_v6/Talentra_Combined.xlsx'));
  const summary=await sheet(wb,{name:'Combined Rating',title:'Lifecycle rating and mini/seed extension',headers:['Measure','Value','Scope'],rows:[['Prior full project score',old.combinedRating,'Carried-forward v6 rating'],['Prior documentary score',old.documentaryRating,'Supplementary measure'],['Workflow actors',27,'18 retained + 9 proposed'],['Workflow operations',168,'116 retained + 52 proposed'],['Workflow sets',54,'27 per version'],['Independent review of v7',null,'Pending'],['Archived full v6 master','prior_v6/Talentra_Combined.xlsx','Preserved byte-for-byte']]});
  await render(wb,summary,'combined_summary');
  await sheet(wb,{name:'Ratings',title:'Prior v6 deliverable ratings',headers:['Step','Deliverable','Full score','Documentary score','Status'],rows:old.steps.flatMap(s=>['Output Schema Definition','Schema Rating Scorecard','Output Document'].map((name,i)=>[s.number,name,s.deliverableScores[i],s.documentaryScores[i],'Carried forward. New extension review pending.']))});
  const records=old.steps.flatMap(s=>s.sections.flatMap(section=>section.rows.map((r,i)=>[s.number,section.name,i+1,JSON.stringify(section.columns),JSON.stringify(r)])));
  records.push(...sections.flatMap(section=>section.rows.map((r,i)=>[22,'Mini Seed / '+section.title,i+1,JSON.stringify(section.headers),JSON.stringify(r)])));
  const sh=await sheet(wb,{name:'All Outputs',title:'All 22 steps, concatenated with mini/seed extension',headers:['Step','Section','Record','Field names JSON','Values JSON'],rows:records});
  sh.getRange(`D5:E${records.length+5}`).format.columnWidth=90;sh.getRange(`A6:E${records.length+5}`).format.rowHeight=38;
  report.push({file:rel,concatenated_records:records.length,archive:'prior_v6/Talentra_Combined.xlsx'});
 }
 const list=kind==='schema'?additions.schema:kind==='scorecard'?additions.scorecard:sections;
 if(kind==='output'||kind==='combined'){
  for(const s of sections){const sh=await sheet(wb,s);if(kind!=='combined')await render(wb,sh,kind+'_'+s.name);}
 }else for(const s of list){const sh=await sheet(wb,s);if(kind==='scorecard')for(let r=6;r<=13;r++){sh.getRange(`D${r}`).formulas=[[`=B${r}/C${r}`]];sh.getRange(`D${r}`).setNumberFormat('0.0%');}await render(wb,sh,kind+'_'+s.name);}
 if(kind==='schema')wb.worksheets.getItem('Artifact Contracts').getRange('D8:E8').values=[[contractHash,'v7 extension: retained sections plus ten mini/seed sections']];
 wb.recalculate();
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:5},maxChars:900});
 if(/"address"/.test(errors.ndjson||''))throw Error(errors.ndjson);
 await(await SpreadsheetFile.exportXlsx(wb)).save(path.join(out,rel));
 report.push({file:rel,added_tabs:list.length,formula_errors:0});console.log('Saved '+kind);
}
await fs.writeFile(path.join(work,'book_validation.json'),JSON.stringify(report,null,2));
await fs.writeFile(path.join(work,'previews.json'),JSON.stringify(previews,null,2));
// One output contract includes all retained v6 sections plus the new mini/seed sections.
await fs.writeFile(path.join(work,'added_sections.json'),JSON.stringify(sections,null,2));
console.log('Four workbooks and the Step 22 output contract updated');
