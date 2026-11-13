#!/usr/bin/env python3
"""Read-only live feedback checks; retain provider bodies/cursors only in memory."""
import argparse
import json
import os
import re
from pathlib import Path
import subprocess
import uuid


def docker(*args):
    return subprocess.run(['docker', *args], capture_output=True, text=True, timeout=90)


def collect(client, limit, repo='exoscale/kms', number=566):
    cursor = None
    seen = set()
    head = None
    reviews, discussion, threads = {}, {}, {}
    pages = 0
    fragment_roots = set()
    cross_page_fragments = 0
    while True:
        args = ['exec', client, 'agentctl', 'github', 'pr', 'feedback', '--repo', repo, '--number', str(number), '--limit', str(limit)]
        if cursor:
            args += ['--cursor', cursor]
        response = docker(*args)
        try:
            envelope = json.loads(response.stdout)
        except ValueError:
            raise RuntimeError('Non-JSON CLI response (body suppressed)') from None
        if response.returncode:
            raise RuntimeError('CLI failed: ' + str(envelope.get('error', {}).get('code')))
        data = envelope['data']
        assert data['repo'] == repo and data['number'] == number
        head = head or data['head_sha']
        assert head and data['head_sha'] == head, 'Observed head changed'
        pages += 1
        assert pages <= 20, 'Unexpected traversal length'
        for review in data['reviews']:
            assert review['id'] and review['url'] and 'body' in review
            reviews[review['id']] = review
        for comment in data['discussion_comments']:
            assert comment['id'] and comment['url'] and 'body' in comment
            discussion[comment['id']] = comment
        for fragment in data['threads']:
            root = fragment['root_comment_id']
            assert fragment['resolved'] is None and fragment['outdated'] is None
            if root in fragment_roots:
                cross_page_fragments += 1
            fragment_roots.add(root)
            group = threads.setdefault(root, {})
            for comment in fragment['comments']:
                assert comment['id'] and comment['url'] and 'body' in comment and 'path' in comment
                group[comment['id']] = comment
        cursor = data['next_cursor']
        if cursor is None:
            assert data['status'] == 'complete', 'Terminal result is not complete'
            assert all(value == 'complete' for value in data['collections'].values())
            break
        assert data['status'] != 'complete' and cursor not in seen
        seen.add(cursor)
    records = {('review', key): value for key, value in reviews.items()}
    records.update({('discussion', key): value for key, value in discussion.items()})
    for root, comments in threads.items():
        records.update({('inline', key): dict(value, root_comment_id=root) for key, value in comments.items()})
    summary = dict(limit=limit, pages=pages, head_sha=head, complete=True,
                   reviews=len(reviews), discussion_comments=len(discussion),
                   threads=len(threads), inline_comments=sum(map(len, threads.values())),
                   replies=sum(c['in_reply_to_id'] is not None for g in threads.values() for c in g.values()),
                   cross_page_fragments=cross_page_fragments,
                   resolved_outdated='unknown (null)')
    return records, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--image', default='go-agent-all')
    parser.add_argument('--gateway', default='go-agent-gateway')
    parser.add_argument('--network', default='go-agent-internal-net')
    parser.add_argument('--repo', default='exoscale/kms')
    parser.add_argument('--number', type=int, default=566)
    parser.add_argument('--context', help='explicit local Docker context; otherwise use Docker defaults')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.number <= 0 or not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+', args.repo):
        parser.error('provide a repository owner/name and positive PR number')
    if args.repo == 'forbidden/project':
        parser.error('repository conflicts with the policy-denial fixture')
    if args.context:
        os.environ['DOCKER_CONTEXT'] = args.context
    client = 'fenced-feedback-' + uuid.uuid4().hex[:10]
    try:
        result = docker('run', '-d', '--name', client, '--network', args.network,
                        '--read-only', '--user', f'{os.getuid()}:{os.getgid()}', '--cap-drop=ALL',
                        '--security-opt=no-new-privileges', '-e', 'HTTP_PROXY=http://127.0.0.1:1',
                        '-e', 'HTTPS_PROXY=http://127.0.0.1:1', args.image, 'sleep', 'infinity')
        assert result.returncode == 0, 'Client failed to start'
        first, initial = collect(client, 50, args.repo, args.number)
        # A failed refresh raises before replacing any complete comparison baseline.
        second, refreshed = collect(client, 50, args.repo, args.number)
        comparison = {'same_head': initial['head_sha'] == refreshed['head_sha'],
                      'new_records': len(second.keys() - first.keys()),
                      'missing_observations': len(first.keys() - second.keys()),
                      'changed_records': sum(first[k] != second[k] for k in first.keys() & second.keys())}
        # Smaller pages exercise thread fragment merging when the live data permits it.
        small_limit = max(1, min(49, (len(second) + 4) // 5))
        _, small = collect(client, small_limit, args.repo, args.number)
        denied = docker('exec', client, 'agentctl', 'github', 'pr', 'feedback', '--repo', 'forbidden/project', '--number', str(args.number))
        assert denied.returncode == 4 and json.loads(denied.stdout)['error']['code'] == 'policy_denied'
        sha = docker('exec', client, 'sha256sum', '/usr/local/bin/agentctl').stdout.split()[0]
        image = json.loads(docker('image', 'inspect', args.image).stdout)[0]
        image_id = image['Id']
        gateway = json.loads(docker('inspect', args.gateway).stdout)[0]
        report = dict(repo=args.repo, number=args.number, network=args.network,
                      architecture=image['Architecture'], agent_image=image_id, gateway_image=gateway['Image'], cli_sha256=sha,
                      initial=initial, refresh=refreshed, comparison=comparison, smaller_pages=small,
                      policy_denied=True, unusable_ambient_proxy_bypassed=True,
                      limitations=['Live feedback can change during pagination; no atomic snapshot.',
                                   'No feedback was posted/edited to manufacture refresh changes.',
                                   'resolved/outdated are unknown; completeness does not supply those fields.',
                                   'Live data may not exercise inline replies; separate fixture evidence covers reply merging.',
                                   'This read-only check does not verify credential rotation or other service lifecycles.'])
        args.output.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report, indent=2))
    finally:
        docker('rm', '-f', client)


if __name__ == '__main__':
    main()
