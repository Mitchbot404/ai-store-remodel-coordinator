"""Reproducible offline comparison; live mode requires explicit reference approval.

This harness uses standalone synthetic fixtures, not the operational database.
No reference expectations are sent to any provider. No human scores are invented.
"""
import argparse
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from time import perf_counter

from coordinator.candidates import build_request, validate, MockProvider, CandidateError
from coordinator.analysis import MockAnalysisProvider, build_analysis_request, validate_analysis

ROOT = Path(__file__).resolve().parent


def run(mode='mock', *, dataset_path=None, approval_hash=None):
    path = Path(dataset_path or ROOT / 'evaluation' / 'cases.json')
    raw = path.read_bytes()
    dataset = json.loads(raw)
    digest = hashlib.sha256(raw).hexdigest()
    if mode == 'live':
        if approval_hash != digest:
            raise ValueError('Review the reference expectations and explicitly approve this dataset hash before live evaluation.')
        from coordinator.openai_provider import OpenAIProvider
        provider = OpenAIProvider()
    elif mode == 'mock_bounded':
        provider = MockAnalysisProvider()
    elif mode == 'mock':
        provider = MockProvider()
    elif mode == 'manual':
        provider = None
    else:
        raise ValueError('Unknown evaluation mode.')
    results = []
    for entry in dataset['cases']:
        original = deepcopy(entry['case'])
        started = perf_counter()
        result = {'case_id': entry['id'], 'mode': mode, 'human_assessment': None}
        stage = 'preflight'
        try:
            request = build_request(deepcopy(original), dataset['evaluated_at'])
            stage = 'generation_or_validation'
            if mode == 'manual':
                result.update(status='manual_review_pending', case=original)
            elif mode == 'mock':
                package = provider.generate(request)
                validate(package, request)
                result.update(status='validated', package=package, invocation_mode='deterministic_mock')
            else:
                generation = provider.analyze(request)
                validate_analysis(generation['analysis'], build_analysis_request(request))
                validate(request['template'], request)
                result.update(status='validated', package=request['template'], **generation)
        except (CandidateError, ValueError, KeyError, TypeError):
            result.update(status='rejected_or_failed', failure_stage=stage,
                          error='Preflight, provider or validation failed; no output accepted.')
        result['elapsed_seconds'] = round(perf_counter() - started, 6)
        assert entry['case'] == original
        results.append(result)
        # Do not continue paid attempts after an error or an ambiguous response.
        if mode == 'live' and result['status'] == 'rejected_or_failed' and stage != 'preflight':
            break
    reference_path = ROOT / 'evaluation' / 'reference-expectations.json'
    return {'dataset_version': dataset['dataset_version'], 'dataset_sha256': digest,
            'reference_sha256': hashlib.sha256(reference_path.read_bytes()).hexdigest(),
            'case_clock': dataset['evaluated_at'], 'executed_at': datetime.now(timezone.utc).isoformat(),
            'mode': mode, 'reference_status': dataset['reference_status'],
            'human_evaluation': 'NOT_PERFORMED', 'results': results}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['manual', 'mock', 'mock_bounded', 'live'], default='mock')
    parser.add_argument('--approval-hash', help='Exact reviewed dataset SHA256; live mode only')
    parser.add_argument('--output', required=True, help='Local JSON evidence destination')
    args = parser.parse_args()
    report = run(args.mode, approval_hash=args.approval_hash)
    target = Path(args.output)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print('Evaluation evidence written. Human assessments are pending.')
