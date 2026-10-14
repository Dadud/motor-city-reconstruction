"""Inspect installed discovery settings; optionally fetch public shard lists.

This is not a login, lobby, transaction or race compatibility test.
"""
import argparse
from dataclasses import asdict
import json

from client.server_discovery import (fetch_shard_list, installed_sources,
                                     installed_patch_settings, windows_auth_settings)
from client.legacy_https import PinnedHTTPSConnection


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('data', help='local game installation')
    parser.add_argument('--fetch', action='store_true', help='fetch public shard lists')
    parser.add_argument('--check-auth-tls', action='store_true',
                        help='check pinned HTTPS certificate only, without login data')
    parser.add_argument('--auth-host', help='explicit HTTPS auth host; otherwise Windows registry')
    args = parser.parse_args()
    report = {'compatibility': 'discovery only; no authenticated acceptance tested',
              'sources': []}
    failed = False
    try:
        sources = installed_sources(args.data)
        settings = installed_patch_settings(args.data)
        report['patch_network_settings'] = asdict(settings) if settings else None
        auth = windows_auth_settings()
        report['windows_auth_settings'] = asdict(auth) if auth else None
    except ValueError as error:
        parser.error(str(error))
    for source in sources:
        result = asdict(source)
        if args.fetch:
            try:
                result['shards'] = [asdict(shard) for shard in fetch_shard_list(source.url)]
            except (OSError, ValueError) as error:
                result['error'] = str(error)
                failed = True
        report['sources'].append(result)
    if args.check_auth_tls:
        host = args.auth_host or (auth.host if auth else None)
        if not host or not settings or not settings.certificate_sha1:
            parser.error('TLS check requires an auth host and explicit installed certificate pin')
        connection = PinnedHTTPSConnection(host, settings.certificate_sha1)
        try:
            connection.connect()
            report['auth_tls'] = {'host': host, 'port': 443,
                                  'certificate_pin_matched': True,
                                  'tls_version': connection.sock.version(),
                                  'application_data_sent': False}
        except OSError as error:
            report['auth_tls'] = {'host': host, 'error': str(error)}
            failed = True
        finally:
            connection.close()
    print(json.dumps(report, indent=2))
    return 1 if failed else 0


if __name__ == '__main__':
    raise SystemExit(main())
