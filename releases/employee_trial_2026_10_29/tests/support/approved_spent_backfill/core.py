"""Restricted orchestration; writes ONLY through deployed revise_record."""
import hashlib,json
from app.security import Permission,Role,require_permission
from data.repositories.base import RepositoryError
from data.business_time import version_bind
from data.repositories.continuity import stable_id

FIELD='SPENT_FOWL_PLANS_ACCOUNT_ID'
APPROVED_HASH='SYNTHETIC_REVIEW_ONLY_NOT_A_COMPANY_APPROVAL'
BATCH='SYNTHETIC'

def digest(v):return hashlib.sha256(json.dumps(v,sort_keys=True,separators=(',',':'),default=str).encode()).hexdigest()

def checked_plan(plan,expected_hash=APPROVED_HASH,expected_batch=BATCH):
 rows=plan.get('records',[])
 if len(rows)!=26 or len({r['source_account_guid'] for r in rows})!=26 or len({(r['original_batch'],r['raw_row_id']) for r in rows})!=26:raise RepositoryError('Approved scope must contain exactly 26 unique source identities.')
 for row in rows:
  proposal=row['proposal']
  if digest(proposal)!=row['review_token']:raise RepositoryError('A reviewed record token changed.')
  for name in ['original_batch','raw_row_id','source_account_guid','proposed_lookup_id','expected_updated_at_ff9','raw_payload_sha256','normalized_payload_sha256']:
   if row[name]!=proposal[name]:raise RepositoryError('Flattened plan does not match reviewed proposal.')
  if row['target_expected_updated_at_ff9']!=proposal['target_updated_at_ff9'] or row['current_database_lookup_id']!=proposal['expected_old_link']:raise RepositoryError('Reviewed old value or target version differs.')
  if row['original_batch']!=expected_batch or row['disposition']!='READY_FOR_USER_REVIEW' or proposal['expected_old_link'] is not None:raise RepositoryError('Plan is outside the approved blank-link supplement.')
 key=digest([{'request_id':r['proposed_request_id'],'review_token':r['review_token']} for r in rows])
 if key!=expected_hash or key!=plan['review_set_sha256']:raise RepositoryError('The approved review-set hash changed; do not refresh it to proceed.')
 return rows

def reason_for(row,review_hash):
 return json.dumps({'operation':'Approved Spent Fowl Plans supplement','review_set':review_hash,'batch':row['original_batch'],'raw_row_id':row['raw_row_id'],'source_account':row['source_account_guid'],'source_hash':row['raw_payload_sha256'],'mapping':'EFNS-ACCOUNT-RELATIONSHIPS-1','review_token':row['review_token']},sort_keys=True,separators=(',',':'))

def identities(row):
 return (stable_id('revision','ACCOUNT',row['source_account_guid'],row['proposed_request_id']),stable_id('record-audit','ACCOUNT',row['source_account_guid'],row['proposed_request_id'],'ATTRIBUTE_CORRECTION'))

def run_atomic(repo,authorized,rows,review_hash,prepare,verify,progress=None):
 require_permission(authorized.actor,Permission.UPDATE_DATA)
 if authorized.actor.role!=Role.ADMIN:raise RepositoryError('Only the authenticated application Admin may execute this approved supplement.')
 # Do not use executor.transaction(): the repository owns exactly one intake transaction.
 with repo._continuity_transaction() as tx:
  state=prepare(tx)
  if state.get('already_applied'):
   verify(tx,state)
   return {'status':'ALREADY_APPLIED','new_rows':0,'verified':26}
  for number,row in enumerate(rows,1):
   authorized.revise_record('ACCOUNT',row['source_account_guid'],{FIELD:row['proposed_lookup_id']},reason_for(row,review_hash),row['proposed_request_id'],expected_updated_at=row['expected_updated_at_ff9'])
   if progress:progress(number,26,'PROCESSED_IN_TRANSACTION_NOT_COMMITTED')
  verify(tx,state)
 return {'status':'COMMIT_CONFIRMED','new_rows':26,'verified':26}
