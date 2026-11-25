"""Shared presentation helpers for the EFNS Streamlit application."""

from __future__ import annotations

import html

import streamlit as st

from app.security import AuthenticationError, AuthorizationError, UserValidationError
from data.repositories.base import ConcurrencyError, RepositoryConfigurationError, RepositoryConnectionError, RepositoryError


def clear_widget_prefix(prefix: str, keep: tuple[str, ...] = ()) -> None:
    """Clear dependent widgets after an edit-record selector changes."""
    for key in list(st.session_state):
        if key.startswith(prefix) and key not in keep:
            st.session_state.pop(key, None)


def show_data_error(error: Exception) -> None:
    """Render repository failures without exposing SQL or connection details."""
    if isinstance(error, ConcurrencyError):
        st.warning("This record has changed. Reload the record before saving your changes again.")
    elif isinstance(error, AuthenticationError):
        st.error("Invalid email or password, or the account is inactive.")
    elif isinstance(error, AuthorizationError):
        st.error("You do not have permission to perform this action.")
    elif isinstance(error, UserValidationError):
        st.error(str(error))
    elif isinstance(error, RepositoryConfigurationError):
        st.error("Snowflake is not configured. Review System Status and the deployment settings.")
    elif isinstance(error, RepositoryConnectionError):
        st.error("Snowflake could not be reached. Check connection settings, network access, and permissions.")
    elif isinstance(error, RepositoryError):
        st.error(str(error) or "The data operation could not be completed.")
    else:
        st.error(str(error))


def optional_form_date(value):
    """Keep a missing SQL/pandas DATE empty, without shifting known dates."""
    import pandas as pd
    return None if value is None or pd.isna(value) else value


def apply_theme() -> None:
    """Add styles only for EFNS-owned markup; native widgets use config.toml."""
    st.markdown(
        """
        <style>
        .efns-brand {
            margin: 0 0 1.5rem;
            padding: .5rem 0 1rem;
            color: #202C32;
            border-bottom: 1px solid #CBD2D1;
            font-size: 1.04rem;
            font-weight: 700;
        }
        .efns-brand small {
            display: block;
            color: #55636B;
            font-size: .875rem;
            font-weight: 500;
            margin-top: .5rem;
        }
        .efns-page-header {
            padding: .5rem 0 1rem;
            margin: 0 0 1.5rem;
            border-bottom: 2px solid #225C80;
        }
        .efns-eyebrow {
            color: #55636B;
            font-size: .875rem;
            font-weight: 600;
        }
        .efns-page-header h1.efns-page-title {
            color: #202C32;
            font-family: "Source Serif", serif, sans-serif;
            font-size: 1.75rem;
            font-weight: 600;
            line-height: 1.2;
            margin: .5rem 0;
        }
        .efns-page-copy {
            color: #55636B;
            line-height: 1.5;
            margin: 0;
        }
        .efns-section-title {
            color: #202C32;
            font-family: "Source Sans", sans-serif;
            font-size: 1.25rem;
            font-weight: 600;
            margin: 1.5rem 0 .5rem;
        }
        h3.efns-section-title {
            font-size: 1.125rem;
            margin-top: 1rem;
        }
        .efns-section-copy {
            color: #55636B;
            font-size: .875rem;
            line-height: 1.45;
            margin: 0 0 1rem;
        }
        .efns-status {
            display: inline-block;
            padding: .5rem;
            background: #EBEFF2;
            color: #375E7A;
            font-size: .875rem;
            font-weight: 600;
        }
        .efns-repository {
            color: #55636B;
            font-size: .875rem;
            margin: .5rem 0 1rem;
        }
        .efns-next-step {
            color: #202C32;
            min-height: 7.2rem;
            padding: 1rem 0;
        }
        .efns-next-step strong {
            color: #202C32;
            display: block;
            margin-bottom: .5rem;
        }
        .efns-next-step span {
            color: #55636B;
            font-size: .875rem;
            line-height: 1.45;
        }
        @media (max-width: 800px) {
            .efns-next-step { min-height: auto; }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def page_header(title: str, description: str, eyebrow: str = "EFNS DATA SYSTEM") -> None:
    st.markdown(
        f"""
        <section class="efns-page-header">
          <div class="efns-eyebrow">{html.escape(eyebrow)}</div>
          <h1 class="efns-page-title">{html.escape(title)}</h1>
          <p class="efns-page-copy">{html.escape(description)}</p>
        </section>
        """,
        unsafe_allow_html=True,
    )


def section_intro(title: str, description: str = "", *, level: int = 2) -> None:
    """Render an escaped section heading without skipping the page title level."""
    tag = "h3" if level == 3 else "h2"
    copy = (
        f'<p class="efns-section-copy">{html.escape(description)}</p>'
        if description
        else ""
    )
    st.markdown(
        f'<{tag} class="efns-section-title">{html.escape(title)}</{tag}>{copy}',
        unsafe_allow_html=True,
    )


def secondary_text(text: str) -> None:
    """Use the shared readable secondary style for supporting instructions."""
    st.markdown(
        f'<p class="efns-section-copy">{html.escape(text)}</p>',
        unsafe_allow_html=True,
    )
