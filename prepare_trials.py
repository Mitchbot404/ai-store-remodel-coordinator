"""Prepare private, offline worksheets after the live run. Never sends requests."""
import json
from pathlib import Path

from coordinator.analysis import build_analysis_request, render_analysis
from coordinator.candidates import build_request
from live_evaluation import DATA_HASH, REFERENCE_HASH, JOURNAL, ROOT, verified_cases

ORDER = [
    ('S1', ('Manual', 'Mock', 'Live')), ('S2', ('Mock', 'Live', 'Manual')),
    ('S3', ('Live', 'Manual', 'Mock')), ('S4', ('Manual', 'Live', 'Mock')),
    ('S5', ('Live', 'Mock', 'Manual')),
]


def worksheets(journal=JOURNAL, target=None):
    requests = verified_cases()
    rows = [json.loads(line) for line in journal.read_text(encoding='utf-8').splitlines()]
    if not rows or rows[0].get('dataset_sha256') != DATA_HASH or rows[0].get('reference_sha256') != REFERENCE_HASH:
        raise ValueError('Evaluation journal does not match the approved experiment.')
    live = {r['case_id']: r for r in rows if r.get('repetition') == 1}
    mock = json.loads((ROOT / 'evaluation/results/mock-bounded.json').read_bytes())
    mocks = {r['case_id']: r for r in mock['results']}
    dataset = json.loads((ROOT / 'evaluation/cases.json').read_bytes())
    cases = {entry['id']: entry['case'] for entry in dataset['cases']}
    target = Path(target or ROOT / 'data' / 'phase6a-personal-trials')
    target.mkdir(parents=True, exist_ok=False)  # Protect completed worksheets.
    guide = (ROOT / 'docs/manual-review-exercise.md').read_text(encoding='utf-8')
    index = []
    number = 0
    for case_id, sequence in ORDER:
        for condition in sequence:
            number += 1
            case = cases[case_id]
            context = requests[case_id]['context']
            lines = [f'# Trial {number:02d} · {case_id} · {condition}',
                     'Start your timer when you open this case. See START.md for the common instructions.',
                     '## Original case']
            for field in ('task', 'blockers', 'sources', 'decisions', 'workflow_state'):
                lines.extend([field, '~~~json', json.dumps(case[field], ensure_ascii=False, indent=2), '~~~'])
            lines.extend(['Recorded flags', '~~~json', json.dumps(context['flags'], indent=2), '~~~'])
            if condition != 'Manual':
                result = mocks[case_id] if condition == 'Mock' else live.get(case_id, {})
                mode = result.get('metadata', {}).get('invocation_mode')
                expected = 'deterministic_mock' if condition == 'Mock' else 'live_response'
                if result.get('status') == 'validated' and mode == expected:
                    display = render_analysis(result['analysis'], build_analysis_request(requests[case_id]))
                    lines.extend([f'## CANDIDATE · {mode}', 'Frozen bounded mock' if condition == 'Mock'
                                  else f"Live repetition 1 · {result['metadata']['model']}",
                                  '~~~json', json.dumps(result['package'], ensure_ascii=False, indent=2),
                                  '~~~', '~~~json', json.dumps(display, ensure_ascii=False, indent=2), '~~~'])
                else:
                    detail = 'No validated live output is available for repetition one.'
                    if result.get('status') == 'provider_failure':
                        status = result.get('metadata', {}).get('http_status')
                        detail = f'The first request returned HTTP {status}.' if status else 'The first provider request failed.'
                    elif not result and rows[-1].get('status') == 'stopped_after_failed_or_ambiguous_attempt':
                        detail = 'The run stopped before this case was sent.'
                    lines[2:2] = ['**Candidate unavailable · manual fallback.** ' + detail,
                                   'Time your review of the original records. Rate the fallback display. Leave live-candidate judgments blank.']
            lines.extend(['## Personal response', 'Reviewer / date / interruptions:',
                          'Recorded state and material observations with source IDs:',
                          'Missing information or conflict:', 'Approved owner and next action:',
                          'Question for the supervisor:', 'Omission, unsupported claim or implied approval:',
                          'Candidate outcome, correction, rationale and sources (if applicable):',
                          'Actual elapsed seconds:', 'Navigation steps:', 'Usefulness (1–5) and reason:'])
            filename = f'{number:02d}-{case_id}-{condition}.md'
            index.append(f'{number}. [{case_id} — {condition}]({filename})')
            (target / filename).write_text('\n\n'.join(lines) + '\n', encoding='utf-8')
    (target / 'START.md').write_text(guide + '\n## Open one worksheet at a time\n\n' +
                                     '\n'.join(index) + '\n', encoding='utf-8')
    return target


if __name__ == '__main__':
    print(worksheets())
