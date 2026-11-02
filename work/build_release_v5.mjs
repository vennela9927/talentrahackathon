import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const root=path.resolve(import.meta.dirname,'..'),work=path.join(root,process.argv.find(a=>a.startsWith('--work='))?.slice(7)||'work/release_v5');
const d=JSON.parse(await fs.readFile(path.join(work,'project_data.json'),'utf8'));
const out=path.join(root,'outputs',d.output_folder),previewDir=path.join(work,'previews');
if(process.argv.includes('--mentor-polish')){
 const sec=d.steps[21].sections.find(s=>s.name==='Business KPI register'),index=d.steps[21].sections.indexOf(sec)+1;
 const file=path.join(out,d.steps[21].files.output),book=await SpreadsheetFile.importXlsx(await FileBlob.load(file));
 const sheet=book.worksheets.getItem(String(index).padStart(2,'0')+'_'+sec.name);
 sheet.getRange('A6:L23').values=sec.rows;sheet.getRange('C5:C23').format.columnWidth=68;sheet.getRange('A6:L23').format.rowHeight=120;
 book.recalculate();const png=await book.render({sheetName:sheet.name,range:'A1:F8',scale:1,format:'png'});await fs.writeFile(path.join(work,'kpi_definitions.png'),new Uint8Array(await png.arrayBuffer()));await(await SpreadsheetFile.exportXlsx(book)).save(file);
 const mf=path.join(out,'Talentra_Combined.xlsx'),master=await SpreadsheetFile.importXlsx(await FileBlob.load(mf));let cursor=6,start;
 for(const s of d.steps)for(const section of s.sections){if(s.number===22&&section.name===sec.name)start=cursor;cursor+=section.rows.length;}
 const output=master.worksheets.getItem('All Outputs');output.getRange(`D${start}:O${start+17}`).values=sec.rows;output.getRange(`A${start}:X${start+17}`).format.rowHeight=120;
 master.recalculate();for(const w of [book,master]){const er=await w.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#NUM!',options:{useRegex:true,maxResults:3},maxChars:600});if(/"address"/.test(er.ndjson||''))throw Error(er.ndjson);}
 if(Math.abs(master.worksheets.getItem('Combined Rating').getRange('B4').values[0][0]-d.combinedRating)>1e-8)throw Error('Score changed during definition edits');
 await(await SpreadsheetFile.exportXlsx(master)).save(mf);console.log('KPI definitions synchronized; full rating unchanged');process.exit(0);
}
await fs.mkdir(previewDir,{recursive:true});
const kinds=['Output Schema Definition','Schema Rating Scorecard','Output Document'];
const col=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const literal=v=>v===null?'PENDING / NULL - see field contract':typeof v==='object'?JSON.stringify(v):typeof v==='string'&&v.startsWith('=')?"'"+v:v;
const onlyArg=process.argv.find(a=>a.startsWith('--only='));
const only=onlyArg?new Set(onlyArg.slice(7).split(',').map(Number)):null;
const prior=only?JSON.parse(await fs.readFile(path.join(out,'evidence/prior_workbook_validation.json'),'utf8')):null;
const changed=new Set(only?d.steps.filter(s=>only.has(s.number)).flatMap(s=>Object.values(s.files)):[]);changed.add('Talentra_Combined.xlsx');
const previews=[],checks=prior?prior.checks.filter(c=>!changed.has(c.file)):[];let tableNo=0;
const ratingHeads=['Step','Deliverable','Dimension','Weight','Critical','Measure','Score /5','Contribution','Evidence','Return stage'];
const fieldHeads=['Step','L1 Section','L2 Parameter','L3 facets','L4 Data type','Required','Validation','Definition','Reason','Priority','Source','Node ID'];
const hierarchyHeads=['Step','Node ID','Parent ID','Level','Name','Priority','Definition','Source'];
const sectionHeads=['Step','Section','Level','Priority','Priority weight','Structure /5','Documentary fill /5','Definition source /5','Evidence readiness /5','Rating /5','Basis'];
const closureHeads=['Step','Deliverable','Current full score','Documentary score','Gap to90','Required evidence','Conditional target','Target status','Release boundary'];
function table(wb,name,title,headers,rows,{start=5,inputs=[],compact=false}={}){
 const sh=wb.worksheets.add(name.replace(/[\[\]:*?/\\]/g,' ').slice(0,31)),end=col(headers.length-1),last=start+rows.length;
 sh.showGridLines=false;sh.getRange('A2').values=[[title]];sh.getRange('A2').format.font={name:'Arial',size:14,bold:true,color:'#203B63'};
 const used=sh.getRange(`A${start}:${end}${Math.max(start+1,last)}`);
 used.format={font:{name:'Arial',size:10,color:'#162A43'},verticalAlignment:'top',wrapText:true,rowHeight:compact?40:62};
 sh.getRange(`A${start}:${end}${start}`).values=[headers];sh.getRange(`A${start}:${end}${start}`).format={fill:'#203B63',font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:42,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true,borders:{insideVertical:{style:'thin',color:'#FFFFFF'}}};
 const widths=[];
 for(let j=0;j<headers.length;j++){
  const h=headers[j],width=/^Step$|^Level$|^Weight$|^Critical$|score|Rating|Nullable|^Change$|Priority weight/i.test(h)?16:/Evidence|Definition|Meaning|Reason|Treatment|Acceptance|Required evidence|Expected|Validation|Question|Response|Basis/i.test(h)?58:/^Priority$/.test(h)?12:32;
  widths.push(width);sh.getRange(`${col(j)}${start}:${col(j)}${Math.max(start+1,last)}`).format.columnWidth=width;
 }
 if(rows.length){
  sh.getRange(`A${start+1}:${end}${last}`).values=rows.map(r=>r.map(literal));
  const heights=rows.map(r=>Math.max(compact?28:36,Math.min(400,Math.ceil((Math.max(...r.map((v,j)=>String(literal(v)).split('\n').reduce((a,t)=>a+Math.max(1,Math.ceil(t.length/(widths[j]*.9))),0)))*13.5+10)/6)*6)));
  let first=0;for(let i=1;i<=heights.length;i++)if(i===heights.length||heights[i]!==heights[first]){sh.getRange(`A${start+first+1}:${end}${start+i}`).format.rowHeight=heights[first];first=i;}
  const t=sh.tables.add(`A${start}:${end}${last}`,true,'Lifecycle_'+(++tableNo));t.showBandedRows=true;
  for(let j=0;j<headers.length;j++)if(rows.every(r=>typeof r[j]==='number')){sh.getRange(`${col(j)}${start+1}:${col(j)}${last}`).setNumberFormat(/rate|share|conversion|completion|acceptance/i.test(headers[j])&&rows.every(r=>r[j]>=0&&r[j]<=1)?'0.0%':/score|rating|contribution|change|gap|target/i.test(headers[j])?'0.0':rows.some(r=>!Number.isInteger(r[j]))?'#,##0.00':'#,##0');}
  sh.freezePanes.freezeRows(start);if(headers.length>6)sh.freezePanes.freezeColumns(2);
 }
 for(const j of inputs)if(rows.length)sh.getRange(`${col(j)}${start+1}:${col(j)}${last}`).format.fill='#FFF1D6';
 return sh;
}
function scores(wb,rows){
 const sh=table(wb,'Ratings','Rating inputs and evidence',ratingHeads,rows,{inputs:[6]});
 sh.getRange(`G6:G${rows.length+5}`).dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
 sh.getRange(`H6:H${rows.length+5}`).formulas=rows.map((_,i)=>[`=IF(ISNUMBER(G${i+6}),D${i+6}*G${i+6}/5,"Missing score")`]);return sh;
}
function levelRatings(wb,rows){const sh=table(wb,'Section Ratings','Section priorities and L1-L4 scores',sectionHeads,rows);sh.getRange(`J6:J${rows.length+5}`).formulas=rows.map((_,i)=>[`=AVERAGE(F${i+6}:I${i+6})`]);return sh;}
function groupFormulas(a,z,doc=false){
 const count=`COUNT(Ratings!G${a}:G${z})=9`;
 if(!doc)return `IF(${count},SUM(Ratings!H${a}:H${z}),"Missing score")`;
 return `IF(${count},(SUM(Ratings!H${a}:H${z})-Ratings!H${a+4}-Ratings!H${a+7})/83*100,"Missing score")`;
}
async function finish(wb,relative,label){
 wb.recalculate();const err=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:5},maxChars:800});
 if(/"address"/.test(err.ndjson||''))throw Error(relative+': '+err.ndjson);
 for(const sh of wb.worksheets.items){
  const end=sh.name==='Combined Rating'?'H14':sh.name==='Summary'?'F9':'F8';
  const png=String(previews.length+1).padStart(4,'0')+'.png';
  const b=await wb.render({sheetName:sh.name,range:'A1:'+end,scale:1,format:'png'});await fs.writeFile(path.join(previewDir,png),new Uint8Array(await b.arrayBuffer()));previews.push({label:label+' / '+sh.name,png});
 }
 const target=path.join(out,relative);await fs.mkdir(path.dirname(target),{recursive:true});await(await SpreadsheetFile.exportXlsx(wb)).save(target);
 checks.push({file:relative,sheets:wb.worksheets.items.length,formulaErrors:err.ndjson});
}
const deliveryIndex=d.steps.flatMap(s=>Object.entries(s.files).map(([kind,file])=>[s.number,s.title,kind,file,only&&!only.has(s.number)?'5.0 retained':d.version,d.date]));
for(const step of d.steps){
 if(only&&!only.has(step.number))continue;
 const n=step.number,rows=d.ratingRows.filter(r=>r[0]===n),fields=d.schema_fields.filter(r=>r[0]===n),nodes=d.schema_nodes.filter(r=>r[0]===n),levels=d.sectionRatings.filter(r=>r[0]===n);
 const a=Workbook.create();
 table(a,'Definition',`Step${n}: populated output schema`,fieldHeads,fields);
 table(a,'Hierarchy',`Step${n}: L1-L4 hierarchy`,hierarchyHeads,nodes);
 table(a,'Artifact Contracts','One schema for each of the three deliverables',['Step','Deliverable','Schema JSON','SHA256','Validation scope'],d.contracts.filter(r=>r[0]===n));
 table(a,'Contract semantics','How to read the schema',['Property','Meaning'],[['L1','Named output section at its stated record grain'],['L2','A single parameter within that section'],['L3','Value contract and meaning/lineage facets'],['L4','Atomic type, requiredness, validation, definition, reason and source'],['Types','Inferred from retained values; source type variation remains explicit as a union. Physical SQL types remain in the dictionary.'],['Nulls','Missing review response stays null and pending. Null is included only for columns where the output contract permits it.'],['Three schemas','Definition records, rating records and output-section records each have a separate serialized JSON contract.'],['Physical additions','157 proposed design fields remain unimplemented; the Excel schema is not an applied database migration.']]);
 await finish(a,step.files.schema,`S${n} schema`);
 const b=Workbook.create();
 const summary=table(b,'Summary',`Step${n}: all three deliverable scores`,['Deliverable','Full score /100','Documentary /100','Critical minimum','Decision','Evidence status'],kinds.map((k,i)=>[k,0,0,0,'Refine','Human interview pending; see closure plan']));
 const inputs=scores(b,rows);
 for(let k=0;k<3;k++){const r=k+6,start=6+k*9;
  summary.getRange(`B${r}:E${r}`).formulas=[[`=${groupFormulas(start,start+8)}`,`=${groupFormulas(start,start+8,true)}`,`=IF(COUNT(Ratings!G${start}:G${start+8})=9,MIN(Ratings!G${start},Ratings!G${start+3},Ratings!G${start+7}),"Missing score")`,`=IF(ISNUMBER(B${r}),IF(B${r}<75,"Rework",IF(AND(B${r}>=90,D${r}>=4),"Accept","Refine")),"Missing score")`]];
 }
 summary.getRange('B6:C8').setNumberFormat('0.0');
 levelRatings(b,levels);
 table(b,'90 Plus Closure','Evidence needed to reach90 under the unchanged rubric',closureHeads,d.closure.filter(r=>r[0]===n));
 const human=table(b,'Human Review','Interview response and independent reviewer inputs',['Step','Question ID','Question','Expected evidence anchor','Human response','Reviewer score 0 to5','Review status','Proposed reviewer role'],d.humanReviews.filter(r=>r[0]===n),{inputs:[4,5]});
 human.getRange('E6:F8').clear({applyTo:'contents'});human.getRange('F6:F8').dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
 table(b,'Method','Scoring and evidence boundaries',['Topic','Rule'],d.method);
 b.recalculate();for(let k=0;k<3;k++)if(Math.abs(summary.getRange(`B${k+6}`).values[0][0]-step.deliverableScores[k])>1e-8)throw Error('Per-step score mismatch '+n);
 await finish(b,step.files.scorecard,`S${n} scorecard`);
 const c=Workbook.create();
 table(c,'Overview',`Step${n}: ${step.title}`,['Item','Value'],[['Step exit',step.exit],['Full step rating /100',step.score],['Documentary step rating /100',step.documentaryScore],['Priority',step.priority],['Implementation boundary','Existing physical baseline and proposed hybrid additions are explicitly separated'],['Approval','Refine: human and production evidence pending'],['Output contract',step.contractFiles.output]]);
 if(n===22&&d.mentor){
  const m=d.mentor,sequence=['searched','screened','applied','shortlisted','assessed','interviewed','selected','rejected','offered','accepted','offer_declined','onboarded'];
  const parents={screened:'searched',applied:'screened',shortlisted:'applied',assessed:'shortlisted',interviewed:'assessed',selected:'interviewed',rejected:'interviewed',offered:'selected',accepted:'offered',offer_declined:'offered',onboarded:'accepted'};
  const calc=table(c,'Funnel Calculator','Editable planning population and conversion rates',['Stage','Projected count','Denominator','Rate','Basis'],sequence.map(st=>[st,m.stages[st],parents[st]||'Population',parents[st]?m.stages[st]/m.stages[parents[st]]:1,'Synthetic scenario assumption; regenerate files after changing inputs']),{inputs:[3]});
  const locations=Object.fromEntries(sequence.map((st,i)=>[st,i+6]));calc.getRange('B6').format.fill='#FFF1D6';
  for(let i=1;i<sequence.length;i++){const st=sequence[i],r=i+6,parent=locations[parents[st]];calc.getRange(`B${r}`).formulas=[[st==='rejected'?`=B${locations.interviewed}-B${locations.selected}`:st==='offer_declined'?`=B${locations.offered}-B${locations.accepted}`:`=ROUND(B${parent}*D${r},0)`]];}
  calc.getRange('D6:D17').setNumberFormat('0.0%');c.recalculate();for(let i=0;i<sequence.length;i++)if(calc.getRange(`B${i+6}`).values[0][0]!==m.stages[sequence[i]])throw Error('Funnel calculator mismatch '+sequence[i]);
  calc.getRange('B6').values=[[m.population*2]];c.recalculate();if(Math.abs(calc.getRange('B8').values[0][0]-m.stages.applied*2)>2||Math.abs(calc.getRange('B17').values[0][0]-m.stages.onboarded*2)>4)throw Error('Population propagation');calc.getRange('B6').values=[[m.population]];c.recalculate();
  for(const st of ['rejected','offer_declined']){const r=locations[st],parent=locations[parents[st]];calc.getRange(`D${r}`).formulas=[[`=IF(B${parent}=0,"n.a.",B${r}/B${parent})`]];calc.getRange(`D${r}`).format.fill='#F1F5FA';}
 }
 for(const [i,sec] of step.sections.entries())table(c,String(i+1).padStart(2,'0')+'_'+sec.name,sec.name,sec.columns,sec.rows);
 await finish(c,step.files.output,`S${n} output`);
 console.log('SAVED STEP',n,'full',step.score.toFixed(1),'documentary',step.documentaryScore.toFixed(1));
 // Checkpoint permits recovery without repeating authored work.
 await fs.writeFile(path.join(out,'evidence/workbook_validation.json'),JSON.stringify({workbooks:checks.length,checks,previews},null,2));
}
const master=Workbook.create();
const heads=['Step','Phase','Step title','Priority','Step weight','Schema full','Scorecard full','Output full','Combined full','Schema documentary','Scorecard documentary','Output documentary','Combined documentary','Decision','Records'];
const summaryRows=d.steps.map(s=>[s.number,s.phase,s.title,s.priority,s.priority==='P0'?3:2,...s.deliverableScores,s.score,...s.documentaryScores,s.documentaryScore,'Refine',s.sections.reduce((a,x)=>a+x.rows.length,0)]);
const main=table(master,'Combined Rating','Talentra hybrid: full and documentary ratings',heads,summaryRows,{start:9});
const ratings=scores(master,d.ratingRows);
main.getRange('A4:B6').values=[['Full rubric /100',0],['Documentary /100',0],['Approval','Refine - human interview and production proof pending']];main.getRange('B4:B5').setNumberFormat('0.0');main.getRange('B4:B5').format.font={name:'Arial',size:16,bold:true,color:'#203B63'};main.getRange('B6:E6').format.rowHeight=32;
for(let i=0;i<22;i++){
 const r=i+10,start=6+i*27,full=[0,9,18].map(k=>'='+groupFormulas(start+k,start+k+8)),doc=[0,9,18].map(k=>'='+groupFormulas(start+k,start+k+8,true));
 main.getRange(`F${r}:M${r}`).formulas=[[...full,`=IF(COUNT(F${r}:H${r})=3,F${r}*0.25+G${r}*0.25+H${r}*0.5,"Missing score")`,...doc,`=IF(COUNT(J${r}:L${r})=3,J${r}*0.25+K${r}*0.25+L${r}*0.5,"Missing score")`]];
 main.getRange(`N${r}`).formulas=[[`=IF(COUNT(F${r}:H${r})<3,"Missing score",IF(I${r}<75,"Rework",IF(AND(I${r}>=90,MIN(Ratings!G${start},Ratings!G${start+3},Ratings!G${start+7},Ratings!G${start+9},Ratings!G${start+12},Ratings!G${start+16},Ratings!G${start+18},Ratings!G${start+21},Ratings!G${start+25})>=4),"Accept","Refine")))`]];
}
main.getRange('B4').formulas=[['=IF(COUNT(I10:I31)=22,SUMPRODUCT(E10:E31,I10:I31)/SUM(E10:E31),"Missing score")']];main.getRange('B5').formulas=[['=IF(COUNT(M10:M31)=22,SUMPRODUCT(E10:E31,M10:M31)/SUM(E10:E31),"Missing score")']];main.getRange('F10:M31').setNumberFormat('0.0');
table(master,'Deliverable Index','66 populated step deliverables',['Step','Title','Kind','Relative file','Version','As of'],deliveryIndex);
table(master,'All Schemas','All typed output parameters',fieldHeads,d.schema_fields);
table(master,'Hierarchy','All L1-L4 contracts',hierarchyHeads,d.schema_nodes);
levelRatings(master,d.sectionRatings);
const max=Math.max(...d.steps.flatMap(s=>s.sections.map(sec=>sec.columns.length)));
table(master,'All Outputs','All populated step records concatenated',['Step','Section','Record',...Array.from({length:max},(_,i)=>'Field '+(i+1))],d.steps.flatMap(s=>s.sections.flatMap(sec=>sec.rows.map((r,i)=>[s.number,sec.name,i+1,...r,...Array(max-r.length).fill('')]))),{compact:true});
table(master,'Field Mapping','Column interpretation for every output section',['Step','Section','Field number','Field name'],d.steps.flatMap(s=>s.sections.flatMap(sec=>sec.columns.map((h,i)=>[s.number,sec.name,i+1,h]))));
table(master,'Artifact Contracts','66 serialized contracts',['Step','Deliverable','Relative file','SHA256','Evidence boundary'],d.contracts);
table(master,'90 Plus Closure','Unchanged-rubric90+ closure plan',closureHeads,d.closure);
table(master,'Merge Decisions','Source conflicts and hybrid decisions',['ID','Topic','Finding','Treatment','Status','Source'],d.mergeDecisions);
table(master,'Source Map','Semantic placement of source B sections',['Source block','B sheet','B section','Records','Canonical step','Destination','Source cell','Mapping rule'],d.sourceMap);
table(master,'Source B Claims','Source reports require independent evidence',['Block','Cell','Context','Source value','Proof boundary','Hybrid treatment'],d.sourceClaims);
table(master,'Source B Archive','Original source B rows as retained values',['Source sheet','Excel row','Section context',...Array.from({length:11},(_,i)=>'Original '+col(i))],d.source_archive,{compact:true});
table(master,'Production Gates','Owned release evidence',['Gate ID','Concern','Required evidence','Owner','Status','Reason'],d.release_gates);
table(master,'Refinement Loops','Executed refinement and stopping conditions',['Loop','Action','Finding or change','Evidence or next action','Status'],d.loops);
table(master,'Current Validation','Current documentary checks',['Test ID','Step','Category','Case','Result','Detail','Proof layer'],d.validation);
table(master,'Sources','Source provenance',['Source ID','Title','File or URL','Locator','Use'],d.sources);
table(master,'Method','Rubric, scope and refresh',['Topic','Rule'],d.method);
master.recalculate();const full=main.getRange('B4').values[0][0],doc=main.getRange('B5').values[0][0];
if(Math.abs(full-d.combinedRating)>1e-8||Math.abs(doc-d.documentaryRating)>1e-8)throw Error('Master score mismatch');
const keep=ratings.getRange('G6').values[0][0];ratings.getRange('G6').values=[[4]];master.recalculate();if(!(main.getRange('B4').values[0][0]<full))throw Error('Rating propagation');ratings.getRange('G6').clear({applyTo:'contents'});master.recalculate();if(main.getRange('B4').values[0][0]!=='Missing score')throw Error('Missing score guard');ratings.getRange('G6').values=[[keep]];
const block=ratings.getRange('G6:G32').values;ratings.getRange('G6:G32').values=Array.from({length:27},()=>[5]);ratings.getRange('G6').values=[[3]];master.recalculate();if(main.getRange('N10').values[0][0]!=='Refine')throw Error('Critical floor');ratings.getRange('G6:G32').values=block;master.recalculate();
d.combinedRating=main.getRange('B4').values[0][0];d.documentaryRating=main.getRange('B5').values[0][0];d.deliverables=deliveryIndex;
await finish(master,'Talentra_Combined.xlsx','Master');
await fs.writeFile(path.join(work,'dashboard_data.json'),JSON.stringify(d));
await fs.writeFile(path.join(out,'evidence/workbook_validation.json'),JSON.stringify({workbooks:checks.length,formulaPropagation:'PASS',missingInputGuard:'PASS',criticalFloor:'PASS',full:d.combinedRating,documentary:d.documentaryRating,checks,previews},null,2));
console.log('COMPLETE',JSON.stringify({books:checks.length,sheets:previews.length,full:d.combinedRating,documentary:d.documentaryRating}));
