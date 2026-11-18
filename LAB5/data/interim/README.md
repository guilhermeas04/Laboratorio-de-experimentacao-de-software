# Dados intermediários

Arquivos derivados da coleta bruta, sem sobrescrever `data/raw/`.

`pilot_metrics.csv` é a tabela piloto usada pela análise descritiva (#144):
uma linha por repetição e versão, com métricas em escala razão. Valores
ausentes ficam vazios (NaN) e não são imputados como zero.
