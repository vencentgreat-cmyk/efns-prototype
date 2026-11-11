# Production sidebar investigation — 2026-11-11

Branch: `codex-nav-production-20261111`.
Base: latest fetched `origin/main`, `ed07dda9ca380ca378e94cfb91dc5f5b0be3ea88`.
Separate worktree: `.local/nav-production-worktree`.

**Outcome: findings only; deployed root cause remains unconfirmed.** No runtime
file was changed. Tests, this report and the integrity manifest are the only
changes. No Snowflake access, deployment, PR, real-data files, or modifications
to another branch/worktree.

## Reported symptom and version

The user confirmed that after a hard refresh, the deployed Production heading
has no chevron and cannot expand; Production Data opens from its Dashboard
link. This is not explained by the local collapsed-section behavior below.

`environment.yml:5` pins `streamlit=1.52.2` for the Snowflake artifact.
Root `requirements.txt:5` allows `streamlit>=1.52.2,<2`; that range alone does
not guarantee the same version. The existing local release virtual environment
reports **1.52.2**, and was used for both AppTest and the headless browser probe.
The deployed stage/container was not inspected, so its actual installed
version and deployed source bytes cannot be independently confirmed here.

## Source and protocol checks

| Check | Evidence and result |
| --- | --- |
| Construction | `app/Home.py:160` builds one grouped dictionary. Production Data is unconditionally registered at `:164`; `:224` only inserts Production Import when `IMPORT_DATA` is granted. No later code removes either entry. |
| Role differences | Admin and Data Editor receive Production Import then Production Data. Reporting Viewer and Developer receive Production Data. This follows existing permissions; no role policy was changed. |
| Routing | `app/Home.py:241` passes the dictionary directly to `st.navigation`; `:262` runs its returned page. Each rerun rebuilds the same permitted entries. |
| URLs/titles | Real navigation messages contain `Production_Import` and `Production_Data`, with distinct titles and script hashes. Every registered URL/hash is unique, across all groups. No `url_path` override or hidden-page option is used. |
| Dashboard links | `app/Home.py:125` uses `st.page_link(page_file(page))`. Captured Dashboard link hashes equal the corresponding sidebar page hashes; these are the same registered pages. |
| File resolution | `app/navigation.py:32` resolves absolute paths to `app/pages`; both `streamlit_app.py` and `app/Home.py` entrypoints pass the tests. |
| CSS | `app/ui.py:46` emits styles for EFNS markup. Its style block at `:50`–`:145` contains no navigation, Production, `display:none`, or visibility-hiding rule. The lone native Markdown selector scopes the EFNS page title. |
| Theme/config | `.streamlit/config.toml:1` and `:13` set light-theme and sidebar colors/fonts/borders. No `client.showSidebarNavigation` override or per-section rule exists. |
| Navigation position | Streamlit 1.52.2 defaults to `position="sidebar", expanded=False`; actual messages specify SIDEBAR. `initial_sidebar_state="expanded"` at `app/Home.py:17` opens the sidebar pane; it does not disable native menu truncation or per-section collapse. |
| Other groups | Production uses the same dictionary/list/Page structure as the other groups. It is second, after Overview; its one or two links fall within the native initial ten-page limit. The only special mutation is the permission-based Import insertion. |
| Packaging | `snowflake.yml` includes `app/*.py`, `app/pages/*.py`, `.streamlit/config.toml` and `environment.yml`. Both Production page files exist. No missing artifact was found in the declared source bundle. Actual deployed artifact parity remains unverified. |

Streamlit's installed 1.52.2 navigation implementation raises on duplicate URL
hashes rather than silently suppressing those pages. `st.page_link` resolves
registered pages without removing them from the menu. Global hidden navigation
would affect the menu as a whole, not just Production.

Reference: [Streamlit 1.52 navigation API](https://docs.streamlit.io/1.52.0/develop/api-reference/navigation/st.navigation).
Implementation behavior was also checked in the installed **1.52.2** Python
and packaged frontend code, rather than assuming current online API behavior.

## Reproduction results

### AppTest

`tests/test_production_navigation.py:23` captures the actual `Navigation`
protocol messages while retaining the real Streamlit enqueue behavior. Eight
cases cover both entrypoints and all four roles, initial render, rerun,
Production Data navigation, and Production Import navigation where permitted.
Assertions cover section membership/order, SIDEBAR position, unique URLs and
hashes, and Dashboard/sidebar target identity. All **8 passed**.

AppTest checks the Python/protocol side; it does not render the React sidebar.

### Local headless browser

An untracked local harness ran the unchanged release entrypoint with the mock
repository and an isolated synthetic Admin session, using Streamlit **1.52.2**
and a separate headless Edge profile. No Snowflake connection was involved.

1. Fresh browser storage: Production Import and Production Data both appeared
   under Production. The header had a Material chevron in the DOM.
   No Streamlit exception was rendered.
2. Deliberately clicking the Production header hid both links while keeping
   the heading **and chevron**. Reload preserved that collapsed state.
3. Clicking the header again restored both links.
4. Clicking Production Data in the sidebar opened its page, with the Reset
   filters control and no Streamlit exception.

The installed frontend stores per-section expansion in browser local storage
under a key beginning `stSidebarSectionsState-`, scoped by the page-link base
URL. A hard refresh does not itself reset that storage. However, this is only
a demonstrated alternative symptom, **not a confirmed cause** of the user's
non-clickable, chevron-free deployed heading. The native overall “View more”
limit also did not hide Production in the fresh browser.

The initial sandboxed browser attempts crashed their renderer/GPU before
rendering. The isolated local browser rerun completed all four checks above.
The harness, profiles, auth database and logs remain untracked under `.local`;
no new browser or application dependency was added.

## Why no runtime change

The reported deployed failure could not be reproduced with the pinned local
version and repository source. Changing URL paths, renaming the group,
forcing `expanded=True`, adding custom navigation, or changing CSS would be
speculative and could mask a deployed-source or embedded-client difference.
In particular, global `expanded=True` does not establish or fix the cause of
a single non-clickable section with no chevron.

The next useful evidence is a comparison of the deployed `app/Home.py`,
`app/ui.py`, `app/navigation.py`, config and environment against this revision,
plus the affected browser's Production header DOM/computed styles and console
errors. A local-storage-free browser session can distinguish persisted state
from deployment/client rendering. These checks require the deployed browser
or artifact evidence; none was accessed during this task.

LF-normalized source fingerprints for an offline artifact comparison:

| File | SHA-256 |
| --- | --- |
| `app/Home.py` | `b32b99b494c5d83ae48dee173d87beb5f07782784930e5edbf4d9b7243da6ddf` |
| `app/ui.py` | `761a3b9a151bf9016c7af9345516e160ddf2e9cab0fa76c6833961a438b611d3` |
| `app/navigation.py` | `1a82a4a92aed31ed06fd8b0510203ab22e4f586f952b60515aa2d9016e6719c0` |
| `.streamlit/config.toml` | `e629191d59cf2d4e9b77594a7c7ed5c1dcd6e11fb64307e18df8b5dcbe3c81b7` |
| `environment.yml` | `d3594dd4c9ef886498924ed1f516adbde7616d8b69795f4ea67295ce9826539d` |

## Validation

- Focused navigation AppTest: **8 passed** (31.99 s).
- Full release suite: **1,988 passed, 1 skipped, 0 failed, 0 errors** (612.92 s).
- Full root suite: **706 passed, 0 skipped, 0 failed, 0 errors** (185.78 s).
- Headless browser: all four checks above completed successfully.
- Manifest: **90 verified hashes**, regenerated from LF-normalized final bytes,
  preserving all existing entries and adding this report and the synthetic
  navigation tests.

Commands: `python -m pytest -q` from the release directory and repository root,
using the existing release virtual environment and existing root Python 3.11
CI environment respectively. The final documentation/manifest update was
followed by the integrity guard and an independent check of all 90 hashes.
