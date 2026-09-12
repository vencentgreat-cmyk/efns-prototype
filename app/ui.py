"""Shared presentation helpers for the EFNS Streamlit application."""

from __future__ import annotations

import html

import streamlit as st

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
    elif isinstance(error, RepositoryConfigurationError):
        st.error("Snowflake is not configured. Review System Status and the deployment settings.")
    elif isinstance(error, RepositoryConnectionError):
        st.error("Snowflake could not be reached. Check connection settings, network access, and permissions.")
    elif isinstance(error, RepositoryError):
        st.error(str(error) or "The data operation could not be completed.")
    else:
        st.error(str(error))


def apply_theme() -> None:
    """Add styles only for EFNS-owned markup; native widgets use config.toml."""
    st.markdown(
        """
        <style>
        .efns-brand {
            margin: .35rem 0 1rem;
            padding: .9rem 1rem;
            background: #172554;
            color: #ffffff;
            border-radius: 8px;
            font-size: 1.04rem;
            font-weight: 700;
        }
        .efns-brand small {
            display: block;
            color: #dbe4ff;
            font-size: .75rem;
            font-weight: 500;
            margin-top: .2rem;
        }
        .efns-page-header {
            background: #ffffff;
            border: 1px solid #d8dee9;
            border-left: 5px solid #3f56d9;
            border-radius: 10px;
            padding: 1.15rem 1.35rem;
            margin: .35rem 0 1.25rem;
            box-shadow: 0 2px 8px rgba(23, 32, 51, .04);
        }
        .efns-eyebrow {
            color: #3f56d9;
            font-size: .72rem;
            font-weight: 700;
            letter-spacing: .09em;
            text-transform: uppercase;
        }
        .efns-page-title {
            color: #172033;
            font-size: 1.72rem;
            line-height: 1.2;
            margin: .28rem 0 .32rem;
        }
        .efns-page-copy {
            color: #667085;
            line-height: 1.5;
            margin: 0;
        }
        .efns-section-title {
            color: #172033;
            font-size: 1.02rem;
            font-weight: 700;
            margin: .35rem 0 .2rem;
        }
        .efns-section-copy {
            color: #667085;
            font-size: .88rem;
            line-height: 1.45;
            margin: 0 0 .75rem;
        }
        .efns-status {
            display: inline-block;
            padding: .28rem .58rem;
            border-radius: 999px;
            background: #e8ecff;
            color: #243bb6;
            font-size: .72rem;
            font-weight: 700;
        }
        .efns-repository {
            color: #667085;
            font-size: .8rem;
            margin: .3rem 0 .65rem;
        }
        .efns-next-step {
            background: #ffffff;
            border: 1px solid #d8dee9;
            border-radius: 8px;
            color: #172033;
            min-height: 7.2rem;
            padding: 1rem;
        }
        .efns-next-step strong {
            color: #172554;
            display: block;
            margin-bottom: .35rem;
        }
        .efns-next-step span {
            color: #667085;
            font-size: .88rem;
            line-height: 1.45;
        }
        @media (max-width: 800px) {
            .efns-page-header { padding: 1rem; }
            .efns-page-title { font-size: 1.45rem; }
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


def section_intro(title: str, description: str = "") -> None:
    copy = (
        f'<p class="efns-section-copy">{html.escape(description)}</p>'
        if description
        else ""
    )
    st.markdown(
        f'<div class="efns-section-title">{html.escape(title)}</div>{copy}',
        unsafe_allow_html=True,
    )
