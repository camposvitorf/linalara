# 🍼 Enxoval das Gêmeas Lina & Lara

Aplicação web desenvolvida em **Python + Streamlit** para organização, sugestão, votação e planejamento do enxoval completo de gêmeas.

Integrado com **Google Sheets** para persistência online em tempo real (qualquer produto adicionado ou voto registrado é salvo diretamente na planilha do Google Drive).

---

## ✨ Funcionalidades Principais

1. **🛍️ Painel de Produtos & Sugestões**:
   - Catálogo de itens sugeridos com foto, link da loja, contador de curtidas (`like` / `dislike`) e indicador de status ("Já Tenho").
   - Formulário para sugerir novos produtos com validação e limpeza automática de links.
   - Painel exclusivo para o administrador marcar itens já adquiridos.
   - **Persistência em Nuvem (Google Sheets)**: os dados nunca se perdem quando o servidor hiberna ou reinicia!

2. **📖 Guia Consolidado do Enxoval**:
   - Conteúdo completo do Guia Prático (`final.txt`) organizado em expander.
   - Tabela consolidada com **79 itens** compilados de listas de referência (`final.csv` / `final.json`).
   - Linhas com texto colorido por prioridade (🔴 Essencial, 🟠 Alta, 🔵 Média, 🟢 Baixa).
   - Coluna de quantidade unificada: `{Qtd total} ({Distribuição})`.
   - Filtros instantâneos por categoria, prioridade e busca textual livre.
   - Botões de download para os arquivos `.txt`, `.csv` e `.json`.

---

## 👥 Perfis de Acesso

| Usuário | Senha | Perfil | Permissões |
|---|---|---|---|
| `linalara` | `laralina` | 🌸 Lina & Lara (user1) | Visualizar produtos, votar (`like`/`dislike`) e sugerir novos itens. |
| `admin` | `abc@123` | 👑 Administrador (user2) | Gerenciar itens adquiridos ("Já Tenho"), sugerir produtos e supervisionar o catálogo. |

---

## 📁 Estrutura de Pastas Deste Repositório

```text
├── .streamlit/
│   ├── config.toml                # Tema visual suave (paleta rosa/cinza) e servidor
│   └── secrets.toml.example       # Modelo de configuração para conectar a Google Sheet
├── enxovais/
│   ├── final.csv                  # Tabela com os 79 itens planejados (UTF-8-SIG)
│   ├── final.json                 # Base de itens em formato JSON
│   └── final.txt                  # Texto do guia de enxoval compilado
├── .gitignore                     # Arquivos e diretórios ignorados pelo Git
├── README.md                      # Este manual de instruções
├── app.py                         # Aplicação Streamlit principal
├── google_apps_script.js          # Código para colar no Apps Script da sua Google Sheet
├── lina_lara.bmp                  # Foto de cabeçalho
├── products.json                  # Cópia/cache inicial de produtos
├── products.csv                   # Versão CSV dos produtos para importar se desejar
└── requirements.txt               # Dependências Python para execução automática
```

---

## 📊 Como Conectar a Planilha Google Sheets (Passo a Passo)

A planilha do projeto é:
`https://docs.google.com/spreadsheets/d/1J2O0GmpNjt91Dhl70HQtobWlh0KrAOXjHLekxX6_Njw/edit`

Para que o site consiga ler e gravar na planilha sem precisar de contas complexas no Google Cloud:

1. Abra a sua planilha no navegador.
2. No menu superior, clique em **Extensões** > **Apps Script**.
3. Apague qualquer código existente no editor e cole o conteúdo do arquivo [`google_apps_script.js`](./google_apps_script.js).
4. Clique no ícone de disquete (**Salvar** ou `Ctrl+S`).
5. Clique no botão azul **Implantar** (Deploy) > **Nova implantação** (New deployment).
6. Na engrenagem ao lado de "Selecione o tipo", escolha **App da Web** (Web app).
7. Configure:
   - **Descrição**: `API Enxoval Lina e Lara`
   - **Executar como**: `Eu (seu_email@gmail.com)`
   - **Quem tem acesso**: `Qualquer pessoa` (Anyone)
8. Clique em **Implantar**. 
   *(Se o Google exibir um aviso de autorização, clique em "Avançado" e depois em "Acessar... (não seguro)" para autorizar sua própria conta a gravar na sua planilha).*
9. Copie a **URL do App da Web** gerada (ela termina com `/exec`).
10. Adicione essa URL no Streamlit:
    - **No Streamlit Cloud**: vá no painel do seu app > **Settings** > **Secrets** e cole:
      ```toml
      GSHEETS_URL = "https://script.google.com/macros/s/SEU_ID_DO_SCRIPT/exec"
      ```
    - **Localmente**: copie `.streamlit/secrets.toml.example` para `.streamlit/secrets.toml` e cole sua URL lá.

> **Dica**: No primeiro acesso após conectar, se a planilha estiver vazia, o app automaticamente cria o cabeçalho e insere os produtos iniciais!

---

## 🚀 Como Rodar Localmente

1. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Execute o Streamlit**:
   ```bash
   streamlit run app.py
   ```

3. O navegador abrirá automaticamente em `http://localhost:8501`.

---

## 🌐 Como Publicar no GitHub e no Streamlit Cloud

### Passo 1: Subir os arquivos para o GitHub
```bash
cd D:\Py\baiaGerencial\babies\github
git init
git add .
git commit -m "Primeira versao do enxoval das gemeas com Google Sheets"
git branch -M main
git remote add origin https://github.com/SEU_USUARIO_GITHUB/NOME_DO_REPOSITORIO.git
git push -u origin main
```

### Passo 2: Fazer o Deploy no Streamlit Cloud
1. Acesse [share.streamlit.io](https://share.streamlit.io/) e faça login com seu GitHub.
2. Clique em **"New app"** (ou "Create app").
3. Selecione seu repositório, branch `main`, e `app.py`.
4. Em **Advanced settings** (ou após o deploy em Settings > Secrets), adicione a variável `GSHEETS_URL` obtida no passo do Google Sheets.
5. Clique em **"Deploy"**. Em cerca de 1 a 2 minutos o site estará online!
