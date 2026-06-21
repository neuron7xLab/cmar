from __future__ import annotations
from .models import MassLedger
def build_mass_ledger(scan, voids, target_valid_mass_bytes=1048576):
    valid=sum(scan.layer_bytes.get(k,0) for k in ['source','test','ci','schema','security','config','docs'])
    blocking=sum(1 for v in voids if v.blocks_release); hollow=max(scan.total_bytes-valid,0); ratio=round(hollow/max(scan.total_bytes,1),6)
    if blocking: status='BLOCKED'; verdict='Release is blocked by critical voids.'
    elif valid<target_valid_mass_bytes: status='PARTIAL_VALIDATED'; verdict='Valid structure exists but target mass is not reached.'
    else: status='PASS'; verdict='Artifact passes release gate and target valid mass.'
    return MassLedger('cmar-mass-ledger/1.4.1',scan.artifact_hash,target_valid_mass_bytes,scan.total_bytes,valid,hollow,len(voids),blocking,1.0 if not voids else 0.0,ratio,blocking>0,status,verdict)
