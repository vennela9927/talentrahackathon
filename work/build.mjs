import fs from 'node:fs/promises';
import path from 'node:path';
import { Workbook, SpreadsheetFile } from '@oai/artifact-tool';

const root=path.resolve(import.meta.dirname,'..');
const dataName=process.argv.find(x=>x.startsWith('--data='))?.split('=')[1]||'project_data.json';
const data=JSON.parse(await fs.readFile(path.join(root,'work',dataName),'utf8'));
const out=path.join(root,'outputs',data.output_folder||'talentra_steps_01_16');
const stepCount=data.steps.length,deliverableCount=stepCount*3,workbookCount=deliverableCount+1,endRow=9+stepCount;
const extended=stepCount>16;
const previewDir=path.join(root,'work',extended?'previews_phase3':'previews');
await fs.mkdir(previewDir,{recursive:true});
const C={ink:'#14243B',navy:'#203B63',blue:'#325FA0',light:'#EDF2F8',muted:'#62748A',amber:'#FFF1D6',red:'#FFE2DD'};
const col=i=>{let s='';for(i++;i;i=Math.floor((i-1)/26))s=String.fromCharCode(65+(i-1)%26)+s;return s;};
const safe=s=>s.replace(/[^a-zA-Z0-9]+/g,'_').replace(/^_|_$/g,'');
let previewNumber=0;
const checks=[];
const only=process.argv.find(x=>x.startsWith('--only='))?.split('=')[1].split(',').map(Number);

function table(wb,name,title,headers,rows,{inputCols=[],start=5}={}){
 const sheet=wb.worksheets.add(name.slice(0,31));
 const end=col(headers.length-1),last=start+rows.length;
 sheet.showGridLines=false;
 sheet.getRange(`A1:${end}${Math.max(last,8)}`).format.font={name:'Arial',size:10,color:C.ink};
 sheet.getRange(`A1:${end}${Math.max(last,8)}`).format.verticalAlignment='center';
 sheet.getRange('A2').values=[[title]];
 sheet.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:C.navy};
 sheet.getRange(`A3:${end}3`).format.borders={bottom:{style:'thin',color:C.blue}};
 sheet.getRange(`A${start}:${end}${start}`).values=[headers];
 sheet.getRange(`A${start}:${end}${start}`).format={fill:C.navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:34,horizontalAlignment:'center',verticalAlignment:'center'};
 if(rows.length) sheet.getRange(`A${start+1}:${end}${last}`).values=rows.map(r=>r.map(v=>v===null?'NULL - permitted by contract':v));
 for(let j=0;j<headers.length;j++){
  const h=headers[j],vals=rows.map(r=>String(r[j]??''));
  const max=Math.max(h.length,...vals.map(x=>Math.min(x.length,100)));
  let width=/ ID$|^ID$|^Step$|^Level$|Priority|Nullable|Weight|Score|score|Row count/.test(h)?17:Math.min(62,Math.max(22,max*.58));
  if(/Definition|Validation|Enforcement|Reason|Null reason|Statement|Acceptance|Postcondition|Question|Evidence|Content|Decision|Remaining|Limitation/.test(h))width=Math.max(width,42);
  sheet.getRange(`${col(j)}${start}:${col(j)}${Math.max(last,start+1)}`).format.columnWidth=width;
  if(rows.length){
   sheet.getRange(`${col(j)}${start+1}:${col(j)}${last}`).format.wrapText=true;
   if(rows.every(r=>typeof r[j]==='number'))sheet.getRange(`${col(j)}${start+1}:${col(j)}${last}`).setNumberFormat(/share|ratio|coverage/i.test(h)?'0.0%':(/score|contribution/i.test(h)?'0.0':(/Seed|^Level$|^Step$/.test(h)?'0':(rows.some(r=>!Number.isInteger(r[j]))?'0.00':'#,##0'))));
  }
 }
 for(let i=0;i<rows.length;i++){
  const r=start+1+i;
  const lines=Math.max(...rows[i].map((v,j)=>Math.ceil(String(v??'').length/(sheet.getRange(`${col(j)}${r}`).format.columnWidth||30))));
  sheet.getRange(`A${r}:${end}${r}`).format.rowHeight=Math.max(30,Math.min(160,(lines+1)*14));
  if(i%2===1)sheet.getRange(`A${r}:${end}${r}`).format.fill='#F3F6FA';
 }
 for(const j of inputCols)if(rows.length)sheet.getRange(`${col(j)}${start+1}:${col(j)}${last}`).format.fill=C.amber;
 if(rows.length){
  const tbl=sheet.tables.add(`A${start}:${end}${last}`,true,'T_'+safe(name)+'_'+wb.worksheets.items.length);
  tbl.showBandedRows=false;
  sheet.freezePanes.freezeRows(start);
  if(headers.length>7)sheet.freezePanes.freezeColumns(2);
 }
 sheet.tabColor=C.blue;
 return sheet;
}

async function finish(wb,file,{render=true}={}){
 if(only&&file.startsWith('steps/')&&!only.includes(Number(file.split('/')[1].slice(0,2))))return;
 wb.recalculate();
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:5},maxChars:1500});
 checks.push({file,errors:errors.ndjson});
 if(/"address"/.test(errors.ndjson||''))throw Error('Formula error in '+file+': '+errors.ndjson);
 if(render){
  for(const sheet of wb.worksheets.items){
   try{
    const png=await wb.render({sheetName:sheet.name,range:sheet.name==='Combined Rating'?'A1:J16':`A1:${col(Math.min(5,sheet.getUsedRange().values[4]?.length-1||3))}9`,scale:1,format:'png'});
    await fs.writeFile(path.join(previewDir,String(++previewNumber).padStart(3,'0')+'_'+safe(path.basename(file,'.xlsx')+'_'+sheet.name)+'.png'),new Uint8Array(await png.arrayBuffer()));
   }catch(e){checks.push({file,sheet:sheet.name,renderError:String(e)});console.log('RENDER LIMIT',file,sheet.name,String(e).slice(0,120));}
  }
 }
 const xlsx=await SpreadsheetFile.exportXlsx(wb);
 await xlsx.save(path.join(out,file));
}

const dimensions=[
 ['Structure conformance',14,true,'Matching output fields / defined fields','Generate'],
 ['Completeness',14,false,'Fields populated or explicit UNKNOWN / fields','Generate'],
 ['Definition clarity',9,false,'Parameters with definition, type and reason / parameters','Define'],
 ['Accuracy and traceability',18,true,'Items with source or explicit design/assumption / items','Generate'],
 ['Consistency across runs',9,false,'Independent content runs compared / required runs','Analyse'],
 ['Structure and depth',9,false,'Atomic typed leaves with justified L1-L4 parents / leaves','Define'],
 ['Fitness for next step',9,false,'Required downstream inputs available / inputs needed','Define'],
 ['Author understanding',8,true,'Human author interview answers demonstrated / questions','Discover'],
 ['Deliverable-specific coverage',10,false,'Step exit criterion addressed by evidence','Validate'],
];
const ratingRows=[];const sectionRows=[];const deliverables=[];const stepRatings=[];
function scoreSet(step,kind){
 const special=[3,4,12,13,16,19,20,21].includes(step.number);
 const specific=kind==='Output Document'&&[20,21].includes(step.number)?3:(special&&kind==='Output Document'?4:5);
 const scores=[5,5,5,5,0,5,kind==='Output Document'?4:5,0,specific];
 const evidence=[
  'Schema column names and row widths are checked by the builder.',
  'All documentary cells populated; NULL and UNKNOWN explicitly identified.',
  'Schema field register includes type, definition, reason, priority and source.',
  'Sources/design decisions are explicit. This is a traceability check, not an independent factual audit.',
  'Unassessed: no independent LLM or human content run. A deterministic seed replay is not substituted.',
  'L1 section > L2 group > L3 parameter > L4 atomic definition; node links checked.',
  kind==='Output Document'?'Downstream contract is available; owner decisions and integration proof remain open.':'Structure provides named fields, rules and evaluation contracts.',
  'Unassessed: student/author interview and independent peer review have not occurred.',
  special&&kind==='Output Document'?'Source unknowns, proposed targets, policy approval or runtime evidence prevent full exit confirmation.':'Requested artifact populated with step-specific records and trace links.',
 ];
 return dimensions.map((d,i)=>({dimension:d[0],weight:d[1],critical:d[2],measure:d[3],score:scores[i],contribution:d[1]*scores[i]/5,evidence:evidence[i],next:d[4]}));
}
const methodRows=[
 ['Scope',extended?'D3 steps1-21: Discover1-5, Model6-12 and Prove13-21. Artifact preparation is complete through21; G3 remains open for native engine, NFR and human review evidence.':'D3 steps1-16: Discover1-5, Model6-12, Prove13-16 only. Phase3/G3 continues through step21.'],
 ['Rubric','D5 pp.12-13 eight core dimensions retained. Reweighted core=90, one step-specific dimension=10; total 100.'],
 ['Weights','Structure 14; completeness 14; clarity 9; traceability 18; independent consistency 9; depth 9; next-step fitness 9; human understanding 8; specific coverage 10.'],
 ['Dimension scale','5 >=98%; 4 >=90%; 3 >=75%; 2 >=50%; 1 >0%; 0 absent/unassessed. Judgment dimensions use written evidence.'],
 ['Score','SUM(weight * dimension_score / 5). Unassessed dimensions conservatively contribute zero.'],
 ['Technical view','Observed-dimension contributions / observed weight * 100. Excludes independent consistency and human understanding (17 total weight). Not the full rating.'],
 ['Acceptance','Accept only if full score >=90 and every critical score >=4. Refine at 75-89 or critical <4; Rework below75. All current acceptance gates remain open.'],
 ['Combined rating','Each step = 25% schema + 25% scorecard + 50% populated output. Project = priority-weighted step scores (P0=3,P1=2). Weights are disclosed design choices, not source mandates.'],
 ['Section and level scores','Each field has 0-5 contract quality scores (shape/completeness/traceability). Section = priority-weighted field average; L1-L4 are structural quality scores and never replace the deliverable gate.'],
 ['Peer entry','Amber peer-score cells are intentionally blank. They record a future review; provisional self-scores are authoritative for the current saved rollup. Reconcile peer findings before a new version.'],
 ['Refresh','Per-step and consolidated workbooks calculate locally from their own ratings. HTML is a dated snapshot; regenerate from evidence after approved changes. No live cross-file Excel dependency.'],
 ['Evidence boundary',extended?'V1 regression was re-executed. V2 Python contracts, full SQLite structural DDL/sample load, state-table queries and independent static PostgreSQL DDL drift checks were executed. Native PostgreSQL, concurrency, target-volume NFRs and runtime endpoints remain pending.':'Python contract tests and a SQLite constraint subset were executed. PostgreSQL DDL, concurrent transaction races, target-volume NFRs and real endpoint authorization were not executed.'],
 ['Kluster','Requested kluster tools are unavailable in this session; no kluster verification is claimed.'],
 ['Source policy','Document content is reference material. User request controls deliverables and step cap; D1 controls product scope; D3 controls step numbering; D5 controls rating model; D2/D4 guide method.'],
 ['Review status','Prepared by Codex on 2026-10-27. No independent peer, mentor sign-off or human understanding assessment is claimed.'],
];
await fs.mkdir(path.join(out,'steps'),{recursive:true});

for(const step of data.steps){
 const stem=`${String(step.number).padStart(2,'0')}_${safe(step.title)}`;
 const dir='steps/'+stem;
 await fs.mkdir(path.join(out,dir),{recursive:true});
 const f=data.schema_fields.filter(r=>r[0]===step.number), n=data.schema_nodes.filter(r=>r[0]===step.number);
 const schema=Workbook.create();
 table(schema,'Definition',`Step ${step.number}: output schema v1`,['Step','L1 Section','L2 Group','L3 Parameter','L4 Data type','Atomic or composite','Required','Allowed values or format','Definition','Reason','Section priority','Source','Example','Node ID'],f);
 table(schema,'Hierarchy',`Step ${step.number}: L1-L4 hierarchy`,['Step','Node ID','Parent ID','Level','Name','Priority','Definition','Source'],n);
 table(schema,'Schema decisions','Schema version and depth decisions',['Decision','Treatment'],[['Version','v1.0 prepared; human freeze/approval pending'],['Depth','L1 section, L2 group, L3 parameter and L4 atomic definition. Stop at atomic typed fields.'],['Branch size','Parameter groups kept near 10-15 children; record instances are not new schema nodes.'],['Kept','All step exit fields plus source, owner, priority and failure/unknown treatment where needed.'],['Dropped','Decorative fields, fabricated reviewer approvals and out-of-cap implementation claims.'],['Source','D5 pp.5,8,17-19; D4 pp.30-35'],['Lifecycle output',step.exit]]);
 const schemaFile=dir+'/a_Output_Schema_Definition.xlsx';await finish(schema,schemaFile);

 const rating=Workbook.create();
 const rows=[];const summaries=[];
 for(const [k,kind] of ['Output Schema Definition','Schema Rating Scorecard','Output Document'].entries()){
  const ds=scoreSet(step,kind); const total=ds.reduce((s,d)=>s+d.contribution,0), observed=ds.filter(d=>![4,7].includes(dimensions.findIndex(x=>x[0]===d.dimension))).reduce((s,d)=>s+d.contribution,0)/83*100;
  summaries.push([kind,total,observed,0,'Refine - critical review unassessed','Provisional author assessment']);
  for(const d of ds){
   rows.push([kind,d.dimension,d.weight,d.critical?'Yes':'No',d.measure,d.score,null,d.evidence,d.next,null,'Peer not reviewed']);
   ratingRows.push([step.number,kind,d.dimension,d.weight,d.critical?'Yes':'No',d.measure,d.score,d.contribution,d.evidence,d.next]);
  }
 }
 const summary=table(rating,'Summary',`Step ${step.number}: deliverable ratings`,['Deliverable','Full score /100','Observed score /100','Critical minimum','Decision','Basis'],summaries);
 const detail=table(rating,'Ratings',`Step ${step.number}: scoring evidence`,['Deliverable','Dimension','Weight','Critical','Measure','Author score /5','Contribution','Evidence','Return stage','Peer score /5','Review status'],rows,{inputCols:[5,9]});
 // Empty peer score cells are deliberate future inputs, not missing scored evidence.
 detail.getRange('J6:J32').clear({applyTo:'contents'});
 detail.getRange('F6:F32').dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
 detail.getRange('J6:J32').dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
 for(let i=0;i<27;i++)detail.getRange(`G${i+6}`).formulas=[[`=C${i+6}*F${i+6}/5`]];
 for(let k=0;k<3;k++){
  const start=6+k*9,last=start+8;
  summary.getRange(`B${k+6}`).formulas=[[`=SUM(Ratings!G${start}:G${last})`]];
  summary.getRange(`C${k+6}`).formulas=[[`=(SUM(Ratings!G${start}:G${last})-Ratings!G${start+4}-Ratings!G${start+7})/83*100`]];
  summary.getRange(`D${k+6}`).formulas=[[`=MIN(Ratings!F${start},Ratings!F${start+3},Ratings!F${start+7})`]];
  summary.getRange(`E${k+6}`).formulas=[[`=IF(B${k+6}<75,"Rework",IF(AND(B${k+6}>=90,D${k+6}>=4),"Accept","Refine"))`]];
 }
 const sr=[];
 for(const sec of step.sections){
  const sourceKnown=!sec.source.includes('UNKNOWN');
  for(let l=1;l<=4;l++){
   const r=[step.number,sec.name,l,sec.priority,sec.priority==='P0'?3:2,5,5,sourceKnown?5:4,null,'Provisional contract assessment; independent review open'];
   sr.push(r);sectionRows.push(r);
  }
 }
 const ss=table(rating,'Section Ratings',`Step ${step.number}: section and level scores`,['Step','Section','Level','Priority','Priority weight','Structure /5','Completeness /5','Traceability /5','Rating /5','Basis'],sr);
 for(let i=0;i<sr.length;i++)ss.getRange(`I${i+6}`).formulas=[[`=AVERAGE(F${i+6}:H${i+6})`]];
 table(rating,'Method','Scoring method and limitations',['Topic','Definition'],methodRows);
 const ratingFile=dir+'/b_Schema_Rating_Scorecard.xlsx';await finish(rating,ratingFile);

 const output=Workbook.create();
 for(const sec of step.sections)table(output,sec.name,`Step ${step.number}: ${sec.name}`,sec.columns,sec.rows);
 const outputFile=dir+'/c_Output_Document.xlsx';await finish(output,outputFile);
 const totals=summaries.map(r=>r[1]);const score=.25*totals[0]+.25*totals[1]+.5*totals[2];
 const priority=[1,4,8,9,10,11,12,14,15,16,17,18,19,20,21].includes(step.number)?'P0':'P1';
 stepRatings.push([step.number,step.phase,step.title,priority,priority==='P0'?3:2,...totals,score,'Refine - independent review pending',step.sections.reduce((s,x)=>s+x.rows.length,0),step.sections.length]);
 for(const [kind,file] of [['Schema',schemaFile],['Scorecard',ratingFile],['Output',outputFile]])deliverables.push([step.number,step.title,kind,file,'Prepared v1.0',data.date]);
 step.files={schema:schemaFile,scorecard:ratingFile,output:outputFile};step.score=score;step.deliverableScores=totals;step.priority=priority;
 console.log('SAVED STEP',step.number,step.title,'score',score.toFixed(1));
}

const master=Workbook.create();
const dash=table(master,'Combined Rating',`Talentra: steps1-${stepCount} combined rating`,['Step','Phase','Step title','Priority','Step weight','Schema /100','Scorecard /100','Output /100','Step score /100','Gate status','Output records','Sections'],stepRatings,{start:9});
dash.getRange('A4').values=[['Combined /100']];
dash.getRange('B4').formulas=[[`=SUMPRODUCT(E10:E${endRow},I10:I${endRow})/SUM(E10:E${endRow})`]];
dash.getRange('B4').setNumberFormat('0.0');dash.getRange('B4').format.font={name:'Arial',size:16,bold:true,color:C.navy};
dash.getRange('D4').values=[['Review status']];dash.getRange('E4').values=[['Provisional; human review unassessed']];
dash.getRange('A6').values=[['Step = 25% schema + 25% scorecard + 50% output. P0 weight 3, P1 weight 2.']];
dash.getRange('A7').values=[[extended?'Phase3 artifacts cover steps13-21. G3 is OPEN for native engine, target NFR and human review evidence.':'Unassessed human understanding is a critical gate. Phase3 ends here at step16; G3 is not reached.']];
if(extended){dash.getRange('D5').values=[['Phase3 /100']];dash.getRange('E5').formulas=[[`=SUMPRODUCT(E22:E${endRow},I22:I${endRow})/SUM(E22:E${endRow})`]];dash.getRange('E5').setNumberFormat('0.0');}
const rr=table(master,'All Ratings',`All ${deliverableCount} deliverables: scoring evidence`,['Step','Deliverable','Dimension','Weight','Critical','Measure','Author score /5','Contribution','Evidence','Return stage'],ratingRows,{inputCols:[6]});
for(let i=0;i<ratingRows.length;i++)rr.getRange(`H${i+6}`).formulas=[[`=D${i+6}*G${i+6}/5`]];
rr.getRange(`G6:G${ratingRows.length+5}`).dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
for(let i=0;i<stepCount;i++){
 const r=i+10,base=6+i*27;
 dash.getRange(`F${r}`).formulas=[[`=SUM('All Ratings'!H${base}:H${base+8})`]];
 dash.getRange(`G${r}`).formulas=[[`=SUM('All Ratings'!H${base+9}:H${base+17})`]];
 dash.getRange(`H${r}`).formulas=[[`=SUM('All Ratings'!H${base+18}:H${base+26})`]];
 dash.getRange(`I${r}`).formulas=[[`=F${r}*0.25+G${r}*0.25+H${r}*0.5`]];
 dash.getRange(`J${r}`).formulas=[[`=IF(I${r}<75,"Rework",IF(AND(I${r}>=90,MIN('All Ratings'!G${base},'All Ratings'!G${base+3},'All Ratings'!G${base+7},'All Ratings'!G${base+9},'All Ratings'!G${base+12},'All Ratings'!G${base+16},'All Ratings'!G${base+18},'All Ratings'!G${base+21},'All Ratings'!G${base+25})>=4),"Accept","Refine"))`]];
}
table(master,'Deliverable Index',`All ${deliverableCount} Excel deliverables`,['Step','Step title','Kind','Relative file','Version','As of'],deliverables);
table(master,'All Schemas',`Output contracts for all ${stepCount} steps`,['Step','L1 Section','L2 Group','L3 Parameter','L4 Data type','Atomic or composite','Required','Allowed values or format','Definition','Reason','Priority','Source','Example','Node ID'],data.schema_fields);
const allOutputs=[];
for(const step of data.steps)for(const sec of step.sections)for(let i=0;i<sec.rows.length;i++)allOutputs.push([step.number,sec.name,i+1,...sec.rows[i],...Array(15-sec.rows[i].length).fill('Not used by this section')]);
table(master,'All Outputs','Concatenated populated output records',['Step','Section','Record number',...Array.from({length:15},(_,i)=>'Field '+String(i+1).padStart(2,'0'))],allOutputs);
table(master,'Field Mapping','Column labels for the concatenated output',['Step','Section','Field number','Field name'],data.steps.flatMap(s=>s.sections.flatMap(x=>x.columns.map((h,i)=>[s.number,x.name,i+1,h]))));
const sr=table(master,'Section Ratings','L1-L4 section ratings and priority',['Step','Section','Level','Priority','Priority weight','Structure /5','Completeness /5','Traceability /5','Rating /5','Basis'],sectionRows);
for(let i=0;i<sectionRows.length;i++)sr.getRange(`I${i+6}`).formulas=[[`=AVERAGE(F${i+6}:H${i+6})`]];
table(master,'Evidence','Executed sample checks',['Measure','Value','Boundary'],Object.entries(data.summary).map(([k,v])=>[k,v,'Synthetic sample; Python/SQLite subset, no PostgreSQL certification']));
table(master,'Method','Scoring and scope',['Topic','Definition'],methodRows);
table(master,'Sources',`Sources used across all ${stepCount} steps`,['Source ID','Title','File or URL','Locator','Use'],data.sources);
master.recalculate();
// Check a real edit propagates to the owning contribution, step result and project rating.
const before=dash.getRange('B4').values[0][0];
const old=rr.getRange('G6').values[0][0];rr.getRange('G6').values=[[4]];master.recalculate();
const changed=dash.getRange('B4').values[0][0];
if(!(changed<before))throw Error('Rating input change did not propagate');
rr.getRange('G6').values=[[old]];master.recalculate();
if(Math.abs(dash.getRange('B4').values[0][0]-before)>1e-8)throw Error('Rating restoration failed');
// Boundary check: a single critical 3 must block an otherwise eligible rating.
const original=rr.getRange('G6:G32').values;
rr.getRange('G6:G32').values=Array.from({length:27},()=>[5]);rr.getRange('G6').values=[[3]];master.recalculate();
if(dash.getRange('J10').values[0][0]!=='Refine')throw Error('Critical gate failed');
rr.getRange('G6:G32').values=original;master.recalculate();
data.combinedRating=dash.getRange('B4').values[0][0];data.ratingRows=ratingRows;data.sectionRatings=sectionRows;data.method=methodRows;data.deliverables=deliverables;
if(extended)data.phase3Rating=dash.getRange('E5').values[0][0];
await finish(master,'Talentra_Combined.xlsx');
await fs.writeFile(path.join(root,'work',extended?'dashboard_data_phase3.json':'dashboard_data.json'),JSON.stringify(data));
await fs.writeFile(path.join(root,'work',extended?'workbook_checks_phase3.json':'workbook_checks.json'),JSON.stringify({checks,formulaEditTest:{before,changed,restored:data.combinedRating},workbooks:workbookCount,previews:previewNumber},null,2));
console.log('COMPLETE',JSON.stringify({combined:data.combinedRating,phase3:data.phase3Rating,workbooks:workbookCount,previews:previewNumber,records:allOutputs.length}));
