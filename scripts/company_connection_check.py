"""Company connection probe and explicit guarded initialization. No credential storage."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from getpass import getpass
import json
from pathlib import Path

EXPECTED = ('QDCTNKN', 'UW19058', 'CB12755', 'AWS_CA_CENTRAL_1')


def verify_identity(row):
    if tuple(row[:4]) != EXPECTED:
        raise RuntimeError('Server identity differs from the verified company account; stop.')


def main():
    import snowflake.connector

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--connection', help='Explicit company connections.toml profile; no default profile')
    parser.add_argument('--password', action='store_true', help='Native password login; does not assume MFA enrollment')
    parser.add_argument('--password-mfa', action='store_true', help='Compatibility: use username_password_mfa authenticator; enrollment is not inferred')
    parser.add_argument('--passcode', action='store_true', help='Also prompt for an MFA passcode instead of push')
    parser.add_argument('--evidence', type=Path, default=Path('.local/company-20261019/connection_evidence.json'))
    parser.add_argument('--verify-schema', action='store_true', help='Read-only comparison after initialization')
    parser.add_argument('--initialize', action='store_true', help='Explicitly create fresh company EFNS_DEV and verify it; no business import')
    parser.add_argument('--inspect-user-profile', action='store_true', help='Read only the confirmed EFNSDATABASE user profile fields; never provisions an admin')
    parser.add_argument('--verify-app-upload', action='store_true', help='Read-only check of all staged application files and existing application status')
    parser.add_argument('--deploy-app', action='store_true', help='Verify upload first, then create/publish a fresh app and apply existing post-deploy grants; never initialize the database')
    parser.add_argument('--complete-app-grants', action='store_true', help='Inspect an existing correct live app and complete post-deploy grants only; no creation/publishing')
    args = parser.parse_args()
    if args.initialize and (args.verify_app_upload or args.deploy_app or args.complete_app_grants):
        parser.error('Application operations cannot be combined with --initialize')
    if args.deploy_app and args.complete_app_grants:
        parser.error('Choose fresh app deployment OR existing-app grant recovery, not both')
    if sum((bool(args.connection), args.password, args.password_mfa)) != 1:
        parser.error('Choose exactly one of --connection efns-company, --password, or --password-mfa')
    if args.connection and args.connection != 'efns-company':
        parser.error('Only the isolated efns-company profile is accepted')
    options = {'account': 'qdctnkn-uw19058', 'user': 'EFNSDATABASE',
               'role': 'ACCOUNTADMIN', 'login_timeout': 60, 'network_timeout': 60,
               'client_session_keep_alive': False}
    if args.connection:
        options['connection_name'] = args.connection
    else:
        options.update(authenticator='username_password_mfa' if args.password_mfa else 'snowflake',
                       password=getpass('Company Snowflake password (hidden, not saved): '))
        if args.passcode:
            options['passcode'] = getpass('MFA passcode (hidden, not saved): ')
    if args.initialize and args.evidence == Path('.local/company-20261019/connection_evidence.json'):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        args.evidence = args.evidence.with_name(f'initialization_{stamp}.json')
    if (args.verify_app_upload or args.deploy_app or args.complete_app_grants) and args.evidence == Path('.local/company-20261019/connection_evidence.json'):
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
        args.evidence = args.evidence.with_name(f'application_{stamp}.json')
    evidence = {'queried_at_utc': datetime.now(timezone.utc).isoformat(), 'queries': [],
                'authentication': {'requested_authenticator': options.get('authenticator', 'explicit profile'),
                                   'passcode_supplied': bool(args.passcode), 'mfa_enrollment_verified': False}}
    try:
        with snowflake.connector.connect(**options) as connection:
            with connection.cursor() as cursor:
                sql = 'SELECT CURRENT_ORGANIZATION_NAME(), CURRENT_ACCOUNT_NAME(), CURRENT_ACCOUNT(), CURRENT_REGION(), CURRENT_ROLE(), CURRENT_USER()'
                cursor.execute(sql)
                row = cursor.fetchone()
                verify_identity(row)
                evidence['identity'] = list(row)
                evidence['connected'] = True
                evidence['queries'].append({'sql': sql, 'query_id': cursor.sfqid})
                for sql in ('SHOW DATABASES', 'SHOW WAREHOUSES', 'SHOW GRANTS TO USER EFNSDATABASE'):
                    cursor.execute(sql)
                    columns = [column[0] for column in cursor.description]
                    evidence['queries'].append({'sql': sql, 'query_id': cursor.sfqid,
                                                'rows': [dict(zip(columns, row)) for row in cursor.fetchall()]})
                if args.inspect_user_profile:
                    cursor.execute('DESCRIBE USER EFNSDATABASE')
                    description_id = cursor.sfqid
                    columns = [column[0] for column in cursor.description]
                    properties = [dict(zip(columns, row)) for row in cursor.fetchall()]
                    selected = [{key: row.get(key) for key in ('property','value')}
                                for row in properties if str(row.get('property','')).upper() in
                                {'NAME','LOGIN_NAME','EMAIL','DISPLAY_NAME','DISABLED'}]
                    # Do not retain password, MFA, key or other authentication
                    # properties returned by DESCRIBE USER.
                    evidence['user_profile'] = {'username': 'EFNSDATABASE', 'query_id': description_id,
                                                'properties': selected, 'viewer_email_verified_in_app': False,
                                                'admin_created': False}
                    values = {str(row['property']).upper(): row['value'] for row in selected}
                    evidence['user_profile']['email_matches_confirmed_admin'] = str(values.get('EMAIL') or '').strip().casefold() == 'database@nsegg.ca'
                    print('Read-only EFNSDATABASE profile checked; application viewer email and admin provisioning remain separate.')
                if args.initialize or args.verify_schema:
                    try:
                        from scripts.company_database_deployment import initialize, verify
                    except ModuleNotFoundError:
                        from company_database_deployment import initialize, verify
                    if args.initialize:
                        initialize(cursor, evidence, Path(__file__).resolve().parents[1] / '.local/company-20261019')
                    verify(cursor, evidence, expect_empty=args.initialize)
                if args.verify_app_upload or args.deploy_app or args.complete_app_grants:
                    try:
                        from scripts.company_application_deployment import run
                    except ModuleNotFoundError:
                        from company_application_deployment import run
                    run(cursor,evidence,deploy=args.deploy_app,complete_existing_grants=args.complete_app_grants)
        args.evidence.parent.mkdir(parents=True, exist_ok=True)
        args.evidence.write_text(json.dumps(evidence, default=str, indent=2), encoding='utf-8')
        label = ('Company application operation completed; inspect actual status in ' if (args.verify_app_upload or args.deploy_app or args.complete_app_grants)
                 else 'Company initialization and verification succeeded; evidence saved to ' if args.initialize
                 else 'Company identity verified; read-only metadata saved to ')
        print(label + str(args.evidence))
    except snowflake.connector.Error as error:
        # Connector messages may contain authentication responses. Log only codes.
        print(f'Company authentication/query failed: {type(error).__name__}; errno={error.errno}; sqlstate={error.sqlstate}')
        evidence['failure'] = {'error_type': type(error).__name__, 'error_code': error.errno,
                               'query_id': getattr(error, 'sfqid', None)}
        raise SystemExit(1) from None
    except ValueError as error:
        evidence['failure'] = {'error_type': type(error).__name__, 'message': str(error)}
        print(str(error))
        raise SystemExit(2) from None
    finally:
        if evidence.get('connected'):
            args.evidence.parent.mkdir(parents=True, exist_ok=True)
            args.evidence.write_text(json.dumps(evidence, default=str, indent=2), encoding='utf-8')
            print('Evidence saved: ' + str(args.evidence), flush=True)
        options.pop('password', None)
        options.pop('passcode', None)


if __name__ == '__main__':
    main()
