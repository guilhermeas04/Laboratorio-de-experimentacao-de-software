# Dicionário inicial de dados — LAB05S01

Este dicionário define o contrato dos registros brutos produzidos pelo coletor piloto. Arquivos em `LAB5/data/raw/` são registros originais e não são modificados pelo validador.

## Identificação e rastreabilidade

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `identifier` | string | derivado/validado | Identificador estável do registro. Quando ausente no JSON, deriva do nome do arquivo bruto. |
| `source` | string | derivado/validado | Origem da medição. O coletor local registra `local`; fontes externas exigiriam autorização explícita. |
| `schema_version` | string | sim | Versão do formato bruto. Nesta etapa: `lab05-pilot-v1`. |
| `collected_at` | timestamp ISO-8601 | sim | Início da execução, incluindo fuso horário. |
| `ended_at` | timestamp ISO-8601 | não | Término da execução, incluindo fuso horário e posterior ou igual ao início. |

## Propriedades do software

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `software` | string | sim | Nome do software observado, por exemplo `PostgreSQL`. |
| `software_version` | string | sim | Versão do software ou rótulo controlado da execução. |
| `configuration` | objeto | derivado/validado | Configuração usada na medição. Inclui modo de execução e timeout; preserva o objeto fornecido pelo registro quando existente. |
| `metadata` | objeto | sim | Metadados técnicos da execução. |
| `metadata.execution_mode` | string | sim | Modo de execução; no piloto, `local`. |
| `metadata.platform` | string | sim | Plataforma do sistema operacional. |
| `metadata.python_version` | string | sim | Versão do Python usada pelo coletor. |
| `metadata.hostname` | string | não | Nome local da máquina. Não deve conter identificadores pessoais externos. |
| `metadata.cwd` | string | não | Diretório local da execução. |

## Execução

| Campo | Tipo | Obrigatório | Descrição |
|---|---|---:|---|
| `repetition` | inteiro positivo | sim | Número da repetição dentro da execução piloto. |
| `command` | lista de strings | sim | Comando local executado, sem dados secretos. |
| `status` | enum | sim | `success` ou `error`. |
| `returncode` | inteiro | condicional | Obrigatório como inteiro em todos os registros; deve ser `0` em sucesso. |
| `error` | string | condicional | Obrigatório e não vazio em registros com `status=error`. |
| `duration_ms` | número | não | Duração observada em milissegundos. |
| `stdout` | string | não | Saída padrão capturada, limitada pelo coletor. |
| `stderr` | string | não | Saída de erro capturada. |

## Regras de validação

- JSON deve ter objeto como raiz.
- Campos obrigatórios devem existir e não podem ser nulos.
- Timestamps devem estar em ISO-8601 e incluir fuso horário.
- `ended_at`, quando presente, não pode preceder `collected_at`.
- Repetição deve ser inteiro positivo.
- Comando deve ser lista não vazia de strings não vazias.
- Sucesso exige `returncode=0`; erro exige mensagem não vazia.
- Identificador, fonte, timestamp, versão e configuração devem permanecer registrados no resultado validado.
- O validador apenas lê arquivos; ele não escreve em nem modifica `LAB5/data/raw/`.
