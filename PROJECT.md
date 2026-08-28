# RPA Web Automator — project profile (Nexus Harness v4)

Nexus registry id: `projects.rpa-web-automator`
Repository: `Rubens-Marques/rpa-web-automator`
Client: `nexus`
Status: `active`

Global workflow, quality policy, security normalization, memory, and runtime
policies come from **Nexus Harness v4**. This file is project-specific only.

## Architecture

- Python RPA (pytest). Sem workflow GitHub legado.

## Commands

pytest via `pytest.ini`. Sem CI legado.

## CI

- **Legacy (preserved):** Nenhum workflow legado — não inventar deploy.
- **Nexus (this PR):** `.github/workflows/nexus-quality-gate.yml` on `[self-hosted, nexus-ci]` — affected graph + Python contract test + `py_compile` do adapter + Trivy canônico (`normalize_trivy`). Sem lint/typecheck/unit/build de produto. Sem Testcontainers. Sem image build. Sem deploy.

O runner `nexus-ci` está hoje **repo-scoped** em `NexusDataBI/marketing-hub`. Neste repo o job fica em fila até a onda 2 (runner org ou por-repo). Isso não é falha silenciosa do adapter.

## Constraints

- PR permanece draft até autorização explícita de merge deste repo.
- Não apagar skills/MCP/plugins Cursor. Não substituir `ci.yml` legado.
- Não colocar secrets de produção no job `nexus-ci`.
