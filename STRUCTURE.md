# Estrutura do Repositório

O projeto é dividido em partes distintas. A raiz do repositório forma o código fonte e os recursos que são distribuídos pelo QGIS.
Outras pastas (como docs/ e desafio-2-port/) são exclusivamente para trabalho, referência e desenvolvimento futuro, **não sendo empacotadas** na distribuição.

## Vai no pacote publicado? (Sim)
- `core/`: Sim. Componentes essenciais do plugin geobr-qgis.
- `algorithms/`: Sim. Os algoritmos expostos no QGIS.
- `__init__.py`: Sim. Ponto de entrada do plugin.
- `geobr_qgis_plugin.py`: Sim. O wrapper do plugin e provider.
- `metadata.txt`: Sim. Os metadados para o repositório de plugins do QGIS.
- `provider.py`: Sim. O provedor QGIS que expõe os algoritmos do plugin.
- `icon.png` / `icon.svg`: Sim. Ícones do plugin.
- `LICENSE`: Sim. O texto da licença (GPL-3.0).

## Vai no pacote publicado? (Não)
As seguintes pastas e arquivos NÃO são empacotados no arquivo distribuído (excluídos via script `package.sh`):
- `docs/`: Não. Material de pesquisa, especificação, documentação interna, manuais, referências.
- `desafio-2-port/`: Não. Staging de código portado de projetos antigos, ainda não integrado (ex. do haCARthon).
- `STRUCTURE.md`: Não. Apenas orientação de organização interna do repositório.
- `ACTIONS.md`: Não. Histórico e quadros de tarefas para agentes de desenvolvimento.
- `AGENTS.md`: Não. Regras e instruções para o agente sênior.
- `INSTRUCTIONS.md`: Não. Instruções para o agente júnior.
- `CLAUDE.md`: Não. Documento de contexto do repositório para a IA.
- `Makefile`: Não. Utilitários locais (make deploy, test).
- `.gitignore`: Não. Ocultado por padrão.
- `*.pdf`, `*.md` avulsos de rascunhos.
- Pastas como `.git/`, `.claude/`, `dist/`.
