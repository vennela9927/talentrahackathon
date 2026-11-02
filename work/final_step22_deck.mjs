import fs from 'node:fs/promises';
const ROOT='C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra';
export const BUILD=ROOT+'/work/final_step22_ppt';
export const PROJECT=ROOT+'/outputs/talentra_step22_mini_seed_v7';
const ink='#182B43',blue='#345F96',muted='#627187';
function txt(s,t,x,y,w,h,size=28,bold=false,color=ink){const a=s.shapes.add({geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});a.text=t;a.text.style={typeface:'Aptos',fontSize:size,bold,color,verticalAlignment:'middle',insets:0,wrap:'word'};return a;}
function node(s,t,x,y,w=260,h=85){const a=s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:h},fill:'#EAF0F7',line:{fill:'#D6E0EC',width:1}});a.text=t;a.text.style={typeface:'Aptos',fontSize:26,bold:true,color:ink,alignment:'center',verticalAlignment:'middle',insets:12};return a;}
const link=(s,a,b,from='right',to='left')=>s.shapes.connect(a,b,{kind:'elbow',fromSide:from,toSide:to,line:{fill:blue,width:2},tail:{type:'arrow',width:'med',length:'med'}});
function table(s,headers,rows,widths,height=360,y=185){const a=s.tables.add({rows:rows.length+1,columns:headers.length,left:64,top:y,width:1152,height,columnWidths:widths,values:[headers,...rows].map(r=>r.map(String))});for(let r=0;r<=rows.length;r++)for(let c=0;c<headers.length;c++){const t=a.getCell(r,c);t.fill=r===0?ink:r%2?'#FFFFFF':'#EEF3F8';t.text.style={typeface:'Aptos',fontSize:25,bold:r===0,color:r===0?'#FFFFFF':ink,verticalAlignment:'middle',insets:10,wrap:'word'};}a.borders.assign({fill:'#D6E0EC',width:1});return a;}
function slide(p,title,sub,ref,notes){const s=p.slides.add({width:1280,height:720});s.background.fill='#FFFFFF';txt(s,title,64,42,1150,65,42,true);txt(s,sub,64,112,1150,55,25,false,muted);txt(s,ref,64,650,1090,45,17,false,muted);s.speakerNotes.text='SAY\n'+notes+'\n\nSHOW\n'+ref+'\n\nEXACT PROJECT PATH\n'+PROJECT+'\n\nSource: current v7 catalogue, workbooks, saved-data analytics and portable evidence. All data is synthetic. Proposals and native/runtime gates remain explicitly open.';return s;}
export async function update(p){
 await fs.mkdir(BUILD+'/previews',{recursive:true});
 const data=JSON.parse(await fs.readFile(PROJECT+'/catalogue/mini_seed_project.json','utf8'));
 p.slides.keep(Array.from({length:15},(_,i)=>i));
 // Refresh retained content without changing the established design.
 for(const s of p.slides.items){
  for(const q of s.shapes.items){let t=String(q.text??'');if(!t)continue;
   t=t.replace('Mentor presentation / 30 October 2026','Final mentor presentation / 2 November 2026').replace('26 populated sections','36 populated sections').replace('1,500 typed samples    12 portable cases    Full saved-file invariant checks','Prior v6: 1,500 typed samples     V7: 50 portable rule cases');
   if(t==='Documentary quality and full-rubric approval measure different things')t='Prior v6 scores. The new extension awaits independent and human review.';
   q.text=t;
  }
  s.speakerNotes.text=String(s.speakerNotes.text).replaceAll('talentra_step22_mentor_v6','talentra_step22_mini_seed_v7').replace('Source basis: saved v6 Step 22 workbooks','Source basis: v6 business data plus the v7 mini/seed extension').replace('The output workbook contains the populated records across 26 sections.','The output workbook retains 26 sections and adds 10 mini/seed sections.');
 }
 let s=slide(p,'Mini and seed versions','Different versions support explanation and larger scenario analysis','Output Excel: 27_Mini seed versions / Dashboard: Mini and seed',
 'Sir, I split the data into two versions. Mini is a small linked sample that is easy to inspect. Seed preserves the full saved synthetic population. Mini contains 120 journeys covering six job families and ten current outcomes, with two examples of each combination. It also contains 100 gig applications. Its balanced selection changes its conversion rates, so I use seed results for the full scenario. Fifteen lakh means 1.5 million journeys. Applications remain a subset.');
 table(s,['Saved dataset','Mini','Seed'],[['Candidate-job journeys','120','15,00,000'],['Submitted applications','96','6,69,375'],['Stage events','684','41,94,321'],['Job requirements','120','20,000'],['Gig applications','100','50,000']],[550,280,322],350);
 txt(s,'Mini supports coverage checks. Seed preserves the full synthetic cohort.',72,570,1120,65,29,true,blue);

 s=slide(p,'27 actors and 168 workflow steps','The catalogue groups the work into eight business areas','Output Excel: 28_Actor catalogue, 29_Workflow catalogue, 30_Workflow steps',
 'The existing project supplied 18 personas and 116 operations. With your approval, I derived nine additional actor contexts and 52 detailed steps. That gives 27 actor contexts and 168 workflow operations across 27 workflows. The additions remain proposals. Provider and service contexts do not mean 27 newly implemented security roles. These 168 operations are inside the project and are different from the numbered development lifecycle steps. The actor filter shows participating workflows while each step keeps its primary owner.');
 const groups=[...new Set(data.workflows.map(w=>w.group))];table(s,['Business group','Workflows','Steps'],groups.map(g=>[g,data.workflows.filter(w=>w.group===g).length,data.steps.filter(st=>data.workflows.find(w=>w.workflow_id===st.workflow_id).group===g).length]),[780,180,192],410,175);
 txt(s,'18 retained + 9 proposed actors      116 retained + 52 proposed steps',72,598,1120,38,27,true,blue);
 s.speakerNotes.append('\n\nALL 27 ACTOR CONTEXTS\n'+data.actors.map(a=>a.actor_id+' '+a.actor+' — '+a.status).join('\n'));

 s=slide(p,'Smaller sets for every workflow','27 workflows have a mini set and a seed set','Folders: mini/workflows/WF-01 … WF-27 and seed/workflows/WF-01 … WF-27',
 'Each workflow has its own manifest, generated cases, step-example references and analytics. Across two versions this creates 54 workflow sets. Mini uses six example cases per workflow, while seed uses sixty. Each includes a valid case, cross-account input, missing input, blocking, a duplicate and a stale version. These run a portable envelope guard. They do not execute native business transactions. Field examples record the data elements associated with every step. Shared business files retain their own record grain.');
 const w=node(s,'Choose one workflow',64,215,260,90),mi=node(s,'Mini\n6 cases',430,195,260,90),se=node(s,'Seed\n60 cases',430,360,260,90),out=node(s,'Case outcomes and\nstep examples',930,275,280,110);link(s,w,mi);link(s,w,se);link(s,mi,out);link(s,se,out);
 txt(s,'54 workflow sets, with analytics for each set',72,510,1120,62,36,true,blue);txt(s,'12 additional family sets contain smaller journey and gig files',72,588,1120,45,27);

 s=slide(p,'Job-category and gig-fulfilment rules','25 declared rules with 50 recorded portable outcomes','Output Excel: 31_Category and gig rules, 35_Rule test outcomes',
 'I made the important business rules explicit. Family codes determine collar, branch and function, while engagement remains separate. Candidates own registration and offer response. Account and blocking rules protect access. Hiring stages follow the permitted order. A gig worker applies to a requester. Accepted assignments need valid windows. The external system owns fulfilment and earnings, and only the owning requester can rate completed work. Twenty-five valid and twenty-five refusal cases produced the expected portable results. Runtime enforcement still needs separate evidence.');
 table(s,['Area','Required business condition'],[['Job classification','Valid family, collar, branch and function'],['Hiring progression','Screen, apply, decide, offer, accept and join in order'],['Access and privacy','Correct organisation, ownership and blocking'],['Gig application','Worker applies to requester with a valid time window'],['Gig outcomes','External completion and nonnegative earnings'],['Gig rating','Owning requester rates completed work only']],[350,802],390,180);

 s=slide(p,'Example: external gig workflow analytics','WF-24 shows the effect of changing the fixture version','Dashboard: Mini and seed / Workflow set WF-24 / Smaller workflow-set analytics',
 'Here is a simple example that I can demonstrate. For WF-24, mini has six cases. One valid example emits six step examples. Five cases are refused or treated as duplicates. Seed has sixty cases. Ten valid examples emit sixty step examples. Both versions cover all six defined steps. These acceptance counts refer to example envelopes, not real gig application acceptance. The business gig acceptance rate is a separate KPI calculated from the gig dataset. Reproduction matched the recorded workflow fixture files.');
 table(s,['WF-24 measure','Mini','Seed'],[['Generated cases','6','60'],['Accepted example envelopes','1','10'],['Refused or duplicate envelopes','5','50'],['Emitted step examples','6','60'],['Defined steps covered','6 / 6','6 / 6']],[620,266,266],345,185);
 txt(s,'Example acceptance and business hiring acceptance use different denominators',72,570,1120,65,29,true,blue);

 s=slide(p,'Mentor demonstration and final conclusion','A short route through the current dashboard','Open index.html inside outputs/talentra_step22_mini_seed_v7',
 'To demonstrate this, I open index.html in Chrome or Edge and choose Mini and seed. I select a version, business group and workflow. The page shows the generated set, its actions, associated data and analytics. The shortcuts open actors, steps and business rules. Step outputs has the detailed Step 22 Mini Seed sections, while Schemas displays L1 through L4. My conclusion is that Step 22 now connects the business scenario to owned data and reviewable evidence. Mini makes the design easier to explain, and seed preserves the larger synthetic scenario. Native SQL, concurrency, authorization, provider and load gates remain open.');
 table(s,['Show this','Dashboard location'],[['Mini and seed comparison','Mini and seed / Dataset version'],['One workflow and its analytics','Workflow group, Workflow set and Actor context filters'],['All 27 actors and 168 steps','Actor catalogue and Workflow steps shortcuts'],['Business rules and data elements','Business rules, Field examples and step table'],['Detailed deliverables and hierarchy','Step outputs / Step 22 / Mini Seed sections, then Schemas']],[470,682],350,185);
 txt(s,'Business meaning, workflow actions and source fields now have traceable evidence',72,567,1120,65,29,true,blue);
 s.speakerNotes.append('\n\nEXACT FILES\n'+['index.html','steps/22_Integration_and_Source_Mapping/a_Output_Schema_Definition.xlsx','steps/22_Integration_and_Source_Mapping/b_Schema_Rating_Scorecard.xlsx','steps/22_Integration_and_Source_Mapping/c_Output_Document.xlsx','Talentra_Combined.xlsx','catalogue/mini_seed_project.json','evidence/mini_seed_validation.json'].map(f=>PROJECT+'/'+f).join('\n'));
 // Keep the narrative compact, with the new split close to the domain explanation.
 const order=[0,1,2,15,3,4,5,16,6,7,8,17,9,18,10,11,12,13,14,19,20];p.slides.reorder(order.map(i=>'sl/'+p.slides.items[i].id));
 for(let i=0;i<p.slides.items.length;i++){
  const sl=p.slides.items[i];for(const q of sl.shapes.items){if(q.position.left===1170&&q.position.top===659)q.text=String(i+1).padStart(2,'0');}
  sl.speakerNotes.append('\n\nPresentation scope: Step 22 only. The current project uses 27 actor contexts and 168 workflow operations. Prior v6 ratings are carried forward, not a new v7 approval.');
 }
 return {slides:p.slides.items.length,project:PROJECT};
}
