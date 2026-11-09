"""Signed daily Adjustment only; synthetic Mock/AppTest, no company writes."""
from decimal import Decimal

import pandas as pd
import pytest

from data.validation import validate_quota_transaction, quota_count_error
from data.repositories.base import RepositoryError
from tests.test_staff_workflows import chain
from tests.test_daily_quota_entry import quota_app


ACTOR={'user_id':'DEV_TEST adjustment reviewer','email':'synthetic.adjustment@nsegg.ca'}


def payload(quota,kind='Adjustment',quantity=-5,related=None):
    return dict(QUOTA_ID=quota,TRANSACTION_TYPE=kind,QUOTA_COUNT=quantity,
                EFFECTIVE_DATE='2026-01-01',RELATED_ACCOUNT_ID=related,PRICE=None)


@pytest.mark.parametrize('quantity', [-5,Decimal('-0.1250'),Decimal('2.1250')])
def test_adjustment_create_and_correction_keep_signed_decimal_and_unknown_price(chain,quantity):
    repo,account,other,facility,quota,*_=chain
    record=payload(quota,quantity=quantity)
    assert not validate_quota_transaction(repo,record)
    target=repo.create_record_once('QUOTA_TRANSACTION',record,'DEV_TEST signed create',actor=ACTOR)
    before=repo.get_quota_transaction(target)
    repo.revise_record('QUOTA_TRANSACTION',target,{'QUOTA_COUNT':Decimal('-7.0625')},
        'DEV_TEST interim allocation correction','DEV_TEST signed edit',actor=ACTOR,
        expected_updated_at=before['UPDATED_AT'])
    after=repo.get_quota_transaction(target)
    assert after['QUOTA_COUNT']==Decimal('-7.0625') and pd.isna(after['PRICE'])
    assert after['TRANSACTION_TYPE']=='Adjustment' and pd.isna(after['RELATED_ACCOUNT_ID'])
    assert len(repo.get_record_revisions())==2


@pytest.mark.parametrize('quantity',[0,Decimal('-0.0000'),'NaN',float('nan'),'Infinity','-Infinity',None,True])
def test_adjustment_invalid_quantity_blocks_create_and_edit_without_partial_history(chain,quantity):
    repo,account,other,facility,quota,*_=chain
    assert quota_count_error(quantity,'Adjustment')
    assert any('non-zero' in e for e in validate_quota_transaction(repo,payload(quota,quantity=quantity)))
    with pytest.raises((ValueError,RepositoryError)):
        repo.create_record_once('QUOTA_TRANSACTION',payload(quota,quantity=quantity),'DEV_TEST invalid',actor=ACTOR)
    assert repo.get_quota_transactions().empty and repo.get_record_revisions().empty
    target=repo.upsert_quota_transaction(payload(quota,quantity=-5))
    before=repo._quota_transactions.copy(deep=True)
    with pytest.raises((ValueError,RepositoryError)):
        repo.revise_record('QUOTA_TRANSACTION',target,{'QUOTA_COUNT':quantity},
            'DEV_TEST invalid correction','DEV_TEST invalid edit',actor=ACTOR,
            expected_updated_at=repo.get_quota_transaction(target)['UPDATED_AT'])
    pd.testing.assert_frame_equal(repo._quota_transactions,before)
    assert repo.get_record_revisions().empty


@pytest.mark.parametrize('kind',['Purchase','Sale','Lease (In)','Lease (Out)','Lease In','Lease Out','Base'])
def test_other_types_stay_positive_on_create_and_correction(chain,kind):
    repo,account,other,facility,quota,*_=chain
    assert any('greater than zero' in e for e in validate_quota_transaction(repo,payload(quota,kind,-1,other)))
    with pytest.raises((ValueError,RepositoryError)):
        repo.upsert_quota_transaction(payload(quota,kind,-1,other))
    target=repo.upsert_quota_transaction(payload(quota,kind,1,other))
    before=repo._quota_transactions.copy(deep=True)
    with pytest.raises((ValueError,RepositoryError),match='greater than zero'):
        repo.revise_record('QUOTA_TRANSACTION',target,{'QUOTA_COUNT':Decimal('-0.1250')},
            'DEV_TEST wrong sign','DEV_TEST wrong sign',actor=ACTOR,
            expected_updated_at=repo.get_quota_transaction(target)['UPDATED_AT'])
    pd.testing.assert_frame_equal(repo._quota_transactions,before)
    assert repo.get_record_revisions().empty


def test_type_only_correction_cannot_turn_negative_adjustment_into_sale(chain):
    repo,account,other,facility,quota,*_=chain
    target=repo.upsert_quota_transaction(payload(quota,quantity=-5,related=other))
    before=repo._quota_transactions.copy(deep=True)
    with pytest.raises(RepositoryError,match='greater than zero'):
        repo.revise_record('QUOTA_TRANSACTION',target,{'TRANSACTION_TYPE':'Sale'},
            'DEV_TEST change type','DEV_TEST change type',actor=ACTOR,
            expected_updated_at=repo.get_quota_transaction(target)['UPDATED_AT'])
    pd.testing.assert_frame_equal(repo._quota_transactions,before)


def test_actual_page_negative_adjustment_create_edit_and_notes_preserve_price(chain,tmp_path,monkeypatch):
    repo,account,other,facility,quota,*_=chain
    app=quota_app(repo,tmp_path,monkeypatch)
    assert app.selectbox(key='quota_tx_form_type').value=='Adjustment'
    assert app.selectbox(key='quota_tx_form_related_account').label=='Related Account'
    assert app.number_input(key='quota_tx_form_count').proto.help=='Use a negative number for a decrease'
    app.number_input(key='quota_tx_form_count').set_value(-5.125)
    app.text_area(key='quota_tx_form_comments').input('DEV_TEST Interim Allocation Adjustment')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    row=repo.get_quota_transactions().iloc[0]
    assert row.QUOTA_COUNT==-5.125 and pd.isna(row.PRICE)
    app.button(key='quota_tx_record_edit').click().run()
    app.text_input(key='quota_tx_form_count').input('-7.0625')
    app.text_input(key='quota_tx_form_revision_reason').input('DEV_TEST signed edit')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    assert repo.get_quota_transaction(row.QUOTA_TRANSACTION_ID)['QUOTA_COUNT']==Decimal('-7.0625')
    app.button(key='quota_tx_record_edit').click().run()
    app.text_area(key='quota_tx_form_comments').input('DEV_TEST historical notes only')
    app.text_input(key='quota_tx_form_revision_reason').input('DEV_TEST keep negative')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    after=repo.get_quota_transaction(row.QUOTA_TRANSACTION_ID)
    assert after['QUOTA_COUNT']==Decimal('-7.0625') and pd.isna(after['PRICE'])


def test_actual_page_zero_adjustment_blocks_and_other_types_have_nonnegative_input(chain,tmp_path,monkeypatch):
    repo,*_=chain
    app=quota_app(repo,tmp_path,monkeypatch)
    app.number_input(key='quota_tx_form_count').set_value(0)
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and any('non-zero' in e.value for e in app.error)
    assert repo.get_quota_transactions().empty and repo.get_record_revisions().empty
    app.selectbox(key='quota_tx_form_type').select('Purchase').run()
    assert app.number_input(key='quota_tx_form_count').proto.min==0


@pytest.mark.parametrize('kind',['Adjustment','Sale'])
@pytest.mark.parametrize('price',[None,0])
def test_unchanged_synthetic_historical_negative_row_keeps_all_other_values(chain,tmp_path,monkeypatch,kind,price):
    repo,account,other,facility,quota,*_=chain
    # An adversarial legacy fixture, not a claim that negative historical Sales exist.
    row=dict(QUOTA_TRANSACTION_ID='DEV_TEST historical signed row',QUOTA_ID=quota,
             OWNER_ACCOUNT_ID=account,RELATED_ACCOUNT_ID=other,TRANSACTION_TYPE=kind,
             QUOTA_COUNT=Decimal('-5.1250'),PRICE=price,QUOTA_LEASE_TYPE='Non One Time Credit',
             EFFECTIVE_DATE='2010-01-01',END_DATE=None,COMMENTS='old',
             UPDATED_AT='2026-01-01T00:00:00.123456789')
    repo._quota_transactions=pd.concat([repo._quota_transactions,pd.DataFrame([row])],ignore_index=True)
    before=repo._quota_transactions.copy(deep=True)
    app=quota_app(repo,tmp_path,monkeypatch,'edit',row['QUOTA_TRANSACTION_ID'])
    assert not app.exception and app.text_input(key='quota_tx_form_count').value=='-5.1250'
    app.text_area(key='quota_tx_form_comments').input('DEV_TEST historical notes preserved')
    app.text_input(key='quota_tx_form_revision_reason').input('DEV_TEST notes-only correction')
    app.button(key='quota_tx_record_save').click().run()
    assert not app.exception and not app.error
    unchanged=[c for c in before if c not in {'UPDATED_AT','COMMENTS'}]
    pd.testing.assert_frame_equal(repo._quota_transactions[unchanged],before[unchanged])
    assert len(repo.get_record_revisions())==1
