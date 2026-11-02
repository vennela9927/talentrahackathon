import fs from 'node:fs/promises';
import path from 'node:path';
import {Workbook,SpreadsheetFile,FileBlob} from '@oai/artifact-tool';
const root=path.resolve(import.meta.dirname,'..');
const working=path.join(root,'work/hybrid_v4');
await fs.mkdir(working,{recursive:true});
if(process.argv.includes('--inspect')){
 const src=await SpreadsheetFile.importXlsx(await FileBlob.load('C:/Users/gauta/Downloads/Talentra_Master_Lifecycle_Steps_01_to_21.xlsx'));
 for(const [sheetName,range,file] of [['00_Overview_Dashboard','A1:H13','friend_overview.png'],['19_Data_Dictionary_v2','A17:G25','friend_dictionary.png']]){
  const b=await src.render({sheetName,range,scale:1,format:'png'});await fs.writeFile(path.join(working,file),new Uint8Array(await b.arrayBuffer()));
 }
 console.log((await src.inspect({kind:'region',sheetId:'Phase3_Scorecards',range:'A20:D35',maxChars:1600,tableMaxRows:4,tableMaxCols:4})).ndjson);
 process.exit(0);
}
const d=JSON.parse(await fs.readFile(path.join(working,'hybrid_data.json'),'utf8')),p=d.project;
const out=path.join(root,'outputs/talentra_hybrid_v4');await fs.mkdir(out,{recursive:true});
const wb=Workbook.create(),navy='#203B63',ink='#162A43';let tableId=0;
const column=n=>{let s='';for(n++;n;n=Math.floor((n-1)/26))s=String.fromCharCode(65+(n-1)%26)+s;return s;};
const literal=v=>v===null?'NULL - source value retained':typeof v==='object'?JSON.stringify(v):typeof v==='string'&&v.startsWith('=')?"'"+v:v;
function addSheet(name,title){const s=wb.worksheets.add(name);s.showGridLines=false;s.getRange('A2').values=[[title]];s.getRange('A2').format.font={name:'Arial',size:15,bold:true,color:navy};return s;}
function put(s,title,headers,rows,start=5,{archive=false,inputs=[]}={}){
 const e=column(headers.length-1),last=start+rows.length;
 if(start>5){s.getRange(`A${start-2}`).values=[[title]];s.getRange(`A${start-2}`).format.font={name:'Arial',size:12,bold:true,color:navy};}
 const rg=s.getRange(`A${start}:${e}${Math.max(last,start+1)}`);rg.format={font:{name:'Arial',size:10,color:ink},verticalAlignment:'top',wrapText:true,rowHeight:archive?45:76};
 for(let j=0;j<headers.length;j++)s.getRange(`${column(j)}${start}:${column(j)}${Math.max(last,start+1)}`).format.columnWidth=/^Step$|^Level$|^Weight$|score|Rating|Critical|Agreement|Nullable/i.test(headers[j])?16:/Definition|Statement|Evidence|Decision|Reason|Treatment|Meaning/i.test(headers[j])?65:36;
 s.getRange(`A${start}:${e}${start}`).values=[headers];s.getRange(`A${start}:${e}${start}`).format={fill:navy,font:{name:'Arial',size:10,bold:true,color:'#FFFFFF'},rowHeight:40,horizontalAlignment:'center',verticalAlignment:'center',wrapText:true};
 if(rows.length){s.getRange(`A${start+1}:${e}${last}`).values=rows.map(r=>r.map(literal));const t=s.tables.add(`A${start}:${e}${last}`,true,'Hybrid_'+(++tableId));t.showBandedRows=true;}
 for(const j of inputs)if(rows.length)s.getRange(`${column(j)}${start+1}:${column(j)}${last}`).format.fill='#FFF1D6';
 return last+5;
}
function sheet(name,title,headers,rows,options){const s=addSheet(name,title);put(s,title,headers,rows,5,options);s.freezePanes.freezeRows(5);s.freezePanes.freezeColumns(2);return s;}
const summary=addSheet('Hybrid Summary','Talentra: hybrid workbook and evidence-based rescore');
summary.getRange('A4:B12').values=[['Hybrid full rating /100',0],['Previous A rating /100',d.source_a_summary.score],['Change /100',0],['A existing physical columns',1250],['Hybrid field register',d.dictionary.length],['Additional design fields',d.proposed.length],['Source B dictionary fields',462],['Source B definition placeholders',d.source_b_summary.placeholder_definitions],['Approval','Refine - human interview and production evidence pending']];
summary.getRange('A4:B12').format={font:{name:'Arial',size:11,color:ink},rowHeight:32};summary.getRange('A4:A12').format.columnWidth=43;summary.getRange('B4:B12').format.columnWidth=70;summary.getRange('B4:B6').setNumberFormat('0.0');summary.getRange('B4').format.font={name:'Arial',size:18,bold:true,color:navy};
summary.getRange('A15').values=[['Use Step Scores for before/after ratings. Numbered tabs contain populated hybrid outputs. Output Schema and Hierarchy define their contracts.']];
summary.getRange('A17').values=[['Models: source A = GPT per user; source B = unknown. Source-reported native PASS claims are retained separately from verified hybrid results.']];
summary.getRange('A19').values=[['157 additions are design proposals, not deployed columns. Existing A baseline is preserved. B schema trees and a human interview were not supplied.']];
const scores=sheet('Step Scores','Before and after: all three deliverables',['Step','Phase','Canonical step','Priority','Step weight','A schema','A scorecard','A output','A combined','Hybrid schema','Hybrid scorecard','Hybrid output','Hybrid combined','Change','Acceptance'],d.expected_steps.map(r=>[...r,0,'Refine']));
const stats=new Map(d.comparison_stats.map(r=>[r[0],r]));
const inputs=new Map(d.consistency_inputs.map(r=>[r[0]+'|'+r[1],r[2]]));
const ratingRows=d.original_source_a_ratings.map(r=>{
 const isComparison=r[2]==='Consistency across runs',score=isComparison?inputs.get(r[0]+'|'+r[1]):r[6];
 let evidence=r[8];
 if(isComparison)evidence=r[1]==='Output Schema Definition'?'0: B references schema files but actual schema trees were not supplied.':r[1]==='Schema Rating Scorecard'?(r[0]>=13&&r[0]<=21?'B phase3 scorecard:19/27 criterion/weight/critical comparisons agree; score2/5.':'No matching B step scorecard supplied; unassessed0.'):`${stats.get(r[0])[2]}/${stats.get(r[0])[1]} unique comparison concepts agree. Score ${score}/5; fewer than5 concepts capped at2. Value-kind agreement does not assert identical physical schema.`;
 return [r[0],r[1],r[2],r[3],r[4],r[6],score,0,evidence,r[5]];
});
const ratings=sheet('Ratings','Frozen common rubric; editable hybrid author scores',['Step','Deliverable','Dimension','Weight','Critical','A score /5','Hybrid score /5','Contribution','Evidence','Measure'],ratingRows,{inputs:[6]});
ratings.getRange(`G6:G${ratingRows.length+5}`).dataValidation={rule:{type:'whole',operator:'between',formula1:0,formula2:5}};
ratings.getRange(`H6:H${ratingRows.length+5}`).formulas=ratingRows.map((_,i)=>[`=IF(ISNUMBER(G${i+6}),D${i+6}*G${i+6}/5,"Missing score")`]);
for(let i=0;i<22;i++){
 const row=i+6,b=6+i*27;const totals=[b,b+9,b+18].map(a=>`IF(COUNT(Ratings!G${a}:G${a+8})=9,SUM(Ratings!H${a}:H${a+8}),"Missing score")`);
 scores.getRange(`J${row}:O${row}`).formulas=[[...totals.map(x=>'='+x),`=IF(COUNT(J${row}:L${row})=3,J${row}*0.25+K${row}*0.25+L${row}*0.5,"Missing score")`,`=IF(ISNUMBER(M${row}),M${row}-I${row},"Missing score")`,`=IF(COUNT(J${row}:L${row})<3,"Missing score",IF(M${row}<75,"Rework",IF(AND(M${row}>=90,MIN(Ratings!G${b},Ratings!G${b+3},Ratings!G${b+7},Ratings!G${b+9},Ratings!G${b+12},Ratings!G${b+16},Ratings!G${b+18},Ratings!G${b+21},Ratings!G${b+25})>=4),"Accept","Refine")))`]];
}
scores.getRange('F6:N27').setNumberFormat('0.0');summary.getRange('B4').formulas=[['=IF(COUNT(\'Step Scores\'!M6:M27)=22,SUMPRODUCT(\'Step Scores\'!E6:E27,\'Step Scores\'!M6:M27)/SUM(\'Step Scores\'!E6:E27),"Missing score")']];summary.getRange('B6').formulas=[['=IF(ISNUMBER(B4),B4-B5,"Missing score")']];
sheet('Comparison Evidence','Normalized comparison decisions and original source values',['Comparison ID','Step','Decision or field','A value','B value','Agreement','B locator','Hybrid conclusion'],d.comparisons);
sheet('Comparison Summary','Agreement before reconciliation; sparse comparisons capped',['Step','Unique concepts','Agree','Different','Agreement rate','Output consistency /5','Boundary'],d.comparison_stats);
sheet('Scorecard Comparison','Source rubrics compared; ratings are not averaged',['Dimension','Property','A value','B value','Agree','Source'],d.scorecard_comparison);
sheet('Merge Decisions','Retain, enrich, reconcile or hold for evidence',['Decision ID','Topic','Finding','Hybrid treatment','Status','Source'],d.decisions);
sheet('Source Map','Semantic placement of every source B table',['Source block','B sheet','B section','Data rows','Canonical step','Canonical destination','Source cell','Mapping rule'],d.section_mapping);
sheet('Source B Claims','Source-reported results kept separate from hybrid verification',['Source block','Source cell','Context','Reported source values','Evidence boundary','Hybrid approval treatment'],d.source_claims,{archive:true});
const names=['Requirements','People_Roles','Features','NFRs','Workflows','Entities','Attributes','Lifecycles','Relationships','Dictionary_v1','Rules_v1','Privacy','Volumetrics','Sample_Data','Data_Tests','Workflow_Coverage','Refinement','Rules_v2','Hybrid_Dictionary','Test_Suite','Physical_Baseline','Integrations'];
const anchors=[];
for(const s of p.steps){
 const name=String(s.number).padStart(2,'0')+'_'+names[s.number-1],sh=addSheet(name,`Step ${s.number}: ${s.title}`);let start=5;
 for(const sec of s.sections){anchors.push([s.number,sec.name,name,start,sec.rows.length,sec.priority,sec.source]);start=put(sh,sec.name,sec.columns,sec.rows,start);}
 sh.freezePanes.freezeRows(5);sh.freezePanes.freezeColumns(2);console.log('POPULATED STEP',s.number);
}
sheet('Section Index','Find every populated area in the hybrid workbook',['Step','Section','Worksheet','Header row','Records','Priority','Source'],anchors);
sheet('Output Schema','Typed output schema for every hybrid area',['Step','L1 Section','L2 Parameter','L3 facets','L4 Data type','Required','Validation','Definition','Reason','Priority','Source','Node ID'],p.schema_fields);
sheet('Hierarchy','L1-L4 tree for all hybrid output contracts',['Step','Node ID','Parent ID','Level','Name','Priority','Definition','Source'],p.schema_nodes);
sheet('Source B Archive','Original non-empty source rows; no source formulas executed',['Source sheet','Excel row','Section context',...Array.from({length:11},(_,i)=>'Original '+column(i))],d.source_archive,{archive:true});
sheet('Sources','Input provenance and scope',['Source','File','Model','SHA256','Treatment'],[['A','Talentra_Combined.xlsx','GPT per user',d.source_a_summary.sha256,'Original unchanged;22-step design baseline retained'],['B',d.source_b_summary.file,'Unknown',d.source_b_summary.sha256,'Original unchanged;24sheets/462dictionary fields reconciled'],['D1-D5','Five PDFs from prior project','Not applicable','Recorded in original source register','User request governs; D3 numbering and D5 quality method retained']]);
sheet('Method','Scoring, use and evidence boundaries',['Topic','Rule'],[
 ['Scope','One hybrid workbook covering canonical steps1-22. B03/B04 remapped by subject; source IDs are namespaced.'],
 ['Scoring','Same A rubric weights14,14,9,18,9,9,9,8,10. Step=25% schema+25% scorecard+50% output. P0 weight3/P1 weight2. No averaging with source B93.'],
 ['New comparison credit','Only the independent-comparison dimension gains credit where supplied artifacts support it. B model is unknown. Source B schema trees were not supplied, so schema comparison stays0.'],
 ['Output comparison','Unique field-value-kind / topic concepts are counted once. Thresholds5>=98%,4>=90%,3>=75%,2>=50%,1>0. Fewer than5 concepts capped at2. Raw differences remain visible.'],
 ['Scorecard comparison','B contains step13-21 ratings.19/27 criterion meaning, weight and critical-flag comparisons agree (2/5). Other step scorecards remain unassessed.'],
 ['Human understanding','0 until an actual author interview. A provisional source score is not an interview. Accept requires>=90 and every critical>=4.'],
 ['Dictionary','1250 existing A fields retained;157 additional supporting fields are proposed. Default, FK, storage and retention remain explicit. Physical migrations and target runtime tests are pending.'],
 ['Source B quality','293/462 v2 definition/example rows contain dash definitions. A and useful B-v1 definitions replace placeholders in the canonical register.'],
 ['Business conflicts','Credit counts stay separate from currency amounts. Tax, pricing, retention and staff-assisted registration remain owned policy decisions.'],
 ['Verification','Merge/extraction checks, formula recalculation, score input propagation, missing-input gate and critical floor checked. A portable results retained as historical evidence; B native results source-reported.'],
 ['Kluster','Unavailable in this session; no Kluster verification claimed.'],
 ['Originals','Neither input workbook was overwritten. All non-empty B source rows are archived as values with original row locators. No hosting or publication.']
]);
sheet('Merge Checks','Independent merge and preservation checks',['Check','Expected','Actual','Result'],d.tests,{archive:true});
wb.recalculate();const actual=summary.getRange('B4').values[0][0];if(Math.abs(actual-d.expected_overall)>1e-8)throw Error('Score mismatch '+actual);
const keep=ratings.getRange('G6').values[0][0];ratings.getRange('G6').values=[[4]];wb.recalculate();if(!(summary.getRange('B4').values[0][0]<actual))throw Error('Score propagation');ratings.getRange('G6').clear({applyTo:'contents'});wb.recalculate();if(summary.getRange('B4').values[0][0]!=='Missing score')throw Error('Missing input guard');ratings.getRange('G6').values=[[keep]];
const keepBlock=ratings.getRange('G6:G32').values;ratings.getRange('G6:G32').values=Array.from({length:27},()=>[5]);ratings.getRange('G6').values=[[3]];wb.recalculate();if(scores.getRange('O6').values[0][0]!=='Refine')throw Error('Critical floor');ratings.getRange('G6:G32').values=keepBlock;wb.recalculate();
const errors=await wb.inspect({kind:'match',searchTerm:'#REF!|#DIV/0!|#VALUE!|#NAME\\?|#N/A|#NUM!|#NULL!|#SPILL!|#CALC!',options:{useRegex:true,maxResults:8},maxChars:1500});if(/"address"/.test(errors.ndjson||''))throw Error(errors.ndjson);
await fs.mkdir(path.join(working,'previews'),{recursive:true});
for(const sh of wb.worksheets.items){const preview=await wb.render({sheetName:sh.name,range:sh.name==='Hybrid Summary'?'A1:B12':'A1:F8',scale:1,format:'png'});await fs.writeFile(path.join(working,'previews',sh.name+'.png'),new Uint8Array(await preview.arrayBuffer()));}
const file=path.join(out,'Talentra_Hybrid_Master_Steps_01_22.xlsx');const x=await SpreadsheetFile.exportXlsx(wb);await x.save(file);
await fs.writeFile(path.join(out,'evidence/workbook_checks.json'),JSON.stringify({score:actual,previous:d.source_a_summary.score,change:actual-d.source_a_summary.score,formulaErrors:errors.ndjson,inputPropagation:'PASS',missingInputGuard:'PASS',criticalFloor:'PASS',sheets:wb.worksheets.items.length,stepScores:scores.getRange('A6:O27').values},null,2));
console.log('COMPLETE',JSON.stringify({file,score:actual,change:actual-d.source_a_summary.score,sheets:wb.worksheets.items.length,fields:d.dictionary.length,sourceBFields:462}));
