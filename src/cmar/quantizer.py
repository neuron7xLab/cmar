from __future__ import annotations
from .models import QuantizationReport
from .normalizer import normalize_payload, normalize_repository
TH=[0.20,0.40,0.65,0.85]; BU=['VOID','WEAK','PARTIAL','STRONG','RELEASE']
def _q(v):
    idx=sum(1 for t in TH if float(v)>=t); idx=min(idx,4); lo=0 if idx==0 else TH[idx-1]; hi=1 if idx>=len(TH) else TH[idx]; return BU[idx],idx,round(abs(float(v)-((lo+hi)/2)),6)
def quantize_normalized_report(norm):
    d=norm.to_dict() if hasattr(norm,'to_dict') else norm; vec=d.get('vector',d); state={}; ords={}; loss={}
    for k in sorted(vec): state[k],ords[k],loss[k]=_q(vec[k])
    mean=round(sum(ords.values())/max(len(ords),1),6); verdict='VOID' if any(v=='VOID' for v in state.values()) else ('RELEASE' if mean>=3.5 else 'STRONG' if mean>=2.5 else 'PARTIAL' if mean>=1.5 else 'WEAK')
    return QuantizationReport('cmar-quantizer/1.4.1','visible_threshold_bucket_quantization',TH,state,ords,loss,mean,verdict)
def quantize_artifact_state(payload): return quantize_normalized_report(normalize_payload(payload))
def quantize_repository(root,target_valid_mass=1048576): return quantize_normalized_report(normalize_repository(root,target_valid_mass))
