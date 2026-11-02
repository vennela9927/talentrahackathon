import fs from 'node:fs/promises';
import path from 'node:path';
import {FileBlob,SpreadsheetFile} from '@oai/artifact-tool';
const root=path.resolve(import.meta.dirname,'..'),out=path.join(root,'outputs/talentra_step22_mini_seed_v7'),work=path.join(root,'work/workflow_split_v7');
const data=JSON.parse(await fs.readFile(path.join(work,'project.json'),'utf8')),w=data.workflows.find(w=>w.workflow_id==='WF-19');
if(!w.actor_ids.includes('ACT-04'))w.actor_ids.push('ACT-04');w.actor_ids.sort();
await fs.writeFile(path.join(work,'project.json'),JSON.stringify(data,null,2));await fs.writeFile(path.join(out,'catalogue/mini_seed_project.json'),JSON.stringify(data,null,2));await fs.writeFile(path.join(out,'catalogue/workflows.json'),JSON.stringify(data.workflows,null,2));
const sections=JSON.parse(await fs.readFile(path.join(work,'added_sections.json'),'utf8'));const section=sections.find(s=>s.name==='29_Workflow catalogue');const row=section.rows.find(r=>r[0]==='WF-19');row[7]=w.actor_ids.join(';');await fs.writeFile(path.join(work,'added_sections.json'),JSON.stringify(sections,null,2));
for(const rel of ['steps/22_Integration_and_Source_Mapping/c_Output_Document.xlsx','Talentra_Combined.xlsx']){
 const book=await SpreadsheetFile.importXlsx(await FileBlob.load(path.join(out,rel)));
 book.worksheets.getItem('29_Workflow catalogue').getRange('H24').values=[[row[7]]];
 const flowSheet=book.worksheets.getItem('29_Workflow catalogue');flowSheet.getRange('F5:F32').format.columnWidth=72;flowSheet.getRange('A6:J32').format.rowHeight=100;
 if(rel==='Talentra_Combined.xlsx'){
  const sh=book.worksheets.getItem('All Outputs');const existing=JSON.parse(sh.getRange('E19878').values[0][0]);if(existing[0]!=='WF-19')throw Error('Unexpected row');sh.getRange('E19878').values=[[JSON.stringify(row)]];
 }
 book.recalculate();if(rel.endsWith('c_Output_Document.xlsx')){const preview=await book.render({sheetName:'29_Workflow catalogue',range:'A1:F9',scale:1,format:'png'});await fs.writeFile(path.join(work,'previews/output_29_Workflow catalogue.png'),new Uint8Array(await preview.arrayBuffer()));}await(await SpreadsheetFile.exportXlsx(book)).save(path.join(out,rel));
}
const readme=path.join(out,'README.md');if(!(await fs.readFile(readme,'utf8')).includes('The compact combined workbook'))await fs.appendFile(readme,'\nThe compact combined workbook retains all 22 steps as concatenated records plus typed mini/seed tabs. The complete original master is preserved at prior_v6/Talentra_Combined.xlsx. Guest participates in the public-search entry of WF-19 only. Workflow participation does not grant permission for the other actors\' actions. The primary owners remain explicit in each step.\n');
console.log('All 27 actors have a participating workflow; source action owners preserved');
