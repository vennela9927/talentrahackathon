"""Reproduce portable workflow fixtures in a new folder, without touching the release."""
import argparse,importlib.util,json
from pathlib import Path

def main():
 parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',type=Path,required=True);a=parser.parse_args()
 source=Path(__file__).resolve().parents[1]
 if a.output.exists():parser.error('--output must be a new, non-existing folder')
 spec=importlib.util.spec_from_file_location('workflow_library',Path(__file__).with_name('build_workflow_split.py'))
 lib=importlib.util.module_from_spec(spec);spec.loader.exec_module(lib)
 lib.OUT=a.output.resolve();lib.FAMILIES={f['code']:f for f in lib.load(source/'scenario_data/generation_summary.json')['families']}
 actors=lib.load(source/'catalogue/actors.json');workflows=lib.load(source/'catalogue/workflows.json');steps=lib.load(source/'catalogue/workflow_steps.json');dictionary=lib.load(source/'evidence/hybrid_dictionary.json')
 analytics,sets,cases=lib.workflow_sets(actors,workflows,steps,dictionary)
 tests=lib.rule_tests();lib.dump(a.output/'analytics.json',analytics);lib.dump(a.output/'rule_tests.json',tests)
 print(json.dumps({'workflow_sets':len(sets),'cases':len(cases),'portable_rule_checks':len(tests),'output':str(a.output.resolve()),'native_execution':False}))

if __name__=='__main__':main()
