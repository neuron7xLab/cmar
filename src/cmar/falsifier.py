from __future__ import annotations
from .models import FalsificationFinding, FalsificationReport
from .scanner import scan_repository
from .voids import build_void_graph
from .planner import build_repair_plan
from .ledger import build_mass_ledger
from .protocol import validate_protocol_payload
from .quantizer import quantize_artifact_state
INV=['tests_present','ci_present','schemas_present','entrypoint_present','protocol_valid','ledger_hash_matches_scan_hash','valid_mass_not_greater_than_total_mass','no_pass_with_blocking_voids','docs_not_dominating_executable_mass','no_release_bucket_with_failed_protocol']
def _f(c,s,field,m): return FalsificationFinding(c,s,field,m)
def falsify_payload(payload):
    scan=payload.get('scan',{}); ledger=payload.get('mass_ledger',{}); protocol=payload.get('protocol_report',{}); quant=payload.get('quantization_report',{}); miss=set(scan.get('missing_surface') or []); f=[]
    for key,sev in [('tests','critical'),('ci','critical'),('schemas','high'),('entrypoint','critical')]:
        if key in miss: f.append(_f('missing_'+key,sev,'scan.missing_surface',key+' absent'))
    if protocol and protocol.get('valid') is not True: f.append(_f('invalid_protocol','critical','protocol_report.valid','protocol rejected payload'))
    if scan.get('artifact_hash') and ledger.get('artifact_hash') and scan['artifact_hash']!=ledger['artifact_hash']: f.append(_f('ledger_hash_mismatch','critical','mass_ledger.artifact_hash','hash mismatch'))
    if ledger.get('valid_mass_bytes',0)>ledger.get('total_bytes',scan.get('total_bytes',0)): f.append(_f('valid_mass_exceeds_total','critical','mass_ledger.valid_mass_bytes','valid mass exceeds total'))
    if ledger.get('status')=='PASS' and ledger.get('blocking_voids',0)>0: f.append(_f('pass_with_blocking_voids','critical','mass_ledger.status','PASS with blocking voids'))
    layer=scan.get('layer_bytes') or {}; total=max(scan.get('total_bytes',0) or 0,1); exe=sum(layer.get(k,0) for k in ['source','test','ci','schema','security','config']);
    if layer.get('docs',0)/total>0.65 and layer.get('docs',0)>exe: f.append(_f('docs_heavy_weak_executable_mass','high','scan.layer_bytes','docs dominate executable mass'))
    if quant.get('verdict')=='RELEASE' and protocol and protocol.get('valid') is not True: f.append(_f('release_bucket_failed_protocol','critical','quantization_report.verdict','release quantization failed protocol'))
    verdict='FALSIFIED' if any(x.severity=='critical' for x in f) else ('PARTIAL' if f else 'NOT_FALSIFIED')
    return FalsificationReport('cmar-falsifier/1.4.1',verdict,f,INV)
def falsify_repository(root,target_valid_mass=1048576):
    scan=scan_repository(root); voids=build_void_graph(scan); plan=build_repair_plan(scan,voids); ledger=build_mass_ledger(scan,voids,target_valid_mass); payload={'scan':scan.to_dict(),'voids':[v.to_dict() for v in voids],'repair_plan':plan.to_dict(),'mass_ledger':ledger.to_dict()}; payload['protocol_report']=validate_protocol_payload(payload).to_dict(); payload['quantization_report']=quantize_artifact_state(payload).to_dict(); return falsify_payload(payload)
