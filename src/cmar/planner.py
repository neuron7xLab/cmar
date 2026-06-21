from __future__ import annotations
from .models import RepairAction, RepairPlan
def build_repair_plan(scan, voids):
    acts=[]
    for n,v in enumerate(voids,1):
        targets={'execution_void':['src/<pkg>/cli.py','pyproject.toml'],'capability_void':['pyproject.toml'],'test_void':['tests/'],'ci_void':['.github/workflows/ci.yml'],'security_void':['SECURITY.md'],'schema_void':['schemas/'],'release_void':['CHANGELOG.md','RELEASE_VERDICT.md'],'evidence_void':['src/','tests/']}.get(v.void_type,['docs/'])
        pr=round(v.weight*(2 if v.blocks_release else 1)/(v.estimated_valid_bytes/4096),4)
        acts.append(RepairAction(f'R-{n:03d}',v.void_id,v.title,targets,v.recommended_action,'machine gate must pass',pr))
    return RepairPlan('cmar-repair-plan/1.4.1',scan.artifact_hash,'NO_ACTIONS_REQUIRED' if not acts else 'REPAIR_REQUIRED',sorted(acts,key=lambda a:(-a.priority,a.action_id)))
