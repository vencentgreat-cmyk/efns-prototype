# ============================================================
# EFNS Prototype v0.1 — Tests
# ============================================================
"""Basic unit/integration tests for the prototype."""

import datetime as dt
import sys
import os

# Ensure project root is on path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import pytest

from data.synthetic import generate_all, generate_accounts, generate_production
from data.repositories.mock import MockRepository
from data.repositories.base import BaseRepository


class TestSyntheticData:
    """Verify synthetic data generation is deterministic and complete."""

    def test_accounts_generated(self):
        df = generate_accounts(seed=42)
        assert len(df) == 12
        assert "ACCOUNT_ID" in df.columns
        assert "ORGANIZATION_NAME" in df.columns
        assert "PRODUCER_ROLE" in df.columns

    def test_full_dataset_consistent(self):
        data = generate_all(seed=42)
        assert len(data["accounts"]) == 12
        assert len(data["facilities"]) > 0
        assert len(data["flocks"]) > 0
        assert len(data["production"]) == 200
        # Facilities reference valid account IDs
        acc_ids = set(data["accounts"]["ACCOUNT_ID"])
        fac_ids = set(data["facilities"]["ACCOUNT_ID"])
        assert fac_ids.issubset(acc_ids)
        # Flocks reference valid account IDs
        flock_acc_ids = set(data["flocks"]["ACCOUNT_ID"])
        assert flock_acc_ids.issubset(acc_ids)

    def test_production_has_flock_link(self):
        data = generate_all(seed=42)
        prod = data["production"]
        assert "FLOCK_ID" in prod.columns
        assert prod["FLOCK_ID"].notna().any()

    def test_determinism(self):
        """Deterministic columns (excluding timestamps) match across seeds."""
        a1 = generate_accounts(seed=42)
        a2 = generate_accounts(seed=42)
        # Exclude timestamp columns
        cols = [c for c in a1.columns if c not in ("CREATED_AT", "UPDATED_AT")]
        pd.testing.assert_frame_equal(a1[cols], a2[cols])

    def test_production_deterministic(self):
        p1 = generate_production(seed=42)
        p2 = generate_production(seed=42)
        assert (p1["GRADER_NUMBER"] == p2["GRADER_NUMBER"]).all()
        assert (p1["TOTAL_RECEIVED"] == p2["TOTAL_RECEIVED"]).all()


class TestMockRepository:
    """Verify the in-memory repository operations."""

    @pytest.fixture
    def repo(self):
        return MockRepository(seed=42)

    def test_get_accounts(self, repo):
        df = repo.get_accounts()
        assert len(df) == 12
        assert isinstance(df, pd.DataFrame)

    def test_get_account(self, repo):
        df = repo.get_accounts()
        aid = df["ACCOUNT_ID"].iloc[0]
        record = repo.get_account(aid)
        assert record is not None
        assert record["ACCOUNT_ID"] == aid

    def test_upsert_account(self, repo):
        aid = repo.upsert_account({
            "ORGANIZATION_NAME": "Test Farm",
            "PRODUCER_ROLE": True,
        })
        record = repo.get_account(aid)
        assert record["ORGANIZATION_NAME"] == "Test Farm"

    def test_delete_account(self, repo):
        df = repo.get_accounts()
        aid = df["ACCOUNT_ID"].iloc[0]
        assert repo.delete_account(aid)
        assert repo.get_account(aid) is None

    def test_get_production_records(self, repo):
        df = repo.get_production_records()
        assert len(df) == 200

    def test_production_filters(self, repo):
        all_records = repo.get_production_records()
        assert len(all_records) > 0
        sample_colour = all_records["EGG_COLOUR"].dropna().iloc[0]
        filtered = repo.get_production_records(egg_colour=sample_colour)
        assert len(filtered) > 0
        assert all(c == sample_colour for c in filtered["EGG_COLOUR"])

    def test_summary_metrics(self, repo):
        metrics = repo.get_production_summary_metrics()
        assert metrics["production_record_count"] == 200
        assert metrics["account_count"] == 12
        assert metrics["total_received"] > 0
        assert metrics["total_accepted"] > 0

    def test_create_import_batch(self, repo):
        import_id = repo.create_import_batch({
            "FILENAME": "test.csv",
            "SOURCE": "Test",
        })
        batches = repo.get_import_batches()
        assert any(b["IMPORT_ID"] == import_id for b in batches.to_dict("records"))

    def test_insert_production_from_df(self, repo):
        import_id = repo.create_import_batch({
            "FILENAME": "test_insert.csv",
            "SOURCE": "Test Insert",
            "REPORTING_YEAR": 2025,
            "REPORTING_WEEK": 10,
        })
        df = pd.DataFrame([
            {
                "GRADER_NUMBER": "G-999",
                "BARN_IDENTITY": "Barn-T1",
                "FLOCK_AGE": 50,
                "EGG_COLOUR": "White",
                "NET_WEIGHT": 1000.0,
                "NET_BOXES": 50.0,
                "NET_PER_BOX": 20.0,
                "TOTAL_RECEIVED": 50.0,
                "REJECTED": 1.0,
                "LOSS": 0.5,
                "TOTAL_ACCEPTED": 48.5,
            }
        ])
        count = repo.insert_production_records(df, import_id)
        assert count == 1
        # Verify inserted
        all_prod = repo.get_production_records()
        assert (all_prod["GRADER_NUMBER"] == "G-999").any()


class TestRepositoryInterface:
    """Verify MockRepository satisfies the abstract interface."""

    def test_conforms_to_base(self):
        repo = MockRepository()
        assert isinstance(repo, BaseRepository)