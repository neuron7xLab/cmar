from __future__ import annotations
from dataclasses import asdict, dataclass, field
from typing import Any
@dataclass(frozen=True)
class FileRecord:
    path:str; bytes:int; sha256:str; layer:str
    def to_dict(self): return asdict(self)
@dataclass
class ScanReport:
    scanner_version:str; root:str; artifact_hash:str; total_files:int; total_bytes:int; layer_bytes:dict[str,int]; layer_files:dict[str,int]; largest_files:list[FileRecord]; entrypoints:list[str]; package_files:list[str]; ci_present:bool; tests_present:bool; docs_present:bool; license_present:bool; security_present:bool; schemas_present:bool; release_metadata_present:bool; missing_surface:list[str]; risk_flags:list[str]; files:list[FileRecord]=field(repr=False)
    def to_dict(self, include_files:bool=False):
        d=asdict(self)
        if not include_files: d.pop('files',None)
        return d
@dataclass(frozen=True)
class VoidNode:
    void_id:str; void_type:str; severity:str; title:str; description:str; evidence:list[str]; recommended_action:str; blocks_release:bool; weight:int; estimated_valid_bytes:int
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class RepairAction:
    action_id:str; void_id:str; title:str; target_paths:list[str]; command_hint:str; acceptance_gate:str; priority:float
    def to_dict(self): return asdict(self)
@dataclass
class RepairPlan:
    plan_version:str; artifact_hash:str; status:str; actions:list[RepairAction]
    def to_dict(self): return {'plan_version':self.plan_version,'artifact_hash':self.artifact_hash,'status':self.status,'actions':[a.to_dict() for a in self.actions]}
@dataclass
class MassLedger:
    ledger_version:str; artifact_hash:str; target_valid_mass_bytes:int; total_bytes:int; valid_mass_bytes:int; hollow_mass_bytes:int; voids_detected:int; blocking_voids:int; void_closure_rate:float; hollow_mass_ratio:float; release_blocked:bool; status:str; verdict:str
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class ProtocolIssue:
    code:str; severity:str; path:str; message:str
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class ProtocolReport:
    protocol_version:str; valid:bool; syntax_valid:bool; schema_valid:bool; semantic_valid:bool; issues:list[ProtocolIssue]
    def to_dict(self): return {'protocol_version':self.protocol_version,'valid':self.valid,'syntax_valid':self.syntax_valid,'schema_valid':self.schema_valid,'semantic_valid':self.semantic_valid,'issues':[i.to_dict() for i in self.issues]}
@dataclass(frozen=True)
class NormalizationReport:
    normalizer_version:str; method:str; artifact_hash:str; vector:dict[str,float]; baselines:dict[str,float]; structural_score:float; release_readiness:float
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class QuantizationReport:
    quantizer_version:str; method:str; thresholds:list[float]; state_vector:dict[str,str]; ordinal_vector:dict[str,int]; information_loss:dict[str,float]; mean_ordinal:float; verdict:str
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class FalsificationFinding:
    code:str; severity:str; field:str; message:str
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class FalsificationReport:
    falsifier_version:str; verdict:str; findings:list[FalsificationFinding]; checked_invariants:list[str]
    def to_dict(self): return {'falsifier_version':self.falsifier_version,'verdict':self.verdict,'findings':[f.to_dict() for f in self.findings],'checked_invariants':self.checked_invariants}
@dataclass(frozen=True)
class AutofillReport:
    autofill_version:str; root:str; created_files:list[str]; skipped_files:list[str]; before:dict[str,Any]; after:dict[str,Any]; success:bool; acceptance:dict[str,bool]
    def to_dict(self): return asdict(self)
@dataclass(frozen=True)
class IntegratedState:
    integrator_version:str; root:str; flow:list[str]; scan:dict[str,Any]; normalized_state:dict[str,Any]; quantized_state:dict[str,Any]; voids:list[dict[str,Any]]; repair_plan:dict[str,Any]; protocol_report:dict[str,Any]; falsification_report:dict[str,Any]; mass_ledger:dict[str,Any]; integrated_verdict:dict[str,Any]; github_activity:dict[str,Any]|None=None; github_signals:dict[str,float]|None=None; cross_stream_synthesis:dict[str,Any]|None=None; expansion:dict[str,Any]|None=None; potential_mass:int|None=None; expansion_verdict:str|None=None
    def to_dict(self): return asdict(self)
