from __future__ import annotations
from .models import NormalizationReport
from .scanner import scan_repository
from .voids import build_void_graph
from .ledger import build_mass_ledger
from .protocol import validate_protocol_payload
def _clamp(x): return max(0.0,min(1.0,float(x)))
def _ratio(a,b): return 0.0 if not b else float(a)/float(b)
def normalize_payload(payload):
    scan=payload.get('scan',{}); ledger=payload.get('mass_ledger',{}); protocol=payload.get('protocol_report',{'valid':True}); total=max(float(scan.get('total_bytes') or ledger.get('total_bytes') or 0),1.0); layer=scan.get('layer_bytes') or {}; missing=set(scan.get('missing_surface') or [])
    vals={
      'source_mass_ratio':_clamp(_ratio(layer.get('source',0),total)/0.20), 'test_mass_ratio':_clamp(_ratio(layer.get('test',0),total)/0.10), 'ci_presence':0.0 if 'ci' in missing else 1.0,
      'schema_presence':0.0 if 'schemas' in missing else 1.0, 'security_presence':0.0 if 'security' in missing else 1.0, 'docs_ratio':_clamp(_ratio(layer.get('docs',0),total)/0.30),
      'valid_mass_ratio':_clamp(_ratio(ledger.get('valid_mass_bytes',0),max(ledger.get('target_valid_mass_bytes',1),1))), 'void_pressure':_clamp(1.0-min(float(ledger.get('voids_detected',0))/10.0,1.0)),
      'blocking_pressure':_clamp(1.0-min(float(ledger.get('blocking_voids',0))/5.0,1.0)), 'protocol_validity':1.0 if protocol.get('valid',True) else 0.0}
    structural=sum(vals[k] for k in ['source_mass_ratio','test_mass_ratio','ci_presence','schema_presence','security_presence','docs_ratio'])/6
    release=sum(vals[k] for k in ['valid_mass_ratio','void_pressure','blocking_pressure','protocol_validity'])/4
    return NormalizationReport('cmar-normalizer/1.4.1','baseline_clamped_unit_interval',scan.get('artifact_hash') or ledger.get('artifact_hash',''),{k:round(v,6) for k,v in vals.items()},{'source':0.20,'test':0.10,'docs':0.30},round(structural,6),round(release,6))
def normalize_github_activity(report,window_days=None):
    """Normalize a GitHub activity report into auxiliary unit-interval signals.

    Auxiliary evidence only: these signals never override repository quality.
    """
    d=report.to_dict() if hasattr(report,'to_dict') else dict(report or {})
    days=max(int(window_days or d.get('window_days') or 30),1)
    authed=bool(d.get('authenticated'))
    commits=float(d.get('commits_authored',0) or 0); pr_open=float(d.get('pull_requests_opened',0) or 0); pr_merged=float(d.get('pull_requests_merged',0) or 0)
    contrib=float(d.get('contribution_days',0) or 0); seen=float(d.get('repositories_seen',0) or 0); active=float(len(d.get('active_repositories') or []))
    private=d.get('private_repositories_if_visible')
    visibility=0.0 if not authed else (1.0 if private is not None else 0.5)
    sig={
      'commit_activity_ratio':_clamp((commits/days)/3.0) if authed else 0.0,
      'pr_merge_ratio':_clamp(_ratio(pr_merged,pr_open)) if authed else 0.0,
      'active_days_ratio':_clamp(_ratio(contrib,days)) if authed else 0.0,
      'repository_activity_ratio':_clamp(_ratio(active,seen)) if authed else 0.0,
      'github_visibility_signal':visibility,
    }
    return {k:round(v,6) for k,v in sig.items()}
def normalize_repository(root,target_valid_mass=1048576):
    scan=scan_repository(root); voids=build_void_graph(scan); ledger=build_mass_ledger(scan,voids,target_valid_mass); payload={'scan':scan.to_dict(),'voids':[v.to_dict() for v in voids],'repair_plan':{'artifact_hash':scan.artifact_hash,'status':'inline','actions':[]},'mass_ledger':ledger.to_dict()}; payload['protocol_report']=validate_protocol_payload(payload).to_dict(); return normalize_payload(payload)
