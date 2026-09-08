# Checklist técnico pré-execução dos trials

Use este checklist depois de instalar o ambiente e antes do primeiro trial real.
A verificação automática correspondente é o comando `lab02-smoke` (issue #50).

## Ambiente

1. Python 3.13.x ativo conforme `LAB2/code/.python-version`.
2. Dependências instaladas a partir de `LAB2/code/requirements-dev.txt`.
3. Pacote instalado em modo editável: `python -m pip install -e .` dentro de
   `LAB2/code`.
4. Diretórios `data/examples`, `data/raw`, `data/processed`, `data/sessions` e
   `data/demo` existem.

## Ferramentas

5. `lab02-trial` responde aos subcomandos `start`, `status` e `finish`.
6. `lab02-metrics` está disponível e o Radon importa sem erro.
7. `lab02-smoke` termina com código 0 e não grava nada em `data/raw`.

## Protocolo operacional

8. Participante, kata, tratamento e ordem do trial estão confirmados.
9. Não existe arquivo com o mesmo `trial_id` em `data/sessions/` ou `data/raw/`.
10. No tratamento com IA, nome e versão do assistente já estão definidos.
11. Testes de aceitação da kata estão preparados.
12. O código final do trial será analisado por `lab02-metrics` após o
    encerramento.

## Isolamento

13. Demonstrações e smoke tests usam apenas `data/demo/`.
14. Exemplos fictícios ficam em `data/examples/` e não entram na análise.
15. Registros reais permanecem imutáveis em `data/raw/`.
