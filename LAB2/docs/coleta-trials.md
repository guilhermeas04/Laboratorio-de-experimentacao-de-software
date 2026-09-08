# Protocolo de cronometragem e coleta

Este documento padroniza o uso da CLI implementada na issue #48. O protocolo
experimental da issue #52 pode acrescentar regras, mas não deve contrariar os
invariantes técnicos descritos aqui.

## Antes de iniciar

1. Confirme participante, kata, tratamento e posição do trial na ordem
   contrabalanceada.
2. Confirme que não existe arquivo com o mesmo `trial_id` em `data/sessions/`
   ou `data/raw/`.
3. No tratamento com IA, registre o nome e a versão descritos no protocolo.
4. Prepare os testes de aceitação, mas não apresente antecipadamente uma
   solução ao participante.

O `trial_id` aceita letras, números, ponto, hífen e sublinhado, com no máximo
100 caracteres. A convenção recomendada é `P01-K01-AI` ou `P01-K01-MANUAL`.

## Início

Execute `lab02-trial start` imediatamente antes de liberar o enunciado. O
horário é armazenado em ISO 8601 com fuso, e uma segunda inicialização com o
mesmo identificador é recusada.

O relógio usa UTC internamente. Isso não altera a duração e evita ambiguidade
entre computadores configurados com fusos diferentes.

## Durante o trial

`lab02-trial status --trial-id <id>` mostra:

- segundos decorridos, limitados visualmente a 2.100;
- segundos restantes;
- indicação de que o time-box foi atingido.

A consulta não pausa nem altera o cronômetro.

## Encerramento

Execute `lab02-trial finish` em uma destas condições:

- todos os testes passaram antes ou exatamente no limite; ou
- o time-box foi atingido e ainda existem testes falhando.

Para sucesso, a duração observada é registrada também como `time-to-green`.
Para falha no limite, a duração é fixada em 2.100 segundos, o trial recebe
`censored = true` e `time_to_green_seconds = null`.

A CLI recusa:

- encerrar uma implementação incompleta antes dos 35 minutos;
- alegar sucesso depois dos 35 minutos;
- contagens negativas ou mais testes passando que o total;
- informar assistente no tratamento manual;
- omitir nome ou versão do assistente no tratamento com IA;
- sobrescrever um resultado já produzido.

Se houver erro operacional, preserve os arquivos e registre a ocorrência antes
de qualquer correção. Não edite manualmente um arquivo em `data/raw/` para
transformar falha em sucesso.

## Arquivos

- `data/sessions/<trial-id>.json`: metadados transitórios de início;
- `data/raw/<trial-id>.json`: registro final imutável usado nas análises;
- `data/examples/`: exemplos fictícios, excluídos das análises.

Os arquivos de sessão não são versionados. Os registros finais deverão ser
versionados conforme a política de rastreabilidade definida para a Sprint 2.
