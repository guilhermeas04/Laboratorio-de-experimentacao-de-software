# Protocolo de rotulação — Guilherme

A amostra contém 60 repositórios escolhidos deterministicamente pela ordem
alfabética entre os candidatos que possuem GitHub Actions. Para cada repositório
foi rotulada a release primária mais recente; quando não havia release primária
na janela, o caso recebeu `sem_release` e não entra na avaliação da heurística.

## Rótulos

- `corretiva`: a identificação da release contém `fix`, `hotfix`, `bug`,
  `security`, `revert` ou `patch`.
- `nao_corretiva`: não há indicador textual explícito de correção.
- `sem_release`: não existe release primária publicada na janela.

O arquivo foi produzido sem ler rótulos de outros avaliadores. A heurística é
registrada junto ao rótulo para permitir auditoria e comparação posterior.
Casos `sem_release` permanecem no arquivo bruto, mas são excluídos de precisão,
recall e F1; não existe release para a heurística classificar.
