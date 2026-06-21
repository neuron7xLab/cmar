from __future__ import annotations
import hashlib, os
from pathlib import Path
from .models import FileRecord, ScanReport
EXCLUDE={'.git','__pycache__','.pytest_cache','.mypy_cache','.ruff_cache','.venv','venv','node_modules','dist','build'}
SRC={'.py','.rs','.go','.ts','.tsx','.js','.java','.c','.cpp','.h','.hpp'}
DOC={'.md','.rst','.txt','.adoc'}; CFG={'.toml','.json','.yaml','.yml','.ini','.cfg'}
def _sha(b:bytes)->str: return hashlib.sha256(b).hexdigest()
def _layer(rel:str,suf:str)->str:
    l=rel.lower(); name=Path(rel).name.lower(); parts=set(Path(rel).parts)
    if '.github/workflows' in l or name in {'.gitlab-ci.yml','azure-pipelines.yml'}: return 'ci'
    if 'security.md'==name or 'codeql' in l or 'dependabot' in l: return 'security'
    if 'schema' in l: return 'schema'
    if '/tests/' in '/'+l or name.startswith('test_') or name.endswith('_test.py'): return 'test'
    if '/docs/' in '/'+l or suf in DOC or name in {'readme.md','changelog.md','contributing.md','citation.cff','release_verdict.md','license'}: return 'docs'
    if suf in SRC: return 'source'
    if suf in CFG or name in {'makefile','dockerfile'}: return 'config'
    return 'other'
def scan_repository(root)->ScanReport:
    root=Path(root).resolve(); rec=[]; lb={}; lf={}
    for dp,dns,fns in os.walk(root):
        dns[:]=[d for d in dns if d not in EXCLUDE]
        for fn in fns:
            p=Path(dp)/fn
            if any(x in p.parts for x in EXCLUDE): continue
            try: b=p.read_bytes()
            except OSError: continue
            rel=str(p.relative_to(root)).replace('\\','/'); layer=_layer(rel,p.suffix.lower())
            r=FileRecord(rel,len(b),_sha(b),layer); rec.append(r); lb[layer]=lb.get(layer,0)+len(b); lf[layer]=lf.get(layer,0)+1
    dig=hashlib.sha256('\n'.join(sorted(r.path+r.sha256 for r in rec)).encode()).hexdigest()
    paths={r.path.lower() for r in rec}; names={Path(p).name.lower() for p in paths}
    entry=sorted({r.path for r in rec if r.path.endswith('cli.py') or r.path.endswith('__main__.py')} | ({'pyproject.toml'} if 'pyproject.toml' in paths else set()))
    pkgs=sorted(p for p in ['pyproject.toml','setup.py','setup.cfg','package.json','go.mod','cargo.toml'] if p in paths)
    ci='ci' in lf; tests='test' in lf; docs='docs' in lf; lic=any(n.startswith('license') for n in names); sec='security' in lf; sch='schema' in lf; rel='changelog.md' in names or 'citation.cff' in names or 'release_verdict.md' in names
    missing=[]
    for ok,name in [(entry,'entrypoint'),(pkgs,'package_metadata'),(tests,'tests'),(ci,'ci'),(docs,'docs'),(lic,'license'),(sec,'security'),(sch,'schemas'),(rel,'release_metadata')]:
        if not ok: missing.append(name)
    total=sum(r.bytes for r in rec); risks=[]
    if lb.get('source',0)>0 and not tests: risks.append('source_without_tests')
    if lb.get('source',0)>0 and not ci: risks.append('source_without_ci')
    if total and lb.get('docs',0)/total>0.65: risks.append('docs_heavy_artifact')
    return ScanReport('cmar-scan/1.4.1',str(root),dig,len(rec),total,dict(sorted(lb.items())),dict(sorted(lf.items())),sorted(rec,key=lambda x:x.bytes,reverse=True)[:20],entry,pkgs,ci,tests,docs,lic,sec,sch,rel,missing,risks,rec)
