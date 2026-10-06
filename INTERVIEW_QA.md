# conversational-rag-with-memory — interview questions and answers

[README](README.md) · [Project architecture](PROJECT_ARCHITECTURE.md)

Answers below use this repository’s files and implementation. They distinguish existing behavior from suggested extensions; source links let you verify each walkthrough.

## 1. What problem does conversational-rag-with-memory address, and what can you demonstrate?

A second turn can refer to `it` because prior questions stay in the session.

I would demonstrate the linked implementation or examples and distinguish that evidence from any planned production features. Start with [`README.md`](README.md).

## 2. How is this repository organized?

- [`src/convrag/main.py`](src/convrag/main.py): Implementation or supporting configuration.
- [`src/convrag/ops.py`](src/convrag/ops.py): Implementation or supporting configuration.
- [`src/convrag/memory.py`](src/convrag/memory.py): Implementation or supporting configuration.
- [`requirements.txt`](requirements.txt): Implementation or supporting configuration.
- [`src/convrag/__init__.py`](src/convrag/__init__.py): Implementation or supporting configuration.
- [`Dockerfile`](Dockerfile): Container build/service configuration.
- [`Makefile`](Makefile): Implementation or supporting configuration.
- [`docker-compose.yml`](docker-compose.yml): Container build/service configuration.

[PROJECT_ARCHITECTURE.md](PROJECT_ARCHITECTURE.md) contains the component diagram and the implementation walkthrough.

## 3. Can you walk through `ask` and explain the decision it makes?

The main walkthrough here is `ask(session_id, question)` in [`src/convrag/memory.py`](src/convrag/memory.py#L12).

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

The implementation calls `' '.join`, `SESSIONS.setdefault`, `ValueError`, `history.append`, `isinstance`, `len`, `sorted`, `words`. In an interview, trace those calls in execution order using a fixture input.

## 4. What responsibility does `words` have?

`words(text)` is defined in [`src/convrag/memory.py`](src/convrag/memory.py#L8).

Its return expressions include:

- `set(re.findall('[a-z0-9]+', text.lower())) - STOP`

It uses `re.findall`, `set`, `text.lower`. This is the code path I would compare against the caller to explain responsibility boundaries.

## 5. What input validation and failure behavior are implemented?

Explicit failure paths include:

- `HTTPException(status_code=422, detail=str(exc))` in [`src/convrag/main.py`](src/convrag/main.py#L19).
- `ValueError('session_id is required')` in [`src/convrag/memory.py`](src/convrag/memory.py#L14).
- `HTTPException(status_code=404, detail='workspace not found')` in [`src/convrag/ops.py`](src/convrag/ops.py#L77).
- `HTTPException(status_code=404, detail='job not found')` in [`src/convrag/ops.py`](src/convrag/ops.py#L100).
- `HTTPException(status_code=404, detail='job not found')` in [`src/convrag/ops.py`](src/convrag/ops.py#L109).
- `HTTPException(status_code=403, detail='production apply is disabled in this lab')` in [`src/convrag/ops.py`](src/convrag/ops.py#L113).

I would test both the condition that reaches each exception and the caller that translates it. An explicit raise does not mean every malformed input or dependency failure is handled.

## 6. Which test would you use to demonstrate correctness?

[`tests/test_memory.py`](tests/test_memory.py#L12) contains `test_second_turn_uses_memory`:

```python
def test_second_turn_uses_memory():
    first = client.post("/ask", json={"session_id": "s1", "question": 'What is the error budget minutes?'}).json()
    assert first["answered"] is True
    second = client.post("/ask", json={"session_id": "s1", "question": 'Who cares about it during rollback?'}).json()
    assert second["turns"] == 2
    assert second["citation"] == "budget.md"
```

This is a concrete regression example from the repository. Its assertions establish that case; they do not establish behavior for every input or under production load.

## 7. What HTTP interface does the code expose?

- `GET /healthz` → `healthz` in [`src/convrag/main.py`](src/convrag/main.py#L10).
- `POST /ask` → `post_ask` in [`src/convrag/main.py`](src/convrag/main.py#L15).
- `GET /readyz` → `readyz` in [`src/convrag/ops.py`](src/convrag/ops.py#L74).
- `POST /workspaces` → `create_workspace` in [`src/convrag/ops.py`](src/convrag/ops.py#L80).
- `GET /workspaces` → `list_workspaces` in [`src/convrag/ops.py`](src/convrag/ops.py#L98).
- `POST /workspaces/{workspace_id}/jobs` → `create_job` in [`src/convrag/ops.py`](src/convrag/ops.py#L106).
- `GET /jobs/{job_id}` → `get_job` in [`src/convrag/ops.py`](src/convrag/ops.py#L130).
- `POST /jobs/{job_id}/approve` → `approve_job` in [`src/convrag/ops.py`](src/convrag/ops.py#L140).

These are literal decorators. Application/router prefixes, authentication, and middleware must be checked in the corresponding setup code.

## 8. Where does state live, and what happens with multiple workers?

Module-level containers include `PASSAGES`, `SESSIONS`, `STOP` in [`src/convrag/memory.py`](src/convrag/memory.py); `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS` in [`src/convrag/ops.py`](src/convrag/ops.py).

These containers belong to a Python process. Inspect which are constant fixtures and which are mutated. Mutable process state needs an explicit shared-storage or synchronization strategy before multiple workers can provide consistent behavior.

## 9. How would another engineer reproduce your walkthrough?

Start from the repository root:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pytest -q
```

These commands follow repository manifests; environment setup and command results still need to be checked on the target machine.

## 10. What does automation verify, and what does it not prove?

Inspect [`.github/workflows/ci.yml`](.github/workflows/ci.yml) for triggers, permissions, and job commands. I would name the checks that those definitions run and show the latest run separately. A workflow definition alone does not establish a successful deployment, security review, or production SLO.

## 11. How would you present this project in a Forward Deployed Engineer interview?

Start with the user and operational problem described in [`README.md`](README.md). Explain one constraint that changes the implementation, show the linked code or example, and walk through a success case and a failure case. Agree on a measurable acceptance criterion before expanding the solution, and leave a handoff with data boundaries and rollback ownership. Any proposed production or business metric should be identified as a target until measured.

## 12. What is the input-to-output contract of `ask`?

In [`src/convrag/memory.py`](src/convrag/memory.py#L12), `ask(session_id, question)` receives the inputs. The function computes these intermediate values:

- `history = SESSIONS.setdefault(session_id, [])`
- `combined = ' '.join(history[-4:] + [question])`
- `query = words(combined)`
- `ranked = sorted(({'source': name, 'text': text, 'overlap': len(query & words(text))} for name, text in PASSAGES), key=lambda row: -row['overlap'])`
- `best = ranked[0]`
- `answered = best['overlap'] >= 2`

Its result is defined by:

- `{'answered': answered, 'answer': best['text'] if answered else 'No passage shares enough terms.', 'citation': best['source'] if answered else None, 'turns': len(history), 'passages': ranked}`

## 13. Which decision rules or boundary conditions should an interviewer challenge?

The implementation in [`src/convrag/memory.py`](src/convrag/memory.py#L12) branches on:

- `not session_id or not isinstance(session_id, str)`

A useful extension is a table-driven test that covers each condition just below, at, and above its boundary where applicable. These expressions are the current rules; changing them changes behavior and should be justified by the project’s acceptance criteria.

## 14. What does the operations plane add, and where is its limit?

[`src/convrag/ops.py`](src/convrag/ops.py) declares `GET /readyz`, `POST /workspaces`, `GET /workspaces`, `POST /workspaces/{workspace_id}/jobs`, `GET /jobs/{job_id}`, `POST /jobs/{job_id}/approve`, `GET /audit`, `GET /metrics`. Inspect the application’s `include_router` call for its URL prefix.

Its state containers are `_WORKSPACES`, `_JOBS`, `_AUDIT`, `_METRICS`. The job-approval handler defines whether a target is accepted or refused; check that branch and the associated tests instead of treating a recorded job as a successful infrastructure apply.
