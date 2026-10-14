"""Private local account verification; no garage, lobby or race acceptance claim."""
import argparse
import getpass
import json
import sys
import warnings

from client.nps_crypto import installed_public_key
from client.nps_identity import installed_executable_checksum
from client.online_account import authenticate
from client.server_discovery import (AuthSettings, fetch_shard_list,
    installed_patch_settings, installed_sources, windows_auth_settings)


class AccountCheckSetupError(ValueError):
    """Public setup errors with fixed, non-sensitive messages."""


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        # An accidentally supplied --password must not appear in diagnostics.
        self.exit(2, 'Invalid account-check arguments; use --help. '
                     'Credentials are accepted only through hidden prompts.\n')


def main(argv=None):
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument('data', help='external original installation')
    parser.add_argument('--shard-id', type=int, required=True)
    parser.add_argument('--source', help='installed discovery path when sources differ')
    parser.add_argument('--auth-host', help='explicit configured host for Linux')
    parser.add_argument('--auth-service', help='explicit configured base service for Linux')
    parser.add_argument('--login', action='store_true',
                        help='prompt privately, then perform one account/persona check')
    args = parser.parse_args(argv)
    report = {'scope': 'account authorization, binary login and persona retrieval only',
              'live_account_tested': False, 'server_version': 'not reported'}
    username = password = None
    try:
        sources = installed_sources(args.data)
        if args.source:
            selected = [s for s in sources if s.path == args.source]
            if len(selected) != 1:
                raise AccountCheckSetupError('unknown installed discovery source')
            source = selected[0]
        elif len({s.url for s in sources}) == 1:
            source = sources[0]
        else:
            raise AccountCheckSetupError('select an installed discovery source')
        shards = [s for s in fetch_shard_list(source.url) if s.identifier == args.shard_id]
        if len(shards) != 1:
            raise AccountCheckSetupError('requested shard is not uniquely advertised')
        shard = shards[0]
        settings = installed_patch_settings(args.data)
        if not settings or not settings.certificate_sha1:
            raise AccountCheckSetupError('installed certificate pin is required')
        if bool(args.auth_host) != bool(args.auth_service):
            raise AccountCheckSetupError('supply both explicit authentication settings')
        auth = (AuthSettings(args.auth_host, args.auth_service) if args.auth_host
                else windows_auth_settings())
        if auth is None:
            raise AccountCheckSetupError('configured authentication settings are required')
        installed_public_key(args.data)
        installed_executable_checksum(args.data)
        report['shard_name'] = shard.name
        report['shard_id'] = shard.identifier
        report['preflight_passed'] = True
        if args.login:
            if not sys.stdin.isatty():
                raise AccountCheckSetupError('private login requires an interactive local terminal')
            # Refuse getpass fallback before it can echo credentials.
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                username = getpass.getpass('Account name (hidden): ')
                password = getpass.getpass('Password (hidden): ')
            account = authenticate(args.data, shard, auth, settings.certificate_sha1,
                                   username, password)
            report['live_account_tested'] = True
            report['persona_count'] = len(account.personas.entries)
        print(json.dumps(report, indent=2))
        return 0
    except KeyboardInterrupt:
        print('Account check cancelled.', file=sys.stderr)
        return 2
    except AccountCheckSetupError as error:
        print(f'Account check setup: {error}.', file=sys.stderr)
        return 1
    except Exception as error:
        # Network exceptions may contain ticket URLs or account payloads.
        # Expose only the error type, never exception text or a traceback.
        print(f'Account check failed ({type(error).__name__}).', file=sys.stderr)
        return 1
    finally:
        username = password = None


if __name__ == '__main__':
    raise SystemExit(main())
