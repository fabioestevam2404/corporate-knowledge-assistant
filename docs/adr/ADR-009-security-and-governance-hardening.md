# ADR-009 — Security and Governance Hardening

`Status: Accepted` · `Data: 2026-08-25` · `Projeto: Corporate Knowledge Assistant`

## 1. Contexto

Até o Bloco 2, todo o pipeline de RAG operava sob um `AccessScope` placeholder
("todas as fontes aprovadas") — não havia autenticação real, nem controle de acesso por
papel, nem por classificação documental. Isso deixava o sistema incapaz de responder à
pergunta central de segurança de um assistente de conhecimento corporativo: *este usuário
pode ver este documento?*

## 2. Decisão

Adotar defesa em profundidade: autenticação JWT, RBAC (papéis + permissões), controle de
acesso documental (ACL) por `access_level`, least privilege, validação de entrada, proteção
contra prompt injection, validação de saída, rate limiting, gestão de segredos, e uma suíte
de testes de segurança real (`tests/security/`) — não apenas documentação de intenção.

### Autenticação
JWT (`HS256`), claims `sub`/`role`/`iat`/`exp`, `ACCESS_TOKEN_EXPIRE_MINUTES=30`. Senhas
com Argon2id (`argon2-cffi`), nunca texto plano nem hash mais fraco. `AuthenticateUser`
normaliza o tempo de resposta entre "usuário inexistente" e "senha incorreta" (verificação
contra um hash-dummy real quando o usuário não existe), para não vazar quais usernames
existem via *timing side-channel* — um detalhe frequentemente esquecido em implementações
ingênuas de login.

### RBAC + ACL — dois mecanismos distintos, nunca confundidos
`ROLE_PERMISSIONS` controla o que um papel pode *fazer* (`documents:write`,
`documents:delete`, etc. — gate em `/documents`). `ACCESS_LEVELS_BY_ROLE` (a Access Matrix)
controla quais fontes documentais um papel pode *ver*, mapeado para `Source.access_level`
(`public`/`internal`/`management`). `build_access_scope_for_user` combina ambos para
construir o `AccessScope` real usado por `/ask` e `/retrieve` — a autorização acontece
**antes** da busca vetorial/lexical, nunca como filtro posterior.

### Rate limiting
Sliding-window em memória, por `user_id` (não por IP — usuários corporativos costumam
compartilhar NAT), `60 req/min` por padrão. Redis foi explicitamente descartado para o MVP
(ver ADR-002); a limitação — não sobrevive a múltiplas instâncias — está documentada, não
escondida.

### Prompt injection
Já mitigado estruturalmente desde o Bloco 2 (isolamento `<UNTRUSTED_DOCUMENTS>` /
`<USER_QUERY>`, regras explícitas no system prompt). Este bloco adiciona a prova real: um
documento adversarial de teste (`SRC-SAMPLE-005`) é ingerido de verdade, recuperado de
verdade, e o teste confirma que o payload de injeção nunca chega ao system prompt — apenas
ao bloco de dados não confiáveis.

### Segredos
`.env` nunca commitado (`.gitignore`), nunca copiado para a imagem Docker (`Dockerfile` +
`.dockerignore`, ambos testados). `JWT_SECRET_KEY` tem um default explícito de
desenvolvimento que **falha o startup em produção** (`Settings` valida
`environment == "production"` e recusa tanto o secret padrão quanto um secret curto demais).

## 3. Justificativa

RBAC sozinho é insuficiente — "papel = permissão para agir" não é o mesmo que "papel =
permissão para ver este documento específico". Confundir os dois é um padrão de vulnerabilidade
comum. Manter os dois mecanismos separados, e explicitamente unidos apenas em
`build_access_scope_for_user`, torna a regra de negócio auditável em um único lugar.

## 4. Alternativas consideradas

- **Sessões server-side em vez de JWT**: rejeitado — adiciona estado compartilhado
  desnecessário para o escopo atual (single-instance).
- **bcrypt em vez de Argon2id**: rejeitado — o roadmap especifica Argon2id explicitamente;
  também é a recomendação atual do OWASP para novos sistemas.
- **Redis para rate limiting**: adiado (ver ADR-002) — complexidade operacional desnecessária
  no MVP; documentado como limitação conhecida, não ignorado silenciosamente.
- **Bloquear palavras-chave suspeitas ("ignore", "system") na entrada**: rejeitado
  explicitamente — gera falsos positivos e falsa sensação de segurança; a defesa real é
  isolamento estrutural do conteúdo não confiável, não filtro de palavras.

## 5. Consequências

### ✅ Positivas
- O teste de autorização mais importante da apresentação (EMPLOYEE não pode ver documento
  MANAGEMENT) agora roda de verdade, contra corpus real, embeddings reais e reranking real.
- Vazamento de timing em login corrigido antes de virar um achado de pentest.

### ⚠️ Negativas
- Rate limiting em memória não sobrevive a múltiplas instâncias — aceito para o MVP,
  documentado para revisão futura.
- Sem endpoint de auditoria persistente (`GET /audit`) neste bloco — eventos de segurança
  ficam em logs estruturados, não em uma tabela dedicada (ver nota de escopo no
  `docs/release-gate/PROGRESS.md` do Bloco 3).

## 6. Considerações de segurança

Este ADR *é* sobre segurança — considerações adicionais estão embutidas nas seções acima,
não separadas.

## 7. Critérios de revisão

Revisar se: (a) o sistema precisar rodar em múltiplas instâncias (rate limiting precisaria de
um store compartilhado); (b) surgir necessidade real de trilha de auditoria persistente e
consultável via API.

## 8. Status

Accepted.
