import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook, SpreadsheetFile} from '@oai/artifact-tool';

const root=path.resolve(import.meta.dirname,'..');
const data=JSON.parse(await fs.readFile(path.join(root,'work/project_data_v3.json'),'utf8'));
const out=path.join(root,'outputs',data.output_folder);
const previewDir=path.join(root,'work/previews_v3');
await fs.mkdir(previewDir,{recursive:true});
const col=i=>{let s='';for(i++;i;i=Math.floor((i-1)/26))s=String.fromCharCode(65+(i-1)%26)+s;return s;};
const safe=s=>s.replace(/[^a-zA-Z0-9]+/g,'_').replace(/^_|_$/g,'');
const C={ink:'#162A43',navy:'#203B63',blue:'#3C6291',light:'#F1F5FA',amber:'#FFF1D6'};
const onlyArg=process.argv.find(x=>x.startsWith('--only='));
const only=onlyArg?onlyArg.split('=')[1].split(',').map(Number):null;
let previous=null;
if(only)previous=JSON.parse(await fs.readFile(path.join(out,'evidence/workbook_validation.json'),'utf8'));
const checks=previous?previous.checks:[];let previewNumber=previous?previous.previews:0;
const sheetsRendered=[];

function table(wb,name,title,headers,rows,{start=5,inputCols=[],renderCols=6}={}){
 const sh=wb.worksheets.add(name.slice(0,31));const end=col(headers.length-1),last=start+rows.length;
 sh.showGridLines=false;
 sh.getRange(`A1:${end}${Math.max(last,8)}`).format={font:{name:'Arial',size:10,color:C.ink},verticalAlignment:'center'};
 sh.getRange('A2').values=[[title]];sh.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:C.navy};
 sh.getRange(`A3:${end}3`).format.borders={bottom:{style:'thin',color:C.blue}};
 sh.getRange(`A${start}:${end}${start}`).values=[headers];
 sh.getRange(`A${start}:${end}${start}`).format={fill:C.navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},wrapText:true,rowHeight:40,horizontalAlignment:'center',verticalAlignment:'center',borders:{insideVertical:{style:'thin',color:'#FFFFFF'}}};
 const rr=rows.map(r=>r.map(v=>v===null?'NULL - permitted only by the stated contract':typeof v==='object'?JSON.stringify(v):v));
 if(rr.length)sh.getRange(`A${start+1}:${end}${last}`).values=rr;
 for(let j=0;j<headers.length;j++){
  const h=headers[j];let width=/^Step$|^Level$|Priority|^Weight$|^Critical$|^Score|^Author score|^Peer score/.test(h)?15:/ ID$|^ID$/.test(h)?19:/Definition|Reason|Evidence|Validation|Statement|Acceptance|Outcome|Required evidence|Transformation|Conflict|Null reason|Treatment|Proof/.test(h)?56:34;
  if(h==='L1 Section'||h==='L2 Parameter')width=36;
  sh.getRange(`${col(j)}${start}:${col(j)}${Math.max(last,start+1)}`).format.columnWidth=width;
  if(rr.length){
   const rg=sh.getRange(`${col(j)}${start+1}:${col(j)}${last}`);rg.format.wrapText=true;
   if(rr.every(r=>typeof r[j]==='number')){rg.setNumberFormat(/score|rating|contribution|weight/i.test(h)?'0.0':rr.some(r=>!Number.isInteger(r[j]))?'0.00':'#,##0');rg.format.horizontalAlignment='right';}
  }
 }
 if(rr.length){
  sh.getRange(`A${start+1}:${end}${last}`).format.rowHeight=64;
  // Group equal row heights so large dictionaries do not trigger a call per cell.
  const heights=rr.map(r=>Math.max(38,Math.min(220,Math.max(...r.map((v,j)=>Math.ceil(String(v??'').length/(sh.getRange(`${col(j)}${start}`).format.columnWidth*.95))))*14+14)));
  let begin=0;for(let i=1;i<=heights.length;i++)if(i===heights.length||heights[i]!==heights[begin]){sh.getRange(`A${start+1+begin}:${end}${start+i}`).format.rowHeight=heights[begin];begin=i;}
  const tbl=sh.tables.add(`A${start}:${end}${last}`,true,'T_'+safe(name)+'_'+wb.worksheets.items.length);tbl.showBandedRows=true;
  sh.freezePanes.freezeRows(start);if(headers.length>7)sh.freezePanes.freezeColumns(2);
 }
 for(const j of inputCols)if(rr.length)sh.getRange(`${col(j)}${start+1}:${col(j)}${last}`).format.fill=C.amber;
 sh.tabColor=C.blue;
 return sh;
}

async function finish(wb,file){
 if(only&&file.startsWith('steps/')&&!only.includes(Number(file.split('/')[1].slice(0,2))))return;
 wb.recalculate();
 const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:10},maxChars:1600});
 if(/"address"/.test(errors.ndjson||''))throw Error('Formula error '+file+': '+errors.ndjson);
 const rec={file,formulaErrors:errors.ndjson,sheets:[]};
 for(const sh of wb.worksheets.items){
  const used=sh.getUsedRange().values;const ncols=Math.min(6,Math.max(1,used[4]?.length||used[0]?.length||1));
  const blob=await wb.render({sheetName:sh.name,range:`A1:${col(ncols-1)}${Math.min(9,used.length)}`,scale:1,format:'png'});
  const png=String(++previewNumber).padStart(3,'0')+'_'+safe(path.basename(file,'.xlsx')+'_'+sh.name)+'.png';
  await fs.writeFile(path.join(previewDir,png),new Uint8Array(await blob.arrayBuffer()));
  rec.sheets.push({sheet:sh.name,preview:png});sheetsRendered.push({file,sheet:sh.name,preview:png});
 }
 const x=await SpreadsheetFile.exportXlsx(wb);await x.save(path.join(out,file));const oldCheck=checks.findIndex(x=>x.file===file);if(oldCheck>=0)checks.splice(oldCheck,1);checks.push(rec);
}
const dimensions=[
 ['Structure conformance',14,true,'Output rows/fields conform to the defined contract','Generate'],
 ['Completeness',14,false,'Populated or explicit UNKNOWN cells / required documentary cells','Generate'],
 ['Definition clarity',9,false,'Parameters with meaning, type, validation and reason / parameters','Define'],
 ['Accuracy and traceability',18,true,'Source-located or explicitly proposed design items / items','Generate'],
 ['Consistency across runs',9,false,'Independent author/model content agreement / compared items','Analyse'],
 ['Structure and depth',9,false,'D5 L1 sections > L2 parameters > L3 facets > L4 atomic definitions','Define'],
 ['Fitness for next step',9,false,'Required downstream inputs usable with stated open decisions','Define'],
 ['Author understanding',8,true,'Human field questions correctly answered / questions asked','Discover'],
 ['Deliverable-specific coverage',10,false,'Step exit criterion supported at its required proof layer','Validate']
];
const method=[
 ['Scope',data.scope_note],['Current version','v3.0 prepared2026-10-28. Prior v1/v2 snapshots preserved.'],
 ['Hierarchy','D5 semantics: L1 section; L2 parameter; L3 value-contract or meaning/lineage facets; L4 atomic type, allowed values, requiredness, definition, reason and source.'],
 ['Rubric','Eight D5 core dimensions reweighted to90 plus10 step-specific. Weights14,14,9,18,9,9,9,8,10 total100.'],
 ['Scale','5 >=98%;4 >=90%;3 >=75%;2 >=50%;1 >0%;0 absent or unassessed. Judgment dimensions require written evidence.'],
 ['Full rating','SUM(weight*score/5). Independent content comparison and human understanding are unassessed and contribute0; no independent review is fabricated.'],
 ['Observed rating','Full contributions divided by83 observed weight, excluding9 independent consistency and8 human understanding. This is a supplementary view, not the acceptance score.'],
 ['Acceptance','Accept only full score>=90 and every critical dimension>=4. Rework below75; otherwise Refine. Release gates remain separately open regardless of documentary scores.'],
 ['Rollup','Step=25% schema+25% scorecard+50% output. Project and phase ratings use P0 weight3/P1 weight2/P2 weight1. These are disclosed project choices.'],
 ['Section ratings','Average of measured structure, documentary fill, source/definition quality and evidence readiness. L1-L4 ratings describe contract quality, not production capacity.'],
 ['Peer inputs','Amber0-5 cells are editable; blank peer cells mean not reviewed. Consolidated workbook owns the authoritative editable rating snapshot. Per-step files calculate independently.'],
 ['Evidence','Baseline v2 suite re-executed1565/1565. V3 portable validation348/348. SQLite/static/Python layers only. Native PostgreSQL, real provider callbacks, concurrency, target volume and recovery NOT RUN.'],
 ['Capacity','Editable assumptions drive RPS, burst DB concurrency, storage and connection ceilings. No number is a measured deployment capacity.'],
 ['HTML refresh','The HTML embeds this saved data snapshot. It includes all output records and can search/filter/download them. Regenerate after approved Excel/source changes.'],
 ['Source priority','User request controls the22-step cap and deliverables. D1 controls business scope. D3 controls lifecycle numbering. D5 controls quality method. D2/D4 guide scenarios and refinement.'],
 ['Production boundary','120 tables and1250 columns provide the current design. Schema breadth cannot guarantee arbitrary user count or zero production defects. Required release evidence is owned and visible.'],
 ['Kluster','Requested Kluster tools unavailable in this session. No Kluster verification is claimed.']
];
const percentScore=x=>x>=.98?5:x>=.9?4:x>=.75?3:x>=.5?2:x>0?1:0;
function scoreSet(s,kind){
 const ms=data.section_metrics.filter(x=>x.step===s.number);
 const structure=percentScore(ms.filter(x=>x.conformance).length/ms.length);
 const fill=percentScore(ms.reduce((a,x)=>a+x.fill,0)/ms.length);
 const specific=kind==='Output Document'&&[20,21].includes(s.number)?3:kind==='Output Document'&&[3,4,12,13,22].includes(s.number)?4:5;
 const fitness=kind==='Output Document'&&[4,12,20,21,22].includes(s.number)?4:5;
 const vals=[structure,fill,5,5,0,5,fitness,0,specific];
 const ev=[`All${ms.length} section contracts checked for exact row widths and defined fields.`,
  'Documentary fill measured. NULL, proposed, pending and UNKNOWN remain explicit rather than silently replaced with business facts.',
  'Every output parameter has a business meaning, type, allowed-value rule, requiredness, reason and source. Semantic owner approval remains open.',
  'PDF locators, retained baseline evidence and proposed design labels identify provenance. Provider fields are proposed interfaces, not claims about a live API.',
  'Unassessed. One authoring session and a deterministic replay are not independent content-review runs.',
  'L1 sections, L2 parameters, L3 facets and L4 atomic properties. Dictionary tables keep their necessary17-field record shape with an explicit depth decision.',
  fitness===5?'Required design inputs are present and traceable to the next step.':'Design inputs are present; proposed targets/policy/provider/native proof prevents unconditional downstream acceptance.',
  'Unassessed. A human author interview, independent peer rating and mentor checkpoint have not occurred.',
  specific===5?'Requested artifact content and exit evidence links are present at the declared documentary layer.':specific===4?'Proposed source/policy/scale inputs require owner confirmation and external evidence.':'Native PostgreSQL/target NFR tests required by the exit criterion have not run.'
 ];
 return dimensions.map((x,i)=>({dimension:x[0],weight:x[1],critical:x[2],measure:x[3],score:vals[i],contribution:x[1]*vals[i]/5,evidence:ev[i],next:x[4]}));
}
const allRatings=[],sections=[],deliverables=[],stepRows=[];
for(const s of data.steps){
 const dir='steps/'+String(s.number).padStart(2,'0')+'_'+safe(s.title);await fs.mkdir(path.join(out,dir),{recursive:true});
 const fields=data.schema_fields.filter(x=>x[0]===s.number),nodes=data.schema_nodes.filter(x=>x[0]===s.number);
 const schema=Workbook.create();
 table(schema,'Definition',`Step ${s.number}: output schema v3`,['Step','L1 Section','L2 Parameter','L3 Contract facets','L4 Data type','Atomic or composite','Required','Allowed values and validation','Definition','Reason','Priority','Source','Example','Node ID'],fields);
 table(schema,'Hierarchy',`Step ${s.number}: L1-L4 hierarchy`,['Step','Node ID','Parent ID','Level','Name','Priority','Atomic definition','Source'],nodes);
 table(schema,'Decisions','Schema decisions and depth',['Decision','Treatment'],[['Version','v3.0; owner freeze and independent review pending'],['Depth','L1 section>L2 field>L3 contract facets>L4 atomic definition. Matches D5 p.5.'],['Branch width','L3 has at most3 leaves. Dictionary and mapping records retain their necessary17/13 typed fields; do not split a single record to manufacture a score.'],['Keep','Exit-critical fields, explicit source ownership, constraints, failures, evidence and UNKNOWN treatment.'],['Exclude','Raw identity/card credentials, fabricated provider data, human approvals and unsupported unlimited-scale claims.'],['Exit',s.exit],['Source','D5 pp.5,8,12-13,17-19; D4 pp.30-37']] );
 await finish(schema,dir+'/a_Output_Schema_Definition.xlsx');
 const rating=Workbook.create(),detailRows=[],summaryRows=[],sr=[];
 for(const kind of ['Output Schema Definition','Schema Rating Scorecard','Output Document']){
  const ds=scoreSet(s,kind);const total=ds.reduce((a,x)=>a+x.contribution,0);
  summaryRows.push([kind,total,total/83*100,0,'Refine','Prepared v3; independent review pending']);
  for(const x of ds){detailRows.push([kind,x.dimension,x.weight,x.critical?'Yes':'No',x.measure,x.score,0,x.evidence,x.next,null,'Peer not reviewed']);allRatings.push([s.number,kind,x.dimension,x.weight,x.critical?'Yes':'No',x.measure,x.score,x.contribution,x.evidence,x.next]);}
 }
 const summary=table(rating,'Summary',`Step ${s.number}: three deliverable ratings`,['Deliverable','Full score /100','Observed score /100','Critical minimum','Decision','Basis'],summaryRows);
 const rs=table(rating,'Ratings',`Step ${s.number}: rating inputs and evidence`,['Deliverable','Dimension','Weight','Critical','Measure','Author score /5','Contribution','Evidence','Return stage','Peer score /5','Review status'],detailRows,{inputCols:[5,9]});
 rs.getRange('J6:J32').clear({applyTo:'contents'});
 rs.getRange('F6:F32').dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};rs.getRange('J6:J32').dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
 rs.getRange('G6:G32').formulas=detailRows.map((_,i)=>[`=C${i+6}*F${i+6}/5`]);
 rs.getRange('F6:F32').conditionalFormats.add('cellIs',{operator:'lessThan',formula:4,format:{fill:'#FFF1D6'}});
 for(let k=0;k<3;k++){const a=6+k*9,z=a+8,r=6+k;
  summary.getRange(`B${r}:E${r}`).formulas=[[`=SUM(Ratings!G${a}:G${z})`,`=B${r}/83*100`,`=MIN(Ratings!F${a},Ratings!F${a+3},Ratings!F${a+7})`,`=IF(B${r}<75,"Rework",IF(AND(B${r}>=90,D${r}>=4),"Accept","Refine"))`]];
 }
 for(const m of data.section_metrics.filter(x=>x.step===s.number))for(let level=1;level<=4;level++){
  const evidence=/NFR|Release|Gate|Privacy|privacy|Compatibility|Capacity|Scale cases|Source ownership/.test(m.section)?3:/Executed|portable|drift/.test(m.section)?5:4;
  const r=[s.number,m.section,level,m.priority,m.priority==='P0'?3:m.priority==='P1'?2:1,m.conformance?5:0,percentScore(m.fill),5,evidence,0,'Contract quality; readiness reflects declared execution/policy evidence'];sr.push(r);sections.push(r);
 }
 const ss=table(rating,'Section Ratings','Section, priority and L1-L4 ratings',['Step','Section','Level','Priority','Priority weight','Structure /5','Fill /5','Definition source /5','Evidence readiness /5','Rating /5','Basis'],sr);
 ss.getRange(`J6:J${sr.length+5}`).formulas=sr.map((_,i)=>[`=AVERAGE(F${i+6}:I${i+6})`]);
 table(rating,'Scorecard schema','Scorecard contract',['Parameter','Type','Required','Allowed values or rule','Definition'],[
 ['Deliverable','text',true,'Schema; scorecard; output','One of the three rated artifacts'],['Dimension','text',true,'Nine frozen dimensions','Quality criterion with disclosed evidence'],['Weight','integer',true,'0..100; sum100 per deliverable','Contribution budget'],['Critical','boolean label',true,'Yes;No','Critical below4 blocks acceptance'],['Author score','integer',true,'0..5','Provisional assessment;0 for unassessed evidence'],['Peer score','integer',false,'Blank until review;0..5','Future independent reviewer input'],['Contribution','formula',true,'Weight*author score/5','Weighted points'],['Evidence','text',true,'Actual source/test layer or explicit unassessed','Justification for the rating'],['Decision','formula',true,'Accept;Refine;Rework','Threshold plus critical floor, separate from production gate']]);
 table(rating,'Method','Scoring and evidence boundaries',['Topic','Definition'],method);
 await finish(rating,dir+'/b_Schema_Rating_Scorecard.xlsx');
 const output=Workbook.create();for(const sec of s.sections)table(output,sec.name,`Step ${s.number}: ${sec.name}`,sec.columns,sec.rows);
 await finish(output,dir+'/c_Output_Document.xlsx');
 const totals=summaryRows.map(x=>x[1]);s.score=.25*totals[0]+.25*totals[1]+.5*totals[2];s.deliverableScores=totals;s.priority=[2,3,6,7].includes(s.number)?'P1':'P0';s.files={schema:dir+'/a_Output_Schema_Definition.xlsx',scorecard:dir+'/b_Schema_Rating_Scorecard.xlsx',output:dir+'/c_Output_Document.xlsx'};
 stepRows.push([s.number,s.phase,s.title,s.priority,s.priority==='P0'?3:2,...totals,s.score,'Refine',s.sections.reduce((a,x)=>a+x.rows.length,0),s.sections.length]);
 for(const [kind,file] of Object.entries(s.files))deliverables.push([s.number,s.title,kind,file,'v3.0',data.date]);
 console.log('SAVED',s.number,s.title,'score',s.score.toFixed(1));
}
const master=Workbook.create();const end=9+data.steps.length;
const dash=table(master,'Combined Rating','Talentra: steps1-22 consolidated rating',['Step','Phase','Step title','Priority','Step weight','Schema /100','Scorecard /100','Output /100','Step score /100','Acceptance','Records','Sections'],stepRows,{start:9});
dash.getRange('A4').values=[['Combined /100']];dash.getRange('B4').formulas=[[`=SUMPRODUCT(E10:E${end},I10:I${end})/SUM(E10:E${end})`]];dash.getRange('B4').setNumberFormat('0.0');dash.getRange('B4').format.font={name:'Arial',size:16,bold:true,color:C.navy};
dash.getRange('D4').values=[['Production release']];dash.getRange('E4').values=[['OPEN - native, scale, provider and human evidence pending']];
dash.getRange('A6').values=[['Step=25% schema+25% scorecard+50% output. P0 weight3/P1 weight2.']];dash.getRange('A7').values=[['Platform coverage is step22 only. Requested artifacts are prepared; acceptance and production gates remain open.']];
const rr=table(master,'All Ratings','Author rating inputs and supporting evidence',['Step','Deliverable','Dimension','Weight','Critical','Measure','Score /5','Contribution','Evidence','Return stage'],allRatings,{inputCols:[6]});
rr.getRange(`H6:H${allRatings.length+5}`).formulas=allRatings.map((_,i)=>[`=D${i+6}*G${i+6}/5`]);rr.getRange(`G6:G${allRatings.length+5}`).dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
for(let i=0;i<data.steps.length;i++){const r=i+10,b=6+i*27;
 dash.getRange(`F${r}:J${r}`).formulas=[[`=SUM('All Ratings'!H${b}:H${b+8})`,`=SUM('All Ratings'!H${b+9}:H${b+17})`,`=SUM('All Ratings'!H${b+18}:H${b+26})`,`=F${r}*0.25+G${r}*0.25+H${r}*0.5`,`=IF(I${r}<75,"Rework",IF(AND(I${r}>=90,MIN('All Ratings'!G${b},'All Ratings'!G${b+3},'All Ratings'!G${b+7},'All Ratings'!G${b+9},'All Ratings'!G${b+12},'All Ratings'!G${b+16},'All Ratings'!G${b+18},'All Ratings'!G${b+21},'All Ratings'!G${b+25})>=4),"Accept","Refine"))`]];
}
table(master,'Deliverable Index','66 per-step deliverables',['Step','Step title','Kind','Relative file','Version','As of'],deliverables);
const phases=table(master,'Phase Ratings','Ratings by lifecycle phase',['Phase','Name','Requested steps','Priority weight','Contribution','Phase rating /100','Scope'],[...new Set(data.steps.map(x=>x.phase))].map(p=>[p,['Discover','Model','Prove','Platform'][p-1],data.steps.filter(x=>x.phase===p).length,0,0,0,p===4?'Step22 only; steps23-28 outside cap':'Artifact content prepared; release evidence remains open']));
for(let p=1;p<=4;p++){const r=p+5;phases.getRange(`D${r}:F${r}`).formulas=[[`=SUMIFS('Combined Rating'!E10:E${end},'Combined Rating'!B10:B${end},A${r})`,`=SUMPRODUCT(('Combined Rating'!B10:B${end}=A${r})*'Combined Rating'!E10:E${end}*'Combined Rating'!I10:I${end})`,`=E${r}/D${r}`]];}
const cap=table(master,'Capacity','Capacity assumptions and calculated bounds',['Driver','Value','Unit','Basis'],data.capacity_math,{inputCols:[1]});
const capStart=23;
const capRows=data.capacity_cases.map(x=>[x[1],x[2],x[4],x[5],x[6],0,0,0,0,0,0,0,0,x[7]]);
cap.getRange(`A${capStart}:N${capStart}`).values=[['Case','Candidates','Applications','Active users','API replicas','Base RPS','Burst RPS','DB concurrent work','API connection use','Connection headroom','Max API replicas','Data+index GiB','Two-copy GiB','Basis']];
cap.getRange(`A${capStart}:N${capStart+3}`).format={wrapText:true,rowHeight:60};cap.getRange(`A${capStart}:N${capStart}`).format.fill=C.navy;cap.getRange(`A${capStart}:N${capStart}`).format.font={name:'Arial',bold:true,color:'#FFFFFF'};
cap.getRange(`A${capStart+1}:N${capStart+3}`).values=capRows;
cap.getRange(`A${capStart}:N${capStart+3}`).format.columnWidth=23;
cap.getRange(`B${capStart+1}:E${capStart+3}`).format.fill=C.amber;
for(let i=0;i<3;i++){const r=capStart+1+i;cap.getRange(`F${r}:M${r}`).formulas=[[`=D${r}*$B$6`,`=F${r}*$B$8`,`=G${r}*$B$9*$B$10/$B$11`,`=E${r}*$B$14`,`=$B$12-$B$13-I${r}`,`=INT(($B$12-$B$13)/$B$14)`,`=(B${r}*$B$15+C${r}*$B$16)*(1+$B$17)/1073741824`,`=L${r}*$B$18`]];}
cap.getRange('A20').values=[['Planning assumptions only. Excludes child/history rows, resumes, queues, WAL and backups; measure before provisioning.']];
cap.getRange('A21').values=[['Max replicas is the connection ceiling for this database/pool budget. Beyond it, resize/rearchitect and remeasure.']];
cap.getRange(`F${capStart+1}:M${capStart+3}`).setNumberFormat('#,##0.0');
cap.getRange(`J${capStart+1}:J${capStart+3}`).conditionalFormats.add('cellIs',{operator:'lessThan',formula:0,format:{fill:'#FFE2DD',font:{color:'#9A2525',bold:true}}});
table(master,'Production Gates','Required production evidence',['Gate ID','Concern','Required evidence','Owner','Status','Reason'],data.release_gates);
table(master,'All Schemas','713 typed output parameters',['Step','L1 Section','L2 Parameter','L3 Contract facets','L4 Data type','Atomic or composite','Required','Allowed values and validation','Definition','Reason','Priority','Source','Example','Node ID'],data.schema_fields);
table(master,'Hierarchy','Complete L1-L4 schema tree',['Step','Node ID','Parent ID','Level','Name','Priority','Atomic definition','Source'],data.schema_nodes);
const maxFields=Math.max(...data.steps.flatMap(s=>s.sections.map(x=>x.columns.length)));
const allOutputs=data.steps.flatMap(s=>s.sections.flatMap(sec=>sec.rows.map((r,i)=>[s.number,sec.name,i+1,...r,...Array(maxFields-r.length).fill('')])));
table(master,'All Outputs','All populated records concatenated',['Step','Section','Record',...Array.from({length:maxFields},(_,i)=>'Field '+(i+1))],allOutputs);
table(master,'Field Mapping','Column interpretation for concatenated records',['Step','Section','Field number','Field name'],data.steps.flatMap(s=>s.sections.flatMap(sec=>sec.columns.map((h,i)=>[s.number,sec.name,i+1,h]))));
const ss=table(master,'Section Ratings','Section, priority and L1-L4 ratings',['Step','Section','Level','Priority','Priority weight','Structure /5','Fill /5','Definition source /5','Evidence readiness /5','Rating /5','Basis'],sections);
ss.getRange(`J6:J${sections.length+5}`).formulas=sections.map((_,i)=>[`=AVERAGE(F${i+6}:I${i+6})`]);
table(master,'Evidence','Measured evidence and explicit limits',['Measure','Value','Boundary'],Object.entries(data.summary).map(([k,v])=>[k,v,'Python/SQLite/static source; native PostgreSQL, provider, load and recovery gates separate']));
table(master,'Refinement Log','V3 refinement journey',['Change ID','Finding','Change','Affected artifacts','Verification'],data.refinement_log);
table(master,'Sources','Sources and retained evidence',['Source ID','Title','File or URL','Locator','Use'],data.sources);
table(master,'Method','Scoring, refresh and limitations',['Topic','Definition'],method);
master.recalculate();
const before=dash.getRange('B4').values[0][0],original=rr.getRange('G6').values[0][0];rr.getRange('G6').values=[[4]];master.recalculate();const changed=dash.getRange('B4').values[0][0];if(!(changed<before))throw Error('Rating edit propagation failed');rr.getRange('G6').values=[[original]];
const originalRatings=rr.getRange('G6:G32').values;rr.getRange('G6:G32').values=Array.from({length:27},()=>[5]);rr.getRange('G6').values=[[3]];master.recalculate();if(dash.getRange('J10').values[0][0]!=='Refine')throw Error('Critical rating gate failed');rr.getRange('G6:G32').values=originalRatings;
const oldReq=cap.getRange('B6').values[0][0],rps=cap.getRange('F24').values[0][0];cap.getRange('B6').values=[[oldReq*2]];master.recalculate();if(Math.abs(cap.getRange('F24').values[0][0]-rps*2)>1e-9)throw Error('Capacity input propagation failed');cap.getRange('B6').values=[[oldReq]];
master.recalculate();if(Math.abs(dash.getRange('B4').values[0][0]-before)>1e-9)throw Error('Rating restore failed');
data.combinedRating=dash.getRange('B4').values[0][0];data.phaseRatings=phases.getRange('A6:G9').values;data.capacityResults=cap.getRange('A24:N26').values;data.ratingRows=allRatings;data.sectionRatings=sections.map(r=>{r[9]=(r[5]+r[6]+r[7]+r[8])/4;return r;});data.method=method;data.deliverables=deliverables;
await finish(master,'Talentra_Combined.xlsx');
await fs.writeFile(path.join(root,'work/dashboard_data_v3.json'),JSON.stringify(data));
await fs.writeFile(path.join(out,'evidence/workbook_validation.json'),JSON.stringify({workbooks:67,previews:previewNumber,formulaEdit:{before,changed,restored:data.combinedRating},capacityInputTest:'PASS',criticalGateTest:'PASS',checks},null,2));
await fs.writeFile(path.join(root,'work/preview_index_v3.json'),JSON.stringify(sheetsRendered,null,2));
console.log('COMPLETE',JSON.stringify({rating:data.combinedRating,workbooks:67,sheets:previewNumber,records:allOutputs.length}));
