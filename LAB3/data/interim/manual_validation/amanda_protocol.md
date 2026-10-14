# Protocolo de rotulacao — Amanda

O lote possui 60 repositorios. Foram preservados o repositorio, o id da release,
a tag e a data da release. Linhas sem release publicada receberam `sem_release`.
Os rotulos dos demais avaliadores nao foram usados.

## Procedimento

Para cada release, foram consultados o titulo, o corpo da release, os links de
release notes indicados pelo proprio GitHub e, quando disponivel, o changelog.

- `corretiva`: as notas ou o changelog indicam correcao de bug, erro, falha,
  regressao, crash, vulnerabilidade ou seguranca.
- `nao_corretiva`: existe release e as notas consultadas nao indicam correcao
  de defeito.
- `incerta`: existe release, mas nao ha titulo, notas ou changelog suficiente.
- `sem_release`: nao existe release primaria publicada na janela.

A versao final deve ser revisada manualmente nas paginas das releases antes da
consolidacao da concordancia.
