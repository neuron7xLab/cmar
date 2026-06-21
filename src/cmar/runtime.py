from __future__ import annotations
from dataclasses import asdict, dataclass
from typing import Any
from .normalizer import normalize_repository
from .quantizer import quantize_repository
from .integrator import integrate_artifact_streams
from .falsifier import falsify_repository
from .autofill import autofill_repository
from .github_activity import collect_github_activity
@dataclass(frozen=True)
class RuntimeExecutionReport:
    runtime_version:str; root:str; normalized_state:dict[str,Any]; quantized_state:dict[str,Any]; integrated_state:dict[str,Any]; falsification_report:dict[str,Any]; autofill_report:dict[str,Any]|None; final_status:str; github_activity:dict[str,Any]|None=None
    def to_dict(self): return asdict(self)
def run_runtime_pipeline(root,target_valid_mass=1048576,autofill=False,github_owner=None,days=30):
    norm=normalize_repository(root,target_valid_mass); quant=quantize_repository(root,target_valid_mass)
    gh=collect_github_activity(github_owner,days).to_dict() if github_owner else None
    integ=integrate_artifact_streams(root,target_valid_mass,github_activity=gh); fals=falsify_repository(root,target_valid_mass); ar=autofill_repository(root,target_valid_mass) if autofill else None
    final='FAIL' if fals.verdict=='FALSIFIED' else ('PASS' if integ.integrated_verdict['gate']=='PASS' else 'PARTIAL')
    return RuntimeExecutionReport('cmar-runtime/1.4.1',str(root),norm.to_dict(),quant.to_dict(),integ.to_dict(),fals.to_dict(),ar.to_dict() if ar else None,final,gh)
