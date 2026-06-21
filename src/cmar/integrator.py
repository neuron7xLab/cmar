from __future__ import annotations
import json
from pathlib import Path
from .models import IntegratedState
from .scanner import scan_repository
from .normalizer import normalize_payload, normalize_github_activity
from .quantizer import quantize_normalized_report
from .voids import build_void_graph
from .planner import build_repair_plan
from .ledger import build_mass_ledger
from .protocol import validate_protocol_payload
from .falsifier import falsify_payload
from .synthesis import synthesize_cross_stream
from .expander import compute_expansion

def _load_github_activity(github_activity):
    """Accept a report dict/object or a path to a github_activity JSON artifact."""
    if github_activity is None: return None
    if hasattr(github_activity,'to_dict'): return github_activity.to_dict()
    if isinstance(github_activity,dict): return github_activity
    if isinstance(github_activity,(str,Path)): return json.loads(Path(github_activity).read_text(encoding='utf-8'))
    raise TypeError('github_activity must be a path, dict, or report object')

def integrate_artifact_streams(root,target_valid_mass=1048576,github_activity=None):
    scan=scan_repository(root); sd=scan.to_dict(); norm=normalize_payload({'scan':sd,'mass_ledger':{'target_valid_mass_bytes':target_valid_mass},'protocol_report':{'valid':True}}); quant=quantize_normalized_report(norm); voids=build_void_graph(scan); plan=build_repair_plan(scan,voids); ledger=build_mass_ledger(scan,voids,target_valid_mass); payload={'scan':sd,'voids':[v.to_dict() for v in voids],'repair_plan':plan.to_dict(),'mass_ledger':ledger.to_dict()}; proto=validate_protocol_payload(payload); payload['protocol_report']=proto.to_dict(); payload['quantization_report']=quant.to_dict(); fals=falsify_payload(payload)
    if not proto.valid: verdict={'state':'PROTOCOL_REJECTED','gate':'FAIL_PROTOCOL','reason':'protocol rejected payload'}
    elif fals.verdict=='FALSIFIED': verdict={'state':'FALSIFIED','gate':'FAIL_FALSIFICATION','reason':'critical falsification findings exist'}
    elif ledger.release_blocked: verdict={'state':'VOID_BLOCKED','gate':'FAIL_RELEASE','reason':'blocking voids remain'}
    elif quant.verdict in {'RELEASE','STRONG'}: verdict={'state':'RELEASE_CANDIDATE','gate':'PASS','reason':'integrated release state accepted'}
    else: verdict={'state':'REPAIR_REQUIRED','gate':'CONTINUE_REPAIR','reason':'state below threshold'}
    gh=_load_github_activity(github_activity); gh_signals=None; synthesis=None; flow=['scan','normalize','quantize','voids','repair_plan','protocol','falsify','mass_ledger']
    if gh is not None:
        gh_signals=normalize_github_activity(gh); flow+=['github_activity','github_signals']
        # Auxiliary evidence only: GitHub activity never overrides repository quality.
        verdict={**verdict,'github_evidence':'auxiliary','github_overrides_quality':False}
    # Future-state projection: output of falsify+ledger becomes input to the expander.
    expansion=compute_expansion(ledger.to_dict(),history=[]); flow.insert(len(flow),'expansion')
    flow.append('integrated_verdict')
    state=IntegratedState('cmar-integrator/1.4.1',str(scan.root),flow,sd,norm.to_dict(),quant.to_dict(),[v.to_dict() for v in voids],plan.to_dict(),proto.to_dict(),fals.to_dict(),ledger.to_dict(),verdict,gh,gh_signals,None,expansion,expansion['potential_mass'],expansion['expansion_verdict'])
    if gh is not None:
        # Emergent join: output of the repo + github streams becomes input to synthesis.
        synthesis=synthesize_cross_stream(state.to_dict()); object.__setattr__(state,'cross_stream_synthesis',synthesis)
        if synthesis: flow.insert(flow.index('integrated_verdict'),'cross_stream_synthesis')
    return state
