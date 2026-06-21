from __future__ import annotations
from .models import VoidNode
def _v(i,t,s,title,ev,act,block,w,bytes=4096): return VoidNode(i,t,s,title,title,ev,act,block,w,bytes)
def build_void_graph(scan):
    m=set(scan.missing_surface); v=[]
    if 'entrypoint' in m: v.append(_v('V-EXEC-001','execution_void','critical','No executable entrypoint detected',['entrypoints=[]'],'Add CLI entrypoint.',True,14))
    if 'package_metadata' in m: v.append(_v('V-CAP-001','capability_void','critical','No package metadata detected',['package_files=[]'],'Add pyproject.toml.',True,13))
    if 'tests' in m: v.append(_v('V-TEST-001','test_void','critical','No test layer detected',['tests_present=false'],'Add tests.',True,10,12000))
    if 'ci' in m: v.append(_v('V-CI-001','ci_void','critical','No CI gate detected',['ci_present=false'],'Add CI.',True,10))
    if 'license' in m: v.append(_v('V-REL-001','release_void','high','No license detected',['license_present=false'],'Add LICENSE.',True,8))
    if 'security' in m: v.append(_v('V-SEC-001','security_void','high','No security policy detected',['security_present=false'],'Add SECURITY.md.',False,7))
    if 'schemas' in m: v.append(_v('V-SCHEMA-001','schema_void','medium','No schema layer detected',['schemas_present=false'],'Add JSON schemas.',False,6,8000))
    if 'release_metadata' in m: v.append(_v('V-REL-002','release_void','medium','No release metadata detected',['release_metadata_present=false'],'Add release metadata.',False,6))
    if 'docs_heavy_artifact' in scan.risk_flags: v.append(_v('V-EVID-001','evidence_void','high','Docs-heavy weak executable mass',['risk_flag=docs_heavy_artifact'],'Increase executable/test mass.',True,11,16000))
    return sorted(v,key=lambda x:(not x.blocks_release,-x.weight,x.void_id))
