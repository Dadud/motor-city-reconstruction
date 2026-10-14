"""Private local fan-server verification through lobby, primary and garage data."""
import argparse
import getpass
import json
import sys
import warnings

from client.fanserver_test import FanServerSetupError, prepare_context, run_test


class PrivateArgumentParser(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, 'Invalid fan-server-check arguments; use --help. '
                     'Credentials are accepted only through hidden prompts.\n')


def _pick_persona(personas):
    if not sys.stdin.isatty():
        raise FanServerSetupError('persona selection requires an interactive local terminal')
    print('Select a persona:')
    for index, persona in enumerate(personas, start=1):
        print(f"  {index}. {persona['name']} (ID {persona['persona_id']})")
    while True:
        choice = input('Persona number: ').strip()
        if not choice.isdigit():
            print('Enter the listed number.')
            continue
        selected = int(choice)
        if 1 <= selected <= len(personas):
            return personas[selected - 1]['persona_id']
        print('Enter the listed number.')


def main(argv=None):
    parser = PrivateArgumentParser(description=__doc__)
    parser.add_argument('data', help='external original installation')
    parser.add_argument('--shard-id', type=int, required=True)
    parser.add_argument('--source', help='installed discovery path when sources differ')
    parser.add_argument('--auth-host', help='explicit configured host for Linux')
    parser.add_argument('--auth-service', help='explicit configured base service for Linux')
    parser.add_argument('--hostname', help='lobby hostname override')
    parser.add_argument('--ip-address', help='lobby IP override')
    parser.add_argument('--persona-id', type=int, help='persona to test without prompting')
    parser.add_argument('--login', action='store_true',
                        help='prompt privately, then perform one fan-server flow check')
    parser.add_argument('--fetch-garage', action='store_true',
                        help='fetch persona startup garage data after primary login')
    parser.add_argument('--probe-race-entry', action='store_true',
                        help='validate recovered race-entry task construction after login')
    parser.add_argument('--catalogue', action='store_true',
                        help='enrich owned parts when Online.mdb is installed')
    args = parser.parse_args(argv)
    report = {
        'scope': 'configured shard preflight and optional live fan-server flow',
        'live_fan_server_tested': False,
        'server_version': 'not reported',
    }
    username = password = None
    try:
        context = prepare_context(
            args.data,
            shard_id=args.shard_id,
            source=args.source,
            auth_host=args.auth_host,
            auth_service=args.auth_service,
            hostname=args.hostname,
            ip_address=args.ip_address,
            fetch_garage=args.fetch_garage,
            use_catalogue=args.catalogue,
            probe_race_entry=args.probe_race_entry,
        )
        report.update({
            'shard_name': context.shard.name,
            'shard_id': context.shard.identifier,
            'preflight_passed': True,
            'fetch_garage_requested': args.fetch_garage,
            'catalogue_requested': args.catalogue,
            'probe_race_entry_requested': args.probe_race_entry,
        })
        if args.login:
            if not sys.stdin.isatty():
                raise FanServerSetupError('private login requires an interactive local terminal')
            with warnings.catch_warnings():
                warnings.simplefilter('error', getpass.GetPassWarning)
                username = getpass.getpass('Account name (hidden): ')
                password = getpass.getpass('Password (hidden): ')
            needs_persona = args.persona_id is None
            result = run_test(
                args.data,
                username,
                password,
                shard_id=args.shard_id,
                source=args.source,
                auth_host=args.auth_host,
                auth_service=args.auth_service,
                persona_id=args.persona_id,
                hostname=args.hostname,
                ip_address=args.ip_address,
                fetch_garage=args.fetch_garage,
                use_catalogue=args.catalogue,
                probe_race_entry=args.probe_race_entry,
                on_personas=_pick_persona if needs_persona else None,
            )
            report['live_fan_server_tested'] = True
            report.update({key: result.get(key) for key in (
                'success', 'cancelled', 'account_authenticated', 'lobby_connected',
                'primary_connected', 'garage_loaded', 'persona_count', 'garage_record_count',
                'part_seed_count', 'part_slot_count', 'selected_persona_id', 'last_stage',
                'race_entry_probe_passed', 'fast_join_tcp_preferred', 'positional_updates_hz',
                'update_interval_seconds', 'recovered_task_kinds',
                'room_channel_probe_passed',
                'expects_room_channel_add',
            )})
        print(json.dumps(report, indent=2))
        return 0
    except KeyboardInterrupt:
        print('Fan-server check cancelled.', file=sys.stderr)
        return 2
    except FanServerSetupError as error:
        print(f'Fan-server check setup: {error}.', file=sys.stderr)
        return 1
    except Exception as error:
        print(f'Fan-server check failed ({type(error).__name__}).', file=sys.stderr)
        return 1
    finally:
        username = password = None


if __name__ == '__main__':
    raise SystemExit(main())

