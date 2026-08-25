# ADR-012 — CI/CD e Production Engineering

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Até o fim do Bloco 3, qualidade (lint, type check, testes), segurança (dependências, SAST,
segredos) e a imagem Docker eram verificadas apenas manualmente, sob demanda, e a imagem rodava
como `root` num único estágio de build. Não havia pipeline de CI/CD, nem hardening de container
para produção. Este bloco (Sprint 12) fecha essa lacuna: automatiza as mesmas verificações já
usadas manualmente em CI, e endurece a imagem real.

## 2. Decisão

- **Dockerfile multi-stage**: estágio `builder` instala dependências via `uv sync --frozen`;
  estágio `runtime` copia apenas `.venv`, `src`, `alembic.ini`, `migrations`, `data` — sem
  toolchain de build na imagem final. `USER app` (uid/gid 999, não-root) a partir da última
  etapa. `HEALTHCHECK` via `urllib.request` (sem depender de `curl` na imagem).
- **`init: true`** no serviço `api` do `docker-compose.yml` — roda `tini` como PID 1 em vez de
  `uvicorn` diretamente, para colher processos órfãos (ver defeito real abaixo).
- **Quatro workflows GitHub Actions**, cada um espelhando comandos já provados manualmente nos
  Blocos 1–3: `ci.yml` (lint, format, mypy, pytest com Postgres/pgvector real via `services:`),
  `security.yml` (`pip-audit`, `semgrep --config auto`, `gitleaks` com baseline), `docker.yml`
  (build, Trivy, SBOM via Syft), `release.yml` (disparado por tag `v*`, publica no GHCR).
- **`.gitleaks-baseline.json`** como mecanismo de aceitação de findings históricos revisados —
  não `.gitleaks.toml` (allowlist não funcionou de forma confiável na versão instalada, ver
  defeito real abaixo).

## 3. Justificativa

Cada ferramenta e comando deste sprint já era usado manualmente nos Blocos 1–3 (`ruff`, `mypy`,
`pytest --cov`, `docker build`) ou foi rodado localmente pela primeira vez neste bloco antes de
ser codificado no YAML (`pip-audit`, `semgrep`, `gitleaks`) — a automação em CI reflete comandos
comprovados, não aspiracionais. Multi-stage + não-root é o hardening padrão de produção para
containers Python: reduz a superfície de ataque (sem toolchain de build na imagem final, sem
processo rodando como root) mesmo quando a redução de tamanho de imagem é modesta (dominada
pelas dependências de ML, `torch`/`sentence-transformers`, independente da estratégia de build).

## 4. Alternativas consideradas

- **`.gitleaks.toml` com `[allowlist]`** (regex e depois fingerprint): tentado primeiro,
  rejeitado — não suprimiu o finding real (`admin:admin` num exemplo de curl neste próprio
  `PROGRESS.md`) sob gitleaks 8.21.2 combinado com `[extend] useDefault = true`. Substituído
  pelo mecanismo de baseline (`gitleaks detect --baseline-path`), que funcionou corretamente.
- **Rodar `act` localmente para verificar os workflows de ponta a ponta**: não disponível nesta
  máquina, e não instalado só para esta verificação. Os workflows são reais e YAML-válidos, com
  cada passo já comprovado manualmente — mas não verificados por um runner real. Gap documentado
  explicitamente no `PROGRESS.md`, não escondido.
- **SBOM gerado localmente como parte deste sprint**: três tentativas reais via
  `docker run anchore/syft ...` — a primeira falhou por instabilidade do Docker/WSL2 (ver
  defeito abaixo), a segunda produziu output vazio por um problema de captura ao usar `tail` em
  background, e a terceira travou o próprio container do Syft (mesma assinatura do defeito de
  PID 1 zumbi). Decisão confirmada com o usuário: documentar como gap local em vez de forçar
  outro reinício disruptivo do Windows por um artefato que não bloqueia o release — `docker.yml`
  já roda o Syft corretamente em CI, ambiente sem essa instabilidade específica de WSL2.

## 5. Consequências

### ✅ Positivas
- Toda verificação de qualidade/segurança que hoje é manual passa a ser automatizável em CI sem
  reinventar comandos.
- Imagem de produção não roda como root e não carrega toolchain de build.
- Zumbis de subprocesso órfão (como o `hf_xet` do defeito abaixo) agora são colhidos pelo
  `tini`, em vez de travarem o container inteiro.

### ⚠️ Negativas
- Workflows não verificados por um runner real (sem `act`, sem remote no GitHub) — risco residual
  de erro de sintaxe/lógica não capturado localmente, mitigado por cada passo já ter sido
  validado manualmente com o comando exato.
- Nenhum SBOM gerado localmente para esta release — depende do `docker.yml` em CI real para essa
  evidência.

## 6. Considerações de segurança

`pip-audit` (0 vulnerabilidades conhecidas), `semgrep --config auto` (290 regras, 89 arquivos,
0 findings) e `gitleaks` (0 leaks reais; 1 finding histórico revisado e aceito via baseline, com
a causa raiz corrigida no código-fonte, não apenas silenciada no scanner) rodaram de verdade
contra este repositório antes de serem codificados no `security.yml`. Imagem roda como usuário
não-root dedicado (uid 999), sem shell de build nem `uv`/`uvx` na imagem final.

### Defeitos reais encontrados e corrigidos neste sprint

1. **Segredo em exemplo de comando documentado** (`admin:admin` num curl de exemplo do Grafana
   neste `PROGRESS.md`) — corrigido na raiz: senha de admin do Grafana passou a ser configurável
   via `GRAFANA_ADMIN_PASSWORD` (com default claramente marcado como dev-only), acesso anônimo
   de Viewer já cobre o caso de uso documentado sem autenticação.
2. **`PermissionError` no primeiro `/retrieve` da imagem não-root**: `/app` continuava de
   propriedade do `root` mesmo após `COPY --chown=app:app` dos subdiretórios, então `app` não
   conseguia criar `/app/.cache` para o download do modelo de embedding. Corrigido criando e
   dando `chown` explícito em `/app/.cache` antes de `USER app`.
3. **PID 1 zumbi derrubando o container e a VM WSL2 inteira**: um subprocesso nativo (`hf_xet`,
   usado por `sentence-transformers`/`huggingface_hub` para download) foi órfão por uma falha
   transitória de DNS; sem processo `init` como PID 1, o zumbi nunca foi colhido. Consequência
   real observada: `docker kill`/`docker rm -f` travaram indefinidamente no container, e a
   própria VM WSL2 (`vmmemWSL`) ficou travada a ponto de exigir um reinício completo do Windows
   para recuperação (confirmado com o usuário antes de qualquer ação disruptiva). Corrigido na
   raiz com `init: true` no `docker-compose.yml` (roda `tini` como PID 1), verificado
   (`docker inspect ... {{.HostConfig.Init}}` → `true`) e validado com uma chamada `/retrieve`
   real de ponta a ponta pós-correção.

Ver `docs/release-gate/PROGRESS.md` (seção Bloco 4 — Sprint 12) para os comandos e outputs reais
completos.

## 7. Critérios de revisão

Revisar se `act` (ou acesso a um remote GitHub real) se tornar disponível, para verificar os
workflows por um runner de verdade em vez de apenas validação de sintaxe YAML. Revisar a decisão
de não pré-aquecer/persistir o cache de modelos (flagged como follow-up do Sprint 13) caso o
padrão de download lento sob rede instável volte a se manifestar. Revisar a instabilidade
observada do Syft/Docker Desktop nesta máquina Windows/WSL2 caso volte a ocorrer em CI real.

## 8. Status

Accepted.
