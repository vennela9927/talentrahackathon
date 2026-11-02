import fs from 'node:fs/promises';
import {pathToFileURL} from 'node:url';
const root='C:/Users/gauta/Downloads/Premium Placement/28_oct/Talentra/Talentra';
const skill='C:/Users/gauta/.codex/plugins/cache/openai-primary-runtime/presentations/26.1029.11837/skills/presentations';
const source='C:/Users/gauta/AppData/Local/Packages/OpenAI.Codex_2p2nqsd0c76g0/LocalCache/Roaming/Codex/web/Codex/artifact-sessions/exports/latest/b8050a477fdac5ca9ee920510701296f3bc5fd0c6d1d855530fcda0585f9a415/Talentra_Step_22.pptx';
await fs.copyFile(source,root+'/work/step22_ppt/candidate.pptx');
await fs.mkdir(root+'/outputs/talentra_step22_presentation',{recursive:true});
const {finalizePresentation}=await import(pathToFileURL(skill+'/container_tools/artifact_tool_utils.mjs').href);
const result=await finalizePresentation({
workspaceDir:root,candidatePath:root+'/work/step22_ppt/candidate.pptx',finalPath:root+'/outputs/talentra_step22_presentation/Talentra_Step_22_Mentor_Presentation.pptx',
pythonExecutable:'C:/Users/gauta/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe',
integrityValidatorPath:skill+'/container_tools/inspect_presentation_package_integrity.py',
layoutValidatorPath:skill+'/container_tools/inspect_presentation_layout_geometry.py',
layoutArgs:['--expected-slide-size-emu','12192000,6858000','--validate-heading-fit'],
fontPolicy:{basis:'design',families:['Aptos']},verifyArtifactToolImport:true,
receiptPath:root+'/work/step22_ppt/validation.json'
});
console.log(JSON.stringify(result,null,2));
