"""Restricted company entry. Default offline; no implicit archive/stage/commit/deploy."""
from pathlib import Path
import sys,json,argparse,datetime as dt
from contextlib import contextmanager
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from data.controlled_case import build_case,validate_case
from data.count_source_supplement import verify_reviewed_plan
from data.repositories.base import RepositoryError

ACTIONS=['offline-check','preview-count','commit-count','status-count','archive-case','stage-case','preview-a','commit-a','verify-a','status-a','preview-b','commit-b','status-b']
WRITES={'commit-count','archive-case','stage-case','commit-a','commit-b'}
_UNCERTAIN_CONNECTIONS=[]

def inputs(manifest_path,scope='all'):
    manifest=json.loads(Path(manifest_path).read_text(encoding='utf-8'))
    if set(manifest)!={'version','count_plan','count_review_sha256','case_plan','case_hash','source_paths'} or manifest['version']!='OCT29_EXECUTION_APPROVAL_1':raise RepositoryError('Only the fixed reviewed execution manifest is supported.')
    count=None
    if scope in {'all','count'}:
        count=json.loads(Path(manifest['count_plan']).read_text(encoding='utf-8'));verify_reviewed_plan(count,count)
        if len(count['records'])!=13556 or count['review_set_sha256']!=manifest['count_review_sha256']:raise RepositoryError('The 13,556-row count approval scope changed.')
    if scope=='count':return count,None,None
    plan=json.loads(Path(manifest['case_plan']).read_text(encoding='utf-8'));validate_case(plan)
    if plan['case_hash']!=manifest['case_hash'] or len(plan['policy']['phase_a_ids'])!=9 or len(plan['policy']['phase_b_ids'])!=1991 or len(plan['policy']['hold_ids'])!=43 or len(plan['policy']['excluded_ids'])!=56:raise RepositoryError('The reviewed 9/1991/43/56 incremental scope changed.')
    if set(manifest['source_paths'])!={f['name'] for f in plan['policy']['files']}:raise RepositoryError('Unreviewed file paths are not accepted.')
    blobs={name:Path(path).read_bytes() for name,path in manifest['source_paths'].items()}
    if build_case(blobs,plan['policy'])['case_hash']!=manifest['case_hash']:raise RepositoryError('Original bytes no longer reproduce the reviewed case.')
    return count,plan,blobs

@contextmanager
def company(password=None):
    import snowflake.connector
    from snowflake.snowpark import Session
    from data.connection import SnowparkExecutor
    from data.repositories.snowflake import SnowflakeRepository
    from app.snowflake_security import SnowflakeAuthStore
    from app.services.authorized_repository import AuthorizedRepository
    from app.security import Role,Permission,require_permission
    options=dict(connection_name='efns-company',authenticator='SNOWFLAKE',account='qdctnkn-uw19058',user='EFNSDATABASE',role='EFNS_DEV_DEPLOYER',database='EFNS_DEV',warehouse='EFNS_DEV_WH',paramstyle='qmark',login_timeout=30,network_timeout=120)
    if password is not None:options['password']=password
    connection=snowflake.connector.connect(**options);session=None;unknown=False
    try:
        session=Session.builder.configs({'connection':connection}).create();ex=SnowparkExecutor(session);repo=SnowflakeRepository(ex);repo._cs_company()
        login=ex.query('SELECT CURRENT_USER() AS LOGIN').iloc[0]['LOGIN']
        if login!='EFNSDATABASE':raise RepositoryError('Unexpected native company operator.')
        with connection.cursor() as cur:
            cur.execute("SHOW USERS LIKE 'EFNSDATABASE'");query_id=cur.sfqid
            cur.execute('SELECT "name","email","disabled" FROM TABLE(RESULT_SCAN(?))',(query_id,));profile=cur.fetchall()
        if len(profile)!=1 or not profile[0][1] or str(profile[0][2]).lower()!='false':raise RepositoryError('Native operator email/active state cannot be verified.')
        users=ex.query('SELECT USER_ID,EMAIL,DISPLAY_NAME,ROLE,ACTIVE,CREATED_AT,UPDATED_AT,LAST_LOGIN_AT FROM EFNS_DEV.SECURITY.APP_USER WHERE LOWER(EMAIL)=%s',(profile[0][1].casefold(),))
        if len(users)!=1:raise RepositoryError('Native email does not resolve to one application user.')
        actor=SnowflakeAuthStore._user_from_row(users.iloc[0].to_dict());require_permission(actor,Permission.IMPORT_DATA)
        if not actor.active or actor.role!=Role.ADMIN:raise RepositoryError('This restricted operation needs an active application Admin.')
        repo._controlled_independent_reader=lambda: independent(password)
        yield repo,AuthorizedRepository(repo,None,actor)
    except Exception as err:
        if 'COMMIT outcome is unknown' in str(err):
            unknown=True;_UNCERTAIN_CONNECTIONS.append((connection,session))
        raise
    finally:
        if not unknown:
            if session is not None:session.close()
            else:connection.close()

@contextmanager
def independent(password):
    with company(password) as (repo,_authorized):yield repo

def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--manifest',required=True);parser.add_argument('--action',choices=ACTIONS,default='offline-check');parser.add_argument('--allow-company-write',action='store_true');parser.add_argument('--approved-token');parser.add_argument('--password',action='store_true',help='Prompt locally with hidden input; never saved')
    args=parser.parse_args(argv);scope='all' if args.action=='offline-check' else 'count' if args.action.endswith('-count') else 'case';count,plan,blobs=inputs(args.manifest,scope)
    if args.action in WRITES and not args.allow_company_write:parser.error('This action requires separately authorized --allow-company-write and --approved-token; never enabled by default.')
    if args.action=='offline-check':print(json.dumps(dict(status='OFFLINE_VALIDATED',company_connection=False,count_rows=13556,phase_a=9,phase_b_maximum=1991,HOLD=43,excluded=56)));return 0
    if args.action in WRITES and not args.approved_token:parser.error('Explicit immutable approval token required.')
    expected=count['review_set_sha256'] if args.action=='commit-count' else plan['case_hash'] if args.action in {'archive-case','stage-case'} else None
    if expected and args.approved_token!=expected:parser.error('Approved token differs from the reviewed manifest; never auto-refresh it.')
    password=None
    if args.password:
        import getpass
        password=getpass.getpass('Company Snowflake password (hidden, not saved): ')
    out=Path(args.manifest).resolve().parent/'execution_logs';out.mkdir(exist_ok=True);file=out/(dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%SZ')+'_'+args.action+'.json')
    log=dict(action=args.action,attempted_at_utc=dt.datetime.now(dt.timezone.utc).isoformat(),deployment=False);raw=None
    def notify(event):print(json.dumps(event),flush=True)
    try:
        with company(password) as (raw,auth):
            log['identity']=raw._cs_company();action=args.action
            if action=='preview-count':result=auth.preview_count_source_supplement(count)
            elif action=='commit-count':result=auth.commit_count_source_supplement(count,confirmed=True,progress_callback=notify)
            elif action=='status-count':result=auth.get_count_source_supplement_status(count)
            elif action=='archive-case':result=auth.archive_controlled_case(plan,blobs,confirmed=True)
            elif action=='stage-case':result=auth.stage_controlled_case(plan,confirmed=True)
            elif action=='verify-a':result=auth.verify_controlled_phase_a(plan)
            elif action.startswith('preview-'):result=auth.preview_controlled_incremental(plan,action[-1].upper())
            elif action.startswith('status-'):result=auth.get_controlled_incremental_status(plan,action[-1].upper())
            elif action.startswith('commit-'):result=auth.commit_controlled_incremental(plan,action[-1].upper(),args.approved_token,confirmed=True,progress_callback=notify)
            log['result']=result
        # Commit confirmation is followed by a genuinely separate connection.
        if args.action in {'commit-count','commit-a','commit-b'}:
            with company(password) as (_,reader):
                log['independent_verification']=reader.get_count_source_supplement_status(count) if args.action=='commit-count' else reader.get_controlled_incremental_status(plan,args.action[-1].upper())
    except Exception as err:
        log['error']={'type':type(err).__name__,'message':str(err) if isinstance(err,RepositoryError) else 'Native operation failed; inspect local/Query History references. No automatic retry.','query_id':getattr(err,'query_id',getattr(err,'sfqid',None)),'code':getattr(err,'error_code',getattr(err,'errno',None))};log['automatic_retry']=False
        if 'COMMIT outcome is unknown' in str(err):
            log['commit_outcome_unknown']=True
            try:
                with company(password) as (repo,reader):
                    if args.action=='archive-case':repo._cs_restore_case(plan);checked={'status':'ARCHIVES_VERIFIED'}
                    elif args.action=='stage-case':repo._cs_staged(plan);checked={'status':'STAGED_VERIFIED'}
                    else:checked=reader.get_count_source_supplement_status(count) if args.action=='commit-count' else reader.get_controlled_incremental_status(plan,args.action[-1].upper())
                    log['readonly_reconciliation']=checked
                    if checked['status'] in {'COMMITTED_VERIFIED','ARCHIVES_VERIFIED','STAGED_VERIFIED'}:
                        log['outcome_independently_confirmed']=True
                    sid=str(log['identity']['SESSION_ID'])
                    if not sid.isdigit():raise RepositoryError('Saved session identity is not numeric.')
                    log['readonly_query_history']=repo._executor().query('SELECT QUERY_ID,QUERY_TEXT,EXECUTION_STATUS,ERROR_CODE,ERROR_MESSAGE,TRANSACTION_ID FROM TABLE(EFNS_DEV.INFORMATION_SCHEMA.QUERY_HISTORY_BY_SESSION(SESSION_ID=>'+sid+',RESULT_LIMIT=>1000)) ORDER BY START_TIME').to_dict('records')
            except Exception as check:log['readonly_check_error']=type(check).__name__
            # Never close/cancel the uncertain writer before independent evidence.
            if log.get('outcome_independently_confirmed'):
                for native,session in _UNCERTAIN_CONNECTIONS:
                    try:session.close() if session is not None else native.close()
                    except Exception:pass
                _UNCERTAIN_CONNECTIONS.clear()
            else:log['automatic_session_cleanup_skipped']='Outcome not confirmed; operator must use read-only history/receipt checks. No retry or cancel was issued.'
    file.write_text(json.dumps(log,ensure_ascii=False,indent=2,default=str),encoding='utf-8')
    status='CONFIRMED_INDEPENDENTLY_DO_NOT_REPEAT' if log.get('outcome_independently_confirmed') else 'COMMITTED_VERIFICATION_PENDING_DO_NOT_REPEAT' if 'error' in log and log.get('result',{}).get('status')=='COMMITTED' else 'STOPPED_NO_RETRY' if 'error' in log else 'COMPLETED'
    print(json.dumps({'result':status,'action':args.action,'evidence':str(file)},ensure_ascii=False))
    return 1 if 'error' in log and not log.get('outcome_independently_confirmed') else 0

if __name__=='__main__':raise SystemExit(main())
