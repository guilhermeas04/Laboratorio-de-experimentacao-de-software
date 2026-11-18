# LAB05 — Experimento em software real

Estrutura inicial para o experimento final sobre um software real, em operação
e de alto impacto. O objeto de estudo, a pergunta de pesquisa e o desenho serão
definidos pelo grupo na proposta.

## Estrutura

```text
LAB5/
├── config/                 # parâmetros do estudo e da coleta
├── data/
│   ├── raw/                # dados brutos e registros originais
│   ├── interim/            # dados validados e transformados
│   └── processed/          # datasets finais para a análise
├── docs/                   # proposta, método, ética e documentação final
├── notebooks/              # exploração e análises auxiliares
├── reports/
│   ├── figures/            # visualizações e gráficos finais
│   └── tables/             # tabelas e resultados estatísticos
├── dashboard/              # dashboard ou visualização final, se aplicável
├── src/lab05_real_software/ # coleta, validação, análise e impacto
└── tests/                  # testes automatizados e validações
```

O diretório `data/raw` deve preservar os registros originais. Dados pessoais,
credenciais e informações que não possam ser compartilhadas não devem ser
versionados.

## Sprints

- `Lab05S01`: proposta, evidências do software, GQM, categorias da pesquisa,
  plano de coleta/análise e coleta piloto.
- `Lab05S02`: coleta completa, validação, análise e ameaças à validade.
- `Lab05S03`: impacto, conclusões, limitações e rascunhos do documento e da
  apresentação.
- Documento final e apresentação: formato livre, conforme o enunciado.

## Critérios do estudo

O software escolhido deve ser real, estar em operação e ter alto impacto,
sempre com evidências e fontes. A coleta deve respeitar os termos de uso,
`robots.txt`, o limite de uma requisição por segundo para medições externas e
as regras de ética descritas no enunciado.

## Piloto PostgreSQL

Prepare as imagens oficiais antes da coleta. Execute a partir da raiz do
repositório, em PowerShell.

```powershell
docker pull postgres:15.20
docker pull postgres:17.12
$env:PYTHONPATH = (Resolve-Path LAB5/src).Path
python -m lab05_real_software.postgres_pilot --blocks 2
python -m pytest -q LAB5/tests
```

Cada rodada cria um contêiner descartável sem rede, com 1 CPU e 512 MB de
memória. O roteiro carrega 100 mil pedidos sintéticos, aquece uma consulta de
soma por cliente e repete a consulta com `EXPLAIN ANALYZE`. As versões rodam
em sequência e a ordem é invertida a cada bloco.

Os JSONs ficam em `LAB5/data/raw/` por padrão. O campo `stdout` contém a
versão confirmada pelo servidor e o plano em JSON, com o tempo de execução
no servidor em `Execution Time` (ms). `duration_ms` inclui a inicialização
do cliente. Os registros com rótulo `pilot-local` correspondem à verificação
inicial do coletor. O piloto com PostgreSQL valida a instrumentação de
latência para uma consulta. Throughput, CPU e memória ficam para a próxima
etapa de instrumentação.
