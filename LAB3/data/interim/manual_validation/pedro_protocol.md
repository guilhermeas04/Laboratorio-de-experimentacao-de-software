# Protocolo de rotulacao — Pedro

O lote e o mesmo dos 60 repositorios da amostra-ouro, na mesma ordem. Cada linha
avalia a release primaria mais recente da janela. O id da release e a tag foram
mantidos para a consolidacao. Nao li a coluna de rotulo dos outros integrantes.

## Como rotulei

Li a tag, o titulo e os primeiros 2000 caracteres das notas. Sem release na
janela, o rotulo e `sem_release`.

- `corretiva`: o texto junta tag, titulo e notas e cita bug, bugfix, hotfix,
  crash, security fix, fix, fixed ou fixes.
- `nao_corretiva`: a release existe, mas esse texto nao cita correcao.
- `sem_release`: nao existe release primaria publicada na janela.

Versao patch sozinha nao vira corretiva. Sem a palavra de correcao nas notas,
deixo `nao_corretiva`.
Casos `sem_release` permanecem no arquivo bruto, mas sao excluidos de
precisao, recall e F1 porque nao possuem release para classificar.
