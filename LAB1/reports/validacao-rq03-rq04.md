# Validacao RQ03 e RQ04

Este arquivo e gerado por `python LAB1/code/src/analyzers/rq03_rq04_metrics.py`
depois da coleta dos 1000 repositorios.

O validador confere:

- quantidade de registros (1000);
- campos ausentes (`releases_count`, `updated_at`, `pushed_at`);
- valores invalidos (contagens negativas, datas sem conversao);
- outliers pelo metodo IQR;
- concentracao de `updatedAt` no dia da coleta, comparada com `pushedAt`.

Limitacao conhecida: `updatedAt` nao mede atualizacao de codigo. A coleta desta
sprint inclui `pushedAt` para a RQ04.
