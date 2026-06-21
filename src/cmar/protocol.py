from __future__ import annotations
from .models import ProtocolIssue, ProtocolReport
def _i(c,s,p,m): return ProtocolIssue(c,s,p,m)
def validate_protocol_payload(payload, protocol=None):
    issues=[]
    for k in ['scan','voids','repair_plan','mass_ledger']:
        if k not in payload: issues.append(_i('missing_top_level','critical',k,f'missing {k}'))
    scan=payload.get('scan',{}); ledger=payload.get('mass_ledger',{}); voids=payload.get('voids',[])
    if scan.get('artifact_hash') and ledger.get('artifact_hash') and scan['artifact_hash']!=ledger['artifact_hash']: issues.append(_i('hash_mismatch','critical','mass_ledger.artifact_hash','ledger hash must match scan hash'))
    if ledger.get('blocking_voids',0)>0 and ledger.get('release_blocked') is not True: issues.append(_i('blocking_voids_not_blocking','critical','mass_ledger.release_blocked','blocking voids must block release'))
    if ledger.get('voids_detected') is not None and ledger.get('voids_detected')!=len(voids): issues.append(_i('void_count_mismatch','high','mass_ledger.voids_detected','void count mismatch'))
    if ledger.get('valid_mass_bytes',0)>ledger.get('total_bytes',scan.get('total_bytes',0)): issues.append(_i('valid_mass_exceeds_total','critical','mass_ledger.valid_mass_bytes','valid mass exceeds total mass'))
    semantic=not any(x.severity=='critical' for x in issues); schema=not any(x.code.startswith('missing') for x in issues)
    return ProtocolReport('cmar-protocol/1.4.1', semantic and schema, True, schema, semantic, issues)
