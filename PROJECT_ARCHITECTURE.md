# conversational-rag-with-memory — project architecture

[README](README.md) · [Interview questions and answers](INTERVIEW_QA.md)

## Purpose and scope

A second turn can refer to `it` because prior questions stay in the session.

This document describes files and symbols in this checkout. Deployment templates and statements in the original overview are distinguished from a verified running environment.

## Component diagram

```mermaid
flowchart LR
    M0["src/convrag/__init__.py"]
    M1["src/convrag/main.py"]
    M2["src/convrag/memory.py"]
    M3["src/convrag/ops.py"]
    M1 -->|imports| M2
    M1 -->|imports| M3
```

For Python repositories, arrows show resolved local imports, not network calls or deployment order. Otherwise the diagram is a repository component map; containment arrows do not assert runtime integration.

## Components and responsibilities

| Component | Responsibility |
| --- | --- |
| [`src/convrag/main.py`](src/convrag/main.py) | HTTP handlers: `GET /healthz`, `POST /ask` |
| [`src/convrag/ops.py`](src/convrag/ops.py) | HTTP handlers: `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}` |
| [`src/convrag/memory.py`](src/convrag/memory.py) | Functions: `words`, `ask` |
| [`requirements.txt`](requirements.txt) | Implementation or supporting configuration |
| [`src/convrag/__init__.py`](src/convrag/__init__.py) | Implementation or supporting configuration |
| [`Dockerfile`](Dockerfile) | Container build/service configuration |
| [`Makefile`](Makefile) | Implementation or supporting configuration |
| [`docker-compose.yml`](docker-compose.yml) | Container build/service configuration |
| [`tests/test_memory.py`](tests/test_memory.py) | Executable checks and regression examples |
| [`tests/test_ops.py`](tests/test_ops.py) | Executable checks and regression examples |
| [`.github/workflows/ci.yml`](.github/workflows/ci.yml) | GitHub Actions job definitions |
| [`README.md`](README.md) | Project explanations or operating notes |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | Project explanations or operating notes |

## Existing design and operating guides

These checked-in guides provide the project’s detailed design, operational context, or deployment view:

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## Request interface

| Method and path | Handler | Source |
| --- | --- | --- |
| `GET /healthz` | `healthz` | [`src/convrag/main.py`](src/convrag/main.py#L10) |
| `POST /ask` | `post_ask` | [`src/convrag/main.py`](src/convrag/main.py#L15) |
| `GET /readyz` | `readyz` | [`src/convrag/ops.py`](src/convrag/ops.py#L74) |
| `POST /workspaces` | `create_workspace` | [`src/convrag/ops.py`](src/convrag/ops.py#L80) |
| `GET /workspaces` | `list_workspaces` | [`src/convrag/ops.py`](src/convrag/ops.py#L98) |
| `POST /workspaces/{workspace_id}/jobs` | `create_job` | [`src/convrag/ops.py`](src/convrag/ops.py#L106) |
| `GET /jobs/{job_id}` | `get_job` | [`src/convrag/ops.py`](src/convrag/ops.py#L130) |
| `POST /jobs/{job_id}/approve` | `approve_job` | [`src/convrag/ops.py`](src/convrag/ops.py#L140) |
| `GET /audit` | `audit` | [`src/convrag/ops.py`](src/convrag/ops.py#L160) |
| `GET /metrics` | `metrics` | [`src/convrag/ops.py`](src/convrag/ops.py#L176) |

The table lists literal route decorators found in the inspected Python modules. Router prefixes and middleware can add behavior; check the linked handler and application setup before calling an endpoint.

## Implementation walkthrough

### `ask(session_id, question)`

Source: [`src/convrag/memory.py`](src/convrag/memory.py#L12).

Calls visible in this function: `' '.join`, `SESSIONS.setdefault`, `ValueError`, `history.append`, `isinstance`, `len`, `sorted`, `words`.

```python
def ask(session_id, question):
    if not session_id or not isinstance(session_id, str):
        raise ValueError("session_id is required")
    history = SESSIONS.setdefault(session_id, [])
    combined = " ".join(history[-4:] + [question])
    query = words(combined)
    ranked = sorted(
        ({"source": name, "text": text, "overlap": len(query & words(text))} for name, text in PASSAGES),
        key=lambda row: -row["overlap"],
    )
    best = ranked[0]
    history.append(question)
    answered = best["overlap"] >= 2
    return {
        "answered": answered,
        "answer": best["text"] if answered else "No passage shares enough terms.",
        "citation": best["source"] if answered else None,
        "turns": len(history),
        "passages": ranked,
    }
```

### `words(text)`

Source: [`src/convrag/memory.py`](src/convrag/memory.py#L8).

Calls visible in this function: `re.findall`, `set`, `text.lower`.

```python
def words(text):
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP
```

## Validation and failure paths

| Explicit exception | Source |
| --- | --- |
| `HTTPException(status_code=422, detail=str(exc))` | [`src/convrag/main.py`](src/convrag/main.py#L19) |
| `ValueError('session_id is required')` | [`src/convrag/memory.py`](src/convrag/memory.py#L14) |
| `HTTPException(status_code=404, detail='workspace not found')` | [`src/convrag/ops.py`](src/convrag/ops.py#L77) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/convrag/ops.py`](src/convrag/ops.py#L100) |
| `HTTPException(status_code=404, detail='job not found')` | [`src/convrag/ops.py`](src/convrag/ops.py#L109) |
| `HTTPException(status_code=403, detail='production apply is disabled in this lab')` | [`src/convrag/ops.py`](src/convrag/ops.py#L113) |

These are explicit exceptions in the inspected source, rather than a claim that every failure is handled. Follow the calling handler to see whether the exception becomes an HTTP response or propagates.

## Data and state

- [`src/convrag/memory.py`](src/convrag/memory.py) defines module-level containers: `PASSAGES`, `SESSIONS`, `STOP`.
- [`src/convrag/ops.py`](src/convrag/ops.py) defines module-level containers: `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`.

Module-level dictionaries/lists live in a Python process. They can be fixtures or mutable state; inspect writes before treating them as persistent storage. A production extension would need to define persistence and concurrency behavior explicitly.

## Data flow and design decisions

### What is the input-to-output contract of `ask`

In [`src/convrag/memory.py`](src/convrag/memory.py#L12), `ask(session_id, question)` receives the inputs. The function computes these intermediate values:

- `history = SESSIONS.setdefault(session_id, [])`
- `combined = ' '.join(history[-4:] + [question])`
- `query = words(combined)`
- `ranked = sorted(({'source': name, 'text': text, 'overlap': len(query & words(text))} for name, text in PASSAGES), key=lambda row: -row['overlap'])`
- `best = ranked[0]`
- `answered = best['overlap'] >= 2`

Its result is defined by:

- `{'answered': answered, 'answer': best['text'] if answered else 'No passage shares enough terms.', 'citation': best['source'] if answered else None, 'turns': len(history), 'passages': ranked}`

### Which decision rules or boundary conditions should an interviewer challenge

The implementation in [`src/convrag/memory.py`](src/convrag/memory.py#L12) branches on:

- `not session_id or not isinstance(session_id, str)`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

### What does the operations plane add, and where is its limit

[`src/convrag/ops.py`](src/convrag/ops.py) declares `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/approve`, `GET /audit`, `GET /metrics`. Inspect the application’s `include_router` call for its URL prefix.

Its state containers are `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`. The job-approval handler defines whether a target is accepted or refused; check that branch and the associated tests instead of treating a recorded job as a successful infrastructure apply.

## Setup and verification

The following commands are derived from the checked-in dependency/test contracts. Execute them from the repository root; the block prepares a local environment, not a cloud deployment.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

Python dependencies: [`requirements.txt`](requirements.txt).

Test entry points: [`tests/test_memory.py`](tests/test_memory.py), [`tests/test_ops.py`](tests/test_ops.py).

Automation definitions: [`.github/workflows/ci.yml`](.github/workflows/ci.yml). Read their triggers and job steps to determine what CI actually runs.

## Operating boundaries and design review

Before turning this checkout into a customer deployment, establish the input contract, data ownership, access controls, failure response, evaluation criteria, and rollback owner. Repository fixtures and unit tests demonstrate local behavior; they do not establish throughput, uptime, compliance, or business impact.

A useful architecture review starts with the linked implementation: identify where input enters, where a decision is made, which state can change, and which external dependency can fail. Add a deployment view only for infrastructure that is actually configured and exercised.
