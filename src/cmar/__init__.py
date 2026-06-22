"""CMAR Cognitive Mass Autofill Runtime."""
__version__='1.9.0'
from .scanner import scan_repository
from .normalizer import normalize_repository
from .quantizer import quantize_repository
from .voids import build_void_graph
from .planner import build_repair_plan
from .ledger import build_mass_ledger
from .protocol import validate_protocol_payload
from .falsifier import falsify_repository
from .autofill import autofill_repository
from .integrator import integrate_artifact_streams
from .runtime import run_runtime_pipeline

from .audit_stream import scan_audit_package, project_audit_to_cmar, integrate_audit_with_cmar

from .corpus_eval import evaluate_corpus

from .github_activity import collect_github_activity, GitHubActivityReport
from .normalizer import normalize_github_activity
from .synthesis import synthesize_cross_stream
from .expander import compute_expansion
from .stats import compute_owner_stats, render_markdown
