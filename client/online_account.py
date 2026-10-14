"""Join recovered authorization, account login, persona and lobby services.

This is an explicit blocking developer API. Additional MCOTS services and the
game's online UI remain incomplete. No credentials are stored in account objects.
"""
from dataclasses import dataclass, field
from client.auth_service import authorize
from client.lobby_connection import connect_lobby
from client.lobby_login import LobbyLogin
from client.mcots_login import MCOTSLoginRecord
from client.mcots_primary_service import connect_primary
from client.nps_transport import _timeout
from client.nps_crypto import installed_public_key
from client.nps_identity import SERVICE_ID, installed_executable_checksum
from client.nps_login_service import AuthenticatedAccount, login
from client.nps_persona import PersonaMaps
from client.nps_persona_service import fetch_personas, activate_persona
from client.nps_response import SessionKeyRecord
from client.nps_session_request import LOGIN_KEY_RECORD_VALUE, prepare_login
from client.server_discovery import Shard


class AuthorizationDenied(RuntimeError):
    def __init__(self, reason_code):
        self.reason_code = reason_code
        super().__init__('account authorization denied')


@dataclass
class OnlineConnections:
    """Own the accepted lobby and primary streams, closing both together."""
    lobby: object = field(repr=False)
    primary: object = field(repr=False)

    def close(self):
        try:
            self.primary.close()
        finally:
            self.lobby.close()

    def __enter__(self):
        return self

    def __exit__(self, *unused):
        self.close()


@dataclass(frozen=True)
class OnlineAccount:
    shard: Shard
    account: AuthenticatedAccount = field(repr=False)
    personas: PersonaMaps = field(repr=False)

    def enter_lobby(self, persona_id, *, hostname, ip_address,
                    on_queue_position=None, queue_timeout=120):
        """Activate an explicitly selected persona, then open its lobby.

        Match both persona and configured shard. Account identity comes from
        login success, never from a possibly different map-record field.
        The returned lobby stream must be closed by its owner.
        """
        persona = self.personas.find(persona_id, self.shard.identifier)
        if persona is None:
            raise ValueError('persona does not belong to the selected shard list')
        # Validate local lobby fields before performing online activation.
        payload = LobbyLogin.for_selected_persona(persona.persona_id, persona.name,
            self.account.prepared_login, account_user_id=self.account.user_id,
            hostname=hostname, ip_address=ip_address)
        if on_queue_position is not None and not callable(on_queue_position):
            raise TypeError('queue callback must be callable')
        _timeout(queue_timeout)
        activate_persona(self.shard.login, self.account.user_id,
                         persona.persona_id, self.shard.identifier)
        return connect_lobby(self.shard.lobby, payload, self.account.prepared_login,
            on_queue_position=on_queue_position, queue_timeout=queue_timeout)

    def enter_connections(self, persona_id, *, hostname, ip_address,
                          on_queue_position=None, queue_timeout=120,
                          connect_timeout=30, attachment_timeout=20, login_timeout=120):
        """Activate a persona, join the lobby, then attach and log in to MCOTS.

        The original 0x5ef240 caller passes zero for all three extra login
        values. Retain the client-generated key and authenticated account ID.
        This stops at the primary rich reply; advertised follow-up services
        and subsequent game-data requests still require reconstruction.
        """
        persona = self.personas.find(persona_id, self.shard.identifier)
        if persona is None:
            raise ValueError('persona does not belong to the selected shard list')
        record = MCOTSLoginRecord(self.account.user_id, persona.persona_id,
                                  persona.name, 0, 0, 0)
        record.encode_native_record()
        material = self.account.prepared_login.session_material
        if not isinstance(material, bytes) or len(material) != 32:
            raise ValueError('expected 32 retained client session bytes')
        for timeout in (connect_timeout, attachment_timeout, login_timeout):
            _timeout(timeout)
        lobby = self.enter_lobby(persona_id, hostname=hostname, ip_address=ip_address,
            on_queue_position=on_queue_position, queue_timeout=queue_timeout)
        try:
            primary = connect_primary(self.shard.transactions, record, material,
                connect_timeout=connect_timeout, attachment_timeout=attachment_timeout,
                login_timeout=login_timeout)
        except Exception:
            lobby.close()
            raise
        return OnlineConnections(lobby, primary)


def authenticate(root, shard, auth_settings, certificate_sha1, username, password,
                 *, key_record_value=LOGIN_KEY_RECORD_VALUE):
    """Authorize once, perform binary login, then download personas.

    The key-record value defaults to the recovered startup zero. Failures stop the
    sequence; no stage is retried and no persona is selected automatically.
    """
    if not isinstance(shard, Shard):
        raise TypeError('expected a discovered shard')
    SessionKeyRecord(b'', key_record_value).encode()
    # Check external identity prerequisites before transmitting credentials.
    installed_public_key(root)
    installed_executable_checksum(root)
    decision = authorize(auth_settings, certificate_sha1, username, password, SERVICE_ID)
    if not decision.valid:
        raise AuthorizationDenied(decision.reason_code)
    prepared = prepare_login(root, decision.ticket.encode('ascii'), key_record_value=key_record_value)
    account = login(shard.login, prepared)
    personas = fetch_personas(shard.login, account.user_id)
    return OnlineAccount(shard, account, personas)
