from __future__ import annotations
from dataclasses import asdict, dataclass
from pathlib import Path
@dataclass(frozen=True)
class RepairResult:
    root:str; mode:str; created_files:list[str]; skipped_files:list[str]; status:str
    def to_dict(self): return asdict(self)
def _pkg(root):
    n=root.name.lower().replace('-','_'); return ''.join(c for c in n if c.isalnum() or c=='_') or 'artifact'
def _w(root,rel,txt,created,skipped,overwrite=False):
    p=root/rel
    if p.exists() and not overwrite: skipped.append(rel); return
    p.parent.mkdir(parents=True,exist_ok=True); p.write_text(txt,encoding='utf-8'); created.append(rel)
def apply_template_repairs(root, overwrite=False):
    root=Path(root).resolve(); pkg=_pkg(root); c=[]; s=[]
    _w(root,'pyproject.toml',f"""[build-system]\nrequires=["setuptools>=68"]\nbuild-backend="setuptools.build_meta"\n[project]\nname="{pkg}"\nversion="0.1.0"\nrequires-python=">=3.10"\n[project.scripts]\n{pkg}="{pkg}.cli:main"\n[tool.setuptools.packages.find]\nwhere=["src"]\n""",c,s,overwrite)
    _w(root,f'src/{pkg}/__init__.py','__version__="0.1.0"\n',c,s,overwrite)
    _w(root,f'src/{pkg}/cli.py','def main():\n    print("artifact operational")\n    return 0\n',c,s,overwrite)
    _w(root,'tests/test_cli.py',f'from {pkg}.cli import main\ndef test_cli():\n    assert main()==0\n',c,s,overwrite)
    _w(root,'.github/workflows/ci.yml','name: CI\non: [push, pull_request]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n      - uses: actions/setup-python@v5\n        with: {python-version: "3.12"}\n      - run: python -m pip install -e .\n      - run: python -m unittest discover -s tests\n',c,s,overwrite)
    _w(root,'SECURITY.md','# Security\n\nReport vulnerabilities privately.\n',c,s,overwrite)
    _w(root,'LICENSE','MIT License\n',c,s,overwrite)
    _w(root,'README.md','# Generated Artifact\n',c,s,overwrite)
    _w(root,'CHANGELOG.md','# Changelog\n',c,s,overwrite)
    _w(root,'RELEASE_VERDICT.md','# Release Verdict\n',c,s,overwrite)
    _w(root,'schemas/artifact.schema.json','{"$schema":"https://json-schema.org/draft/2020-12/schema","type":"object"}\n',c,s,overwrite)
    return RepairResult(str(root),'template',c,s,'CREATED' if c else 'NOOP')
