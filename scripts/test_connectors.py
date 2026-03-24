#!/usr/bin/env python3
"""
Test script for all MCP connectors.

Runs basic tests against each connector to verify they're working.
"""

import subprocess
import json
import os
import sys
from datetime import date, timedelta
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent
os.chdir(PROJECT_ROOT)

# Load environment
from dotenv import load_dotenv
load_dotenv()


def test_mcp_server(server_name: str, tools_to_test: list, env_vars: dict = None) -> dict:
    """Test an MCP server by calling its tools."""

    print(f"\n{'='*60}")
    print(f"Testing: {server_name}")
    print(f"{'='*60}")

    # Build environment for subprocess
    env = os.environ.copy()
    if env_vars:
        env.update(env_vars)

    # Start the MCP server
    proc = subprocess.Popen(
        ['uv', 'run', server_name],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        env=env
    )

    results = {
        'server': server_name,
        'tools': {}
    }

    try:
        # Initialize
        init_request = json.dumps({
            'jsonrpc': '2.0',
            'id': 1,
            'method': 'initialize',
            'params': {
                'protocolVersion': '2024-11-05',
                'capabilities': {},
                'clientInfo': {'name': 'test', 'version': '1.0'}
            }
        }) + '\n'

        proc.stdin.write(init_request)
        proc.stdin.flush()
        init_response = proc.stdout.readline()

        init_data = json.loads(init_response)
        if 'error' in init_data:
            print(f"❌ Initialization failed: {init_data['error']['message']}")
            results['status'] = 'failed'
            results['error'] = init_data['error']['message']
            proc.terminate()
            return results

        print(f"✅ Initialized successfully")

        # List tools
        tools_request = json.dumps({
            'jsonrpc': '2.0',
            'id': 2,
            'method': 'tools/list',
            'params': {}
        }) + '\n'

        proc.stdin.write(tools_request)
        proc.stdin.flush()
        tools_response = proc.stdout.readline()

        tools_data = json.loads(tools_response)
        available_tools = [t['name'] for t in tools_data.get('result', {}).get('tools', [])]
        print(f"📦 Available tools: {', '.join(available_tools)}")

        # Test each requested tool
        for tool_name, tool_args in tools_to_test:
            if tool_name not in available_tools:
                print(f"⚠️  Tool '{tool_name}' not available, skipping")
                results['tools'][tool_name] = 'skipped (not available)'
                continue

            call_request = json.dumps({
                'jsonrpc': '2.0',
                'id': 3,
                'method': 'tools/call',
                'params': {
                    'name': tool_name,
                    'arguments': tool_args
                }
            }) + '\n'

            proc.stdin.write(call_request)
            proc.stdin.flush()
            call_response = proc.stdout.readline()

            call_data = json.loads(call_response)

            if 'error' in call_data:
                print(f"❌ Tool '{tool_name}' failed: {call_data['error']['message']}")
                results['tools'][tool_name] = f"failed: {call_data['error']['message']}"
            else:
                result_text = call_data['result']['content'][0]['text']
                # Try to parse as JSON for nicer output
                try:
                    result_json = json.loads(result_text)
                    if isinstance(result_json, list):
                        print(f"✅ Tool '{tool_name}': {len(result_json)} items returned")
                    elif isinstance(result_json, dict):
                        if 'status' in result_json:
                            print(f"✅ Tool '{tool_name}': {result_json.get('status', 'ok')}")
                        else:
                            print(f"✅ Tool '{tool_name}': OK")
                    else:
                        print(f"✅ Tool '{tool_name}': OK")
                except:
                    print(f"✅ Tool '{tool_name}': OK")

                results['tools'][tool_name] = 'success'

        results['status'] = 'success'

    except Exception as e:
        print(f"❌ Error testing {server_name}: {e}")
        results['status'] = 'failed'
        results['error'] = str(e)

    finally:
        proc.terminate()

    return results


def main():
    """Run all connector tests."""

    print("╔═══════════════════════════════════════════════════════════╗")
    print("║       Multi-Platform Connector Test Suite                 ║")
    print("╚═══════════════════════════════════════════════════════════╝")

    # Define tests for each server
    end_date = date.today()
    start_date = end_date - timedelta(days=30)

    tests = []

    # Umami (if configured)
    if os.environ.get('UMAMI_API_KEY') or (os.environ.get('UMAMI_USERNAME') and os.environ.get('UMAMI_PASSWORD')):
        tests.append({
            'server': 'umami-mcp',
            'tools': [
                ('get_websites', {}),
                ('get_stats', {
                    'website_id': '1',  # Will fail if no website, but tests connection
                    'start_at': str(start_date),
                    'end_at': str(end_date)
                })
            ]
        })
    else:
        print("\n⚠️  Skipping Umami: credentials not configured")

    # GSC (if OAuth token exists)
    if (PROJECT_ROOT / '.gsc_token.json').exists():
        tests.append({
            'server': 'gsc-mcp',
            'env': {
                'GSC_SITE_URL': os.environ.get('GSC_SITE_URL', 'sc-domain:example.com')
            },
            'tools': [
                ('test_gsc_connection', {}),
                ('get_gsc_metrics', {
                    'start_date': str(start_date),
                    'end_date': str(end_date)
                }),
                ('get_gsc_queries', {
                    'start_date': str(start_date),
                    'end_date': str(end_date),
                    'limit': 5
                })
            ]
        })
    else:
        print("\n⚠️  Skipping GSC: .gsc_token.json not found")

    # YouTube (if configured)
    if os.environ.get('YOUTUBE_API_KEY') and os.environ.get('YOUTUBE_CHANNEL_ID'):
        tests.append({
            'server': 'youtube-mcp',
            'tools': [
                ('test_youtube_connection', {}),
                ('get_youtube_metrics', {
                    'start_date': str(start_date),
                    'end_date': str(end_date)
                })
            ]
        })
    else:
        print("\n⚠️  Skipping YouTube: credentials not configured")

    # Mastodon (if configured)
    if os.environ.get('MASTODON_ACCESS_TOKEN') and os.environ.get('MASTODON_ACCOUNT_ID'):
        tests.append({
            'server': 'mastodon-mcp',
            'tools': [
                ('test_mastodon_connection', {}),
                ('get_mastodon_followers', {})
            ]
        })
    else:
        print("\n⚠️  Skipping Mastodon: credentials not configured")

    # Bluesky (if configured)
    if os.environ.get('BLUESKY_IDENTIFIER') and os.environ.get('BLUESKY_PASSWORD'):
        tests.append({
            'server': 'bluesky-mcp',
            'tools': [
                ('test_bluesky_connection', {}),
                ('get_bluesky_followers', {})
            ]
        })
    else:
        print("\n⚠️  Skipping Bluesky: credentials not configured")

    # LinkedIn (if configured)
    if os.environ.get('LINKEDIN_ACCESS_TOKEN') and os.environ.get('LINKEDIN_ORGANIZATION_ID'):
        tests.append({
            'server': 'linkedin-mcp',
            'tools': [
                ('test_linkedin_connection', {}),
                ('get_linkedin_followers', {})
            ]
        })
    else:
        print("\n⚠️  Skipping LinkedIn: credentials not configured")

    # Instagram (if configured)
    if os.environ.get('INSTAGRAM_ACCESS_TOKEN') and os.environ.get('INSTAGRAM_BUSINESS_ACCOUNT_ID'):
        tests.append({
            'server': 'instagram-mcp',
            'tools': [
                ('test_instagram_connection', {}),
                ('get_instagram_followers', {})
            ]
        })
    else:
        print("\n⚠️  Skipping Instagram: credentials not configured")

    if not tests:
        print("\n❌ No platforms configured. Please set up at least one platform in .env")
        sys.exit(1)

    # Run tests
    results = []
    for test in tests:
        result = test_mcp_server(
            test['server'],
            test['tools'],
            test.get('env', {})
        )
        results.append(result)

    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")

    passed = 0
    failed = 0

    for result in results:
        status = '✅' if result['status'] == 'success' else '❌'
        print(f"{status} {result['server']}: {result['status']}")

        if result['status'] == 'success':
            passed += 1
        else:
            failed += 1

        for tool, tool_result in result['tools'].items():
            if tool_result == 'success':
                print(f"   ✅ {tool}")
            elif tool_result == 'skipped (not available)':
                print(f"   ⚠️  {tool}: not available")
            else:
                print(f"   ❌ {tool}: {tool_result}")

    print(f"\n{'='*60}")
    print(f"Results: {passed} passed, {failed} failed")
    print(f"{'='*60}")

    sys.exit(0 if failed == 0 else 1)


if __name__ == '__main__':
    main()
