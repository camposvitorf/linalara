import json
import os
import pandas as pd
import requests
import streamlit as st

# -----------------------------------------------------------------------------
# Configuração de Caminhos e Persistência
# -----------------------------------------------------------------------------
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))

# Localiza o arquivo products.json (na mesma pasta ou na pasta pai)
if os.path.exists(os.path.join(CURRENT_DIR, "products.json")):
    PRODUCTS_FILE = os.path.join(CURRENT_DIR, "products.json")
elif os.path.exists(os.path.join(os.path.dirname(CURRENT_DIR), "products.json")):
    PRODUCTS_FILE = os.path.join(os.path.dirname(CURRENT_DIR), "products.json")
else:
    PRODUCTS_FILE = os.path.join(CURRENT_DIR, "products.json")

# Localiza a foto lina_lara.bmp para o header (compatível com Windows e Linux / Streamlit Cloud)
HEADER_IMAGE_PATH = os.path.join(CURRENT_DIR, "lina_lara.bmp")
for img_name in ["lina_lara.bmp", "lina_lara.png", "lina_lara.jpg"]:
    candidate = os.path.join(CURRENT_DIR, img_name)
    if os.path.exists(candidate):
        HEADER_IMAGE_PATH = candidate
        break
    candidate_parent = os.path.join(os.path.dirname(CURRENT_DIR), img_name)
    if os.path.exists(candidate_parent):
        HEADER_IMAGE_PATH = candidate_parent
        break


def get_enxoval_file_path(filename: str) -> str:
    """Localiza arquivos da pasta de enxovais (final.txt, final.csv, final.json) de forma portável."""
    candidates = [
        os.path.join(CURRENT_DIR, "enxovais", filename),
        os.path.join(CURRENT_DIR, "developing-with-streamlit", "enxovais", filename),
        os.path.join(os.path.dirname(CURRENT_DIR), "enxovais", filename),
        os.path.join(os.path.dirname(CURRENT_DIR), "developing-with-streamlit", "enxovais", filename),
        os.path.join(CURRENT_DIR, filename),
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return candidate
    return candidates[0]


# -----------------------------------------------------------------------------
# Usuários e Perfis de Acesso
# user1: linalara (visualiza, vota com like/dislike, sugere produtos)
# user2: admin    (gerencia o site, controla a coluna 'tenho' em todos os itens)
# -----------------------------------------------------------------------------
USERS = {
    "linalara": {
        "password": "laralina",
        "role": "user1",
        "label": "Lina & Lara",
        "badge": "🌸 Usuário (user1)",
        "can_vote": True,
        "can_manage_tenho": False,
        "can_suggest": True,
    },
    "admin": {
        "password": "abc@123",
        "role": "user2",
        "label": "Administrador",
        "badge": "👑 Administrador (user2)",
        "can_vote": False,
        "can_manage_tenho": True,
        "can_suggest": True,
    },
}

DEFAULT_PRODUCTS = [
    {
        "title": "Carrinho de bebê para gêmeos",
        "link": "https://www.amazon.com.br/Carrinho-para-Gemeos-Doppio-Grafite/dp/B0CD4D7LWT",
        "image_url": "",
        "likes": 0,
        "dislikes": 0,
        "tenho": 0,
        "qtd_necessaria": 1,
    },
    {
        "title": "Babá eletrônica com câmera noturna",
        "link": "https://produto.mercadolivre.com.br/MLB-6892873926-baba-eletrnica-com-cmera-noturna-sensor-tela-lcd-vb603-b50-_JM",
        "image_url": "",
        "likes": 0,
        "dislikes": 0,
        "tenho": 0,
        "qtd_necessaria": 1,
    },
]


def normalize_link(url: str) -> str:
    """
    Remove parâmetros de consulta (?) e âncoras (#) da URL,
    evitando problemas de rastreamento ou links expirados.
    """
    url = url.strip()
    if not url:
        return ""
    if "?" in url:
        url = url.split("?", 1)[0]
    if "#" in url:
        url = url.split("#", 1)[0]
    return url.strip()


def get_gsheets_url() -> str:
    """Retorna a URL do Webhook do Google Apps Script configurada."""
    try:
        if "GSHEETS_URL" in st.secrets and st.secrets["GSHEETS_URL"]:
            val = str(st.secrets["GSHEETS_URL"]).strip()
            if val and "SEU_ID" not in val:
                return val
    except Exception:
        pass
    env_val = os.environ.get("GSHEETS_URL", "").strip()
    if env_val and "SEU_ID" not in env_val:
        return env_val
    return ""


def load_local_products() -> list[dict]:
    """Carrega a lista de produtos do arquivo JSON local com validação."""
    if os.path.exists(PRODUCTS_FILE):
        try:
            with open(PRODUCTS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    for item in data:
                        item.setdefault("title", "Produto sem nome")
                        item.setdefault("link", "")
                        item.setdefault("likes", 0)
                        item.setdefault("dislikes", 0)
                        item.setdefault("tenho", 0)
                        item.setdefault("qtd_necessaria", 1)
                        item.setdefault("image_url", "")
                    return data
        except (json.JSONDecodeError, OSError):
            pass
    return [dict(p) for p in DEFAULT_PRODUCTS]


def load_products() -> list[dict]:
    """
    Carrega a lista de produtos da planilha Google Sheets via Apps Script Web App.
    Se a planilha estiver vazia, faz o povoamento inicial automático com os dados locais.
    Se o Google Sheets não estiver configurado ou offline, utiliza o arquivo local.
    """
    gsheets_url = get_gsheets_url()
    if gsheets_url:
        try:
            resp = requests.get(gsheets_url, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list):
                    if len(data) > 0:
                        for item in data:
                            item.setdefault("title", "Produto sem nome")
                            item.setdefault("link", "")
                            item["likes"] = int(item.get("likes") or 0)
                            item["dislikes"] = int(item.get("dislikes") or 0)
                            item["tenho"] = int(item.get("tenho") or 0)
                            item["qtd_necessaria"] = int(item.get("qtd_necessaria") or 1)
                            item.setdefault("image_url", "")
                        # Atualiza o cache local
                        try:
                            with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
                                json.dump(data, f, ensure_ascii=False, indent=2)
                        except Exception:
                            pass
                        return data
                    else:
                        # Planilha vazia: popula com os dados iniciais locais
                        initial = load_local_products()
                        save_products(initial)
                        return initial
        except Exception:
            pass  # Recorre ao arquivo local em caso de erro

    return load_local_products()


def save_products(products: list[dict]) -> None:
    """Salva a lista de produtos no arquivo JSON local e na planilha Google Sheets."""
    # 1. Salva localmente (como cache/backup)
    try:
        with open(PRODUCTS_FILE, "w", encoding="utf-8") as f:
            json.dump(products, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

    # 2. Salva no Google Sheets via Webhook se configurado
    gsheets_url = get_gsheets_url()
    if gsheets_url:
        try:
            requests.post(gsheets_url, json=products, timeout=12)
        except Exception:
            pass


def init_session_state() -> None:
    """Inicializa as variáveis de controle de sessão."""
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "role" not in st.session_state:
        st.session_state.role = ""
    if "products" not in st.session_state:
        st.session_state.products = load_products()
    if "login_error" not in st.session_state:
        st.session_state.login_error = ""
    if "current_page" not in st.session_state:
        st.session_state.current_page = "🛍️ Produtos & Sugestões"


def handle_login(username_input: str, password_input: str) -> None:
    """Valida as credenciais para user1 (linalara) e user2 (admin)."""
    user = username_input.strip().lower()
    if user in USERS and USERS[user]["password"] == password_input.strip():
        st.session_state.logged_in = True
        st.session_state.username = user
        st.session_state.role = USERS[user]["role"]
        st.session_state.login_error = ""
    else:
        st.session_state.login_error = "Usuário ou senha incorretos. Tente novamente."


def handle_logout() -> None:
    """Desconecta o usuário atual."""
    st.session_state.logged_in = False
    st.session_state.username = ""
    st.session_state.role = ""
    st.session_state.login_error = ""
    st.session_state.current_page = "🛍️ Produtos & Sugestões"
    st.rerun()


# -----------------------------------------------------------------------------
# Interface de Login
# -----------------------------------------------------------------------------
def render_login_page() -> None:
    """Exibe a tela de login simples e acolhedora."""
    st.markdown(
        """
        <div style="text-align: center; margin-top: 1rem; margin-bottom: 1rem;">
            <h1 style="color: #d85a8a; margin-bottom: 0.2rem;">🍼 Enxoval Lina & Lara 🎀</h1>
            <p style="font-size: 1.15rem; color: #555;">Lista de Produtos & Sugestões para Meninas Gêmeas</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns([1, 1.3, 1])
    with col2:
        if os.path.exists(HEADER_IMAGE_PATH):
            st.image(HEADER_IMAGE_PATH, width="stretch")

        with st.container(border=True):
            st.subheader("🔐 Identificação de Acesso")
            with st.form("login_form", clear_on_submit=False):
                username_input = st.text_input(
                    "Usuário",
                    placeholder="Digite seu usuário (ex: linalara ou admin)",
                )
                password_input = st.text_input(
                    "Senha",
                    type="password",
                    placeholder="Digite sua senha",
                )
                submit_btn = st.form_submit_button("Entrar no App", width="stretch")

                if submit_btn:
                    handle_login(username_input, password_input)
                    if st.session_state.logged_in:
                        st.rerun()

            if st.session_state.login_error:
                st.error(st.session_state.login_error)

            st.markdown(
                """
                <div style="font-size: 0.82rem; color: #777; margin-top: 1rem; border-top: 1px dashed #ddd; padding-top: 0.5rem;">
                    💡 <b>Acessos disponíveis:</b><br>
                    • <b>user1:</b> <code>linalara</code> (vota e sugere produtos)<br>
                    • <b>user2:</b> <code>admin</code> (gerencia site e coluna 'tenho')
                </div>
                """,
                unsafe_allow_html=True,
            )


# -----------------------------------------------------------------------------
# Página 1: Produtos Sugeridos e Cadastro (Tabs)
# -----------------------------------------------------------------------------
def render_products_page(role: str, is_admin: bool) -> None:
    """Renderiza a tela principal com as duas abas de produtos sugeridos e novo produto."""
    # --- CABEÇALHO DA PÁGINA COM FOTO ---
    if os.path.exists(HEADER_IMAGE_PATH):
        col_foto, col_titulo = st.columns([1.2, 4.8], vertical_alignment="center")
        with col_foto:
            st.image(HEADER_IMAGE_PATH, width="stretch")
        with col_titulo:
            st.markdown(
                """
                <div style="padding-left: 0.5rem;">
                    <h1 style="color: #d85a8a; margin: 0; font-size: 2.1rem; font-weight: 700; line-height: 1.2;">
                        🍼 Lista de Enxoval das Gêmeas Lina & Lara
                    </h1>
                    <p style="color: #555; font-size: 1.05rem; margin-top: 0.35rem; margin-bottom: 0;">
                        Acompanhamento de compras, votações e sugestões de produtos em dose dupla! 🎀
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div style="margin-bottom: 1.5rem;">
                <h1 style="color: #d85a8a; margin-bottom: 0.2rem;">🍼 Lista de Enxoval das Gêmeas Lina & Lara</h1>
                <p style="color: #666; font-size: 1.05rem;">Acompanhamento de compras, votações e sugestões de produtos.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 1.5rem; border: none; border-top: 1px solid #f2c2d4;'>", unsafe_allow_html=True)

    # --- TABS PRINCIPAIS ---
    tab_list, tab_suggest = st.tabs(["📋 Produtos sugeridos", "➕ Sugerir novo produto"])

    # -------------------------------------------------------------------------
    # TAB 1: LISTA DE PRODUTOS SUGERIDOS
    # -------------------------------------------------------------------------
    with tab_list:
        if not st.session_state.products:
            st.info("Ainda não há produtos cadastrados. Utilize a aba 'Sugerir novo produto' para começar!")
        else:
            # Banner amigável com atalho para o Guia Completo do Enxoval
            col_b1, col_b2 = st.columns([3.8, 1.4], vertical_alignment="center")
            with col_b1:
                st.markdown("### Produtos sugeridos até agora")
            with col_b2:
                if st.button("📖 Ver Guia do Enxoval", width="stretch"):
                    st.session_state.current_page = "📖 Guia do Enxoval (final.txt & Tabela)"
                    st.rerun()

            # Barra de busca e filtros rápidos
            search_col, filter_col = st.columns([2, 1])
            with search_col:
                search_term = st.text_input(
                    "🔍 Filtrar produtos por nome:",
                    placeholder="Digite para buscar...",
                    label_visibility="collapsed",
                )
            with filter_col:
                status_filter = st.selectbox(
                    "Filtrar por status",
                    options=["Todos", "Já temos (Tenho > 0)", "Falta comprar (Tenho = 0)"],
                    label_visibility="collapsed",
                )

            # Filtragem dos produtos
            filtered_indices = []
            for idx, prod in enumerate(st.session_state.products):
                title_match = search_term.lower() in prod.get("title", "").lower()
                tenho_val = prod.get("tenho", 0)

                status_match = True
                if status_filter == "Já temos (Tenho > 0)":
                    status_match = tenho_val > 0
                elif status_filter == "Falta comprar (Tenho = 0)":
                    status_match = tenho_val == 0

                if title_match and status_match:
                    filtered_indices.append(idx)

            st.caption(f"Exibindo **{len(filtered_indices)}** de **{len(st.session_state.products)}** produtos")

            # Exibição dos cards de produtos
            for idx in filtered_indices:
                prod = st.session_state.products[idx]
                with st.container(border=True):
                    c_info, c_tenho, c_actions = st.columns([2.5, 1.4, 1.6])

                    # 1. Informações do Produto
                    with c_info:
                        st.markdown(f"#### 🛍️ {prod.get('title', 'Produto sem título')}")
                        link = prod.get("link", "").strip()
                        if link:
                            clean_display_link = link if len(link) < 55 else link[:52] + "..."
                            st.markdown(f"🔗 **Link:** [{clean_display_link}]({link})")
                        else:
                            st.caption("Sem link informado")

                        if prod.get("image_url"):
                            try:
                                st.image(prod["image_url"], width=130)
                            except Exception:
                                pass

                    # 2. Coluna "Tenho" (Gerenciada pelo user2 / admin)
                    with c_tenho:
                        st.markdown("##### 📦 Tenho")
                        tenho_atual = int(prod.get("tenho", 0))

                        if is_admin:
                            novo_tenho = st.number_input(
                                label="Quantidade que já tenho:",
                                min_value=0,
                                max_value=999,
                                value=tenho_atual,
                                step=1,
                                key=f"admin_tenho_{idx}",
                                label_visibility="collapsed",
                            )
                            if novo_tenho != tenho_atual:
                                st.session_state.products[idx]["tenho"] = novo_tenho
                                save_products(st.session_state.products)
                                st.toast(f"✅ 'Tenho' atualizado para {novo_tenho}!")
                                st.rerun()
                            st.caption("⚙️ Editável pelo admin")
                        else:
                            if tenho_atual > 0:
                                st.markdown(
                                    f"""
                                    <div style="background-color: #e8f8f0; color: #1e7e44; padding: 6px 12px; border-radius: 8px; font-weight: bold; text-align: center; border: 1px solid #b8ebcf;">
                                        ✅ Já temos: {tenho_atual} un.
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                            else:
                                st.markdown(
                                    """
                                    <div style="background-color: #fff8e6; color: #8a6300; padding: 6px 12px; border-radius: 8px; font-weight: bold; text-align: center; border: 1px solid #ffe099;">
                                        ⏳ Falta comprar (0)
                                    </div>
                                    """,
                                    unsafe_allow_html=True,
                                )
                            st.caption("Status definido pelo gestor")

                    # 3. Coluna de Votação (user1 vota com Like / Dislike) e Ações
                    with c_actions:
                        st.markdown("##### 🗳️ Avaliação")
                        likes = prod.get("likes", 0)
                        dislikes = prod.get("dislikes", 0)

                        if role == "user1":
                            col_like, col_dislike = st.columns(2)
                            with col_like:
                                if st.button(f"👍 {likes}", key=f"btn_like_{idx}", width="stretch"):
                                    st.session_state.products[idx]["likes"] += 1
                                    save_products(st.session_state.products)
                                    st.toast("Obrigado pelo seu voto positivo! 👍")
                                    st.rerun()
                            with col_dislike:
                                if st.button(f"👎 {dislikes}", key=f"btn_dislike_{idx}", width="stretch"):
                                    st.session_state.products[idx]["dislikes"] += 1
                                    save_products(st.session_state.products)
                                    st.toast("Voto registrado! 👎")
                                    st.rerun()
                            st.caption("Clique para votar")
                        else:
                            st.markdown(f"**Votos:** 👍 `{likes}` | 👎 `{dislikes}`")
                            if st.button("🗑️ Remover", key=f"btn_del_{idx}", type="secondary", width="stretch"):
                                st.session_state.products.pop(idx)
                                save_products(st.session_state.products)
                                st.toast("Item removido com sucesso.")
                                st.rerun()

    # -------------------------------------------------------------------------
    # TAB 2: SUGERIR NOVO PRODUTO
    # -------------------------------------------------------------------------
    with tab_suggest:
        st.markdown("### ➕ Sugerir um Produto para as Bebês")
        st.write(
            "Preencha os dois campos abaixo para sugerir um item para o enxoval. "
            "Ele será adicionado imediatamente à lista de produtos!"
        )

        with st.container(border=True):
            with st.form("form_sugerir_produto", clear_on_submit=True):
                nome_produto = st.text_input(
                    "1. Nome do produto *",
                    placeholder="Ex: Carrinho duplo para gêmeos, Berço portátil, Banheira com suporte...",
                )
                link_produto = st.text_input(
                    "2. Link do produto *",
                    placeholder="Ex: https://www.amazon.com.br/... ou https://produto.mercadolivre.com.br/...",
                )

                submit_sugestao = st.form_submit_button(
                    "Adicionar à lista de produtos sugeridos",
                    width="stretch",
                )

                if submit_sugestao:
                    nome_limpo = nome_produto.strip()
                    link_limpo = normalize_link(link_produto)

                    if not nome_limpo:
                        st.error("Por favor, preencha o **Nome do produto**.")
                    elif not link_limpo:
                        st.error("Por favor, informe um **Link** válido para o produto.")
                    else:
                        novo_item = {
                            "title": nome_limpo,
                            "link": link_limpo,
                            "image_url": "",
                            "likes": 0,
                            "dislikes": 0,
                            "tenho": 0,
                            "qtd_necessaria": 1,
                        }
                        st.session_state.products.append(novo_item)
                        save_products(st.session_state.products)
                        st.success(f"🎉 Produto **'{nome_limpo}'** adicionado com sucesso à lista!")
                        st.balloons()
                        st.rerun()


# -----------------------------------------------------------------------------
# Página 2: Guia de Enxoval (final.txt) e Tabela Consolidada (final.csv / final.json)
# -----------------------------------------------------------------------------
def render_enxoval_guide_page() -> None:
    """Renderiza a página com o conteúdo de final.txt e a tabela com final.csv / final.json."""
    # --- CABEÇALHO DA PÁGINA COM FOTO ---
    if os.path.exists(HEADER_IMAGE_PATH):
        col_foto, col_titulo = st.columns([1.2, 4.8], vertical_alignment="center")
        with col_foto:
            st.image(HEADER_IMAGE_PATH, width="stretch")
        with col_titulo:
            st.markdown(
                """
                <div style="padding-left: 0.5rem;">
                    <h1 style="color: #d85a8a; margin: 0; font-size: 2.1rem; font-weight: 700; line-height: 1.2;">
                        📖 Guia Consolidado de Enxoval para Gêmeas
                    </h1>
                    <p style="color: #555; font-size: 1.05rem; margin-top: 0.35rem; margin-bottom: 0;">
                        Compilado das listas de referência com diretrizes e tabela dos 79 itens planejados para Lina & Lara. 🎀
                    </p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.markdown(
            """
            <div style="margin-bottom: 1.5rem;">
                <h1 style="color: #d85a8a; margin-bottom: 0.2rem;">📖 Guia Consolidado de Enxoval para Gêmeas</h1>
                <p style="color: #666; font-size: 1.05rem;">Compilado das listas de referência e tabela com os 79 itens planejados para Lina & Lara.</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown("<hr style='margin-top: 1rem; margin-bottom: 1.5rem; border: none; border-top: 1px solid #f2c2d4;'>", unsafe_allow_html=True)

    # Barra superior com atalho e botões de download
    col_nav, col_d1, col_d2, col_d3 = st.columns([1.8, 1, 1, 1], vertical_alignment="center")
    with col_nav:
        if st.button("⬅️ Voltar para Produtos Sugeridos", width="stretch"):
            st.session_state.current_page = "🛍️ Produtos & Sugestões"
            st.rerun()

    txt_path = get_enxoval_file_path("final.txt")
    csv_path = get_enxoval_file_path("final.csv")
    json_path = get_enxoval_file_path("final.json")

    with col_d1:
        if os.path.exists(txt_path):
            with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                st.download_button(
                    label="📥 Baixar final.txt",
                    data=f.read(),
                    file_name="enxoval_gemeas_final.txt",
                    mime="text/plain",
                    width="stretch",
                )

    with col_d2:
        if os.path.exists(csv_path):
            with open(csv_path, "rb") as f:
                st.download_button(
                    label="📥 Baixar final.csv",
                    data=f.read(),
                    file_name="enxoval_gemeas_final.csv",
                    mime="text/csv",
                    width="stretch",
                )

    with col_d3:
        if os.path.exists(json_path):
            with open(json_path, "r", encoding="utf-8", errors="replace") as f:
                st.download_button(
                    label="📥 Baixar final.json",
                    data=f.read(),
                    file_name="enxoval_gemeas_final.json",
                    mime="application/json",
                    width="stretch",
                )

    # -------------------------------------------------------------------------
    # PARTE 1: CONTEÚDO DO final.txt (em expander)
    # -------------------------------------------------------------------------
    if os.path.exists(txt_path):
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            txt_content = f.read()

        with st.expander("📜 Conteúdo Completo do Guia Prático (`final.txt`)", expanded=False):
            st.caption("Texto consolidado com regras de ouro, quantidades recomendadas por fase, diretrizes pediátricas e mala da maternidade.")
            st.markdown(
                f"""
                <div style="background-color: #fff9fb; padding: 1.2rem; border-radius: 8px; border: 1px solid #ffd8e4; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; line-height: 1.6; color: #2c3e50;">
                <pre style="white-space: pre-wrap; font-family: inherit; font-size: 0.95rem; margin: 0;">{txt_content}</pre>
                </div>
                """,
                unsafe_allow_html=True,
            )
    else:
        st.warning(f"Arquivo final.txt não encontrado ({txt_path}).")

    st.markdown("---")

    # -------------------------------------------------------------------------
    # PARTE 2: TABELA DE ITENS (final.json / final.csv)
    # -------------------------------------------------------------------------
    st.markdown("### 📊 Tabela Consolidada de Itens (`final.json` / `final.csv`)")
    st.write(
        "Abaixo está a tabela interativa contendo todos os **79 itens** do compilado de enxoval para as gêmeas. "
        "Filtre por categoria ou prioridade e busque por qualquer termo."
    )

    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")

        # 1. Coluna combinada: "{Qtd total} ({Distribuição})"
        df["qtd_distribuicao"] = (
            df["quantidade_total"].astype(str) + " (" + df["por_bebe_ou_compartilhado"].astype(str) + ")"
        )

        # Cards de métricas
        m1, m2, m3, m4 = st.columns(4)
        total_itens = len(df)
        essenciais = int((df["prioridade"] == "Essencial").sum())
        total_pecas = int(df["quantidade_total"].sum())
        num_categorias = int(df["categoria"].nunique())

        m1.metric("Total de Itens", total_itens)
        m2.metric("Itens Essenciais", essenciais)
        m3.metric("Total de Peças Somadas", f"~{total_pecas} un.")
        m4.metric("Categorias", num_categorias)

        # Filtros interativos
        col_filtro1, col_filtro2, col_busca = st.columns([1.5, 1.5, 2])
        with col_filtro1:
            categorias = ["Todas as Categorias"] + sorted(df["categoria"].dropna().unique().tolist())
            cat_sel = st.selectbox("Filtrar Categoria:", categorias)

        with col_filtro2:
            prioridades = ["Todas as Prioridades"] + sorted(df["prioridade"].dropna().unique().tolist())
            prio_sel = st.selectbox("Filtrar Prioridade:", prioridades)

        with col_busca:
            termo_busca = st.text_input("🔍 Buscar na tabela:", placeholder="Ex: body, berço, banheira, zíper...")

        # Aplicar filtros
        df_filtrado = df.copy()
        if cat_sel != "Todas as Categorias":
            df_filtrado = df_filtrado[df_filtrado["categoria"] == cat_sel]
        if prio_sel != "Todas as Prioridades":
            df_filtrado = df_filtrado[df_filtrado["prioridade"] == prio_sel]
        if termo_busca:
            t = termo_busca.lower().strip()
            mask = (
                df_filtrado["item"].astype(str).str.lower().str.contains(t, na=False) |
                df_filtrado["especificacao"].astype(str).str.lower().str.contains(t, na=False) |
                df_filtrado["categoria"].astype(str).str.lower().str.contains(t, na=False) |
                df_filtrado["dica_pratica"].astype(str).str.lower().str.contains(t, na=False) |
                df_filtrado["qtd_distribuicao"].astype(str).str.lower().str.contains(t, na=False)
            )
            df_filtrado = df_filtrado[mask]

        st.caption(f"Exibindo **{len(df_filtrado)}** de **{len(df)}** itens.")

        # Legenda visual de cores para prioridades
        st.markdown(
            """
            <div style="display: flex; gap: 1.5rem; flex-wrap: wrap; margin-bottom: 0.8rem; align-items: center; background: #fff5f8; padding: 10px 16px; border-radius: 8px; border: 1px solid #ffd6e4;">
                <span style="font-weight: 700; color: #495057; font-size: 0.95rem;">🏷️ Legenda de Cores (Prioridades):</span>
                <span style="color: #c92a2a; font-weight: 700; font-size: 0.95rem;">● Essencial</span>
                <span style="color: #d97706; font-weight: 700; font-size: 0.95rem;">● Alta</span>
                <span style="color: #1971c2; font-weight: 700; font-size: 0.95rem;">● Média</span>
                <span style="color: #2f9e44; font-weight: 700; font-size: 0.95rem;">● Baixa</span>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Mapeamento e aplicação de cores de prioridade no texto
        priority_colors = {
            "Essencial": "#c92a2a",  # Vermelho
            "Alta": "#d97706",       # Âmbar / Laranja
            "Média": "#1971c2",      # Azul
            "Media": "#1971c2",
            "Baixa": "#2f9e44",      # Verde
        }

        def style_priority(row):
            prio = str(row.get("prioridade", "")).strip()
            color = priority_colors.get(prio, "#212529")
            return [f"color: {color}; font-weight: 500;" for _ in row]

        styler = df_filtrado.style.apply(style_priority, axis=1)

        # Colunas visíveis: sem 'tamanho_fase' (fase), sem 'prioridade' e sem 'unidade'
        visible_cols = ["categoria", "item", "especificacao", "qtd_distribuicao", "dica_pratica"]

        # Exibição com st.data_editor e height='content' para quebra de linha
        st.data_editor(
            styler,
            column_order=visible_cols,
            column_config={
                "categoria": st.column_config.TextColumn("Categoria", width="medium"),
                "item": st.column_config.TextColumn("Item", width="large"),
                "especificacao": st.column_config.TextColumn("Especificação", width="large"),
                "qtd_distribuicao": st.column_config.TextColumn("Qtd Total (Distribuição)", width="medium"),
                "dica_pratica": st.column_config.TextColumn("Dica Prática", width="large"),
            },
            hide_index=True,
            disabled=True,
            height="content",
            width="stretch",
        )
    elif os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        df = pd.DataFrame(data)
        df["qtd_distribuicao"] = (
            df["quantidade_total"].astype(str) + " (" + df["por_bebe_ou_compartilhado"].astype(str) + ")"
        )
        priority_colors = {
            "Essencial": "#c92a2a",
            "Alta": "#d97706",
            "Média": "#1971c2",
            "Media": "#1971c2",
            "Baixa": "#2f9e44",
        }
        styler = df.style.apply(
            lambda row: [f"color: {priority_colors.get(str(row.get('prioridade', '')).strip(), '#212529')}; font-weight: 500;" for _ in row],
            axis=1,
        )
        visible_cols = ["categoria", "item", "especificacao", "qtd_distribuicao", "dica_pratica"]
        st.data_editor(
            styler,
            column_order=visible_cols,
            column_config={
                "categoria": st.column_config.TextColumn("Categoria", width="medium"),
                "item": st.column_config.TextColumn("Item", width="large"),
                "especificacao": st.column_config.TextColumn("Especificação", width="large"),
                "qtd_distribuicao": st.column_config.TextColumn("Qtd Total (Distribuição)", width="medium"),
                "dica_pratica": st.column_config.TextColumn("Dica Prática", width="large"),
            },
            hide_index=True,
            disabled=True,
            height="content",
            width="stretch",
        )
    else:
        st.warning("Não foi possível carregar final.csv ou final.json.")


# -----------------------------------------------------------------------------
# Ponto Central da Aplicação Logada
# -----------------------------------------------------------------------------
def render_main_page() -> None:
    """Renderiza a aplicação principal após a autenticação."""
    current_user_key = st.session_state.username
    user_info = USERS.get(current_user_key, {})
    role = st.session_state.role  # 'user1' ou 'user2'
    is_admin = role == "user2"

    # --- BARRA LATERAL (SIDEBAR) ---
    with st.sidebar:
        if os.path.exists(HEADER_IMAGE_PATH):
            st.image(HEADER_IMAGE_PATH, width="stretch")
            st.markdown("<br>", unsafe_allow_html=True)

        st.markdown(f"### {user_info.get('badge', '👤 Usuário')}")
        st.markdown(f"**Olá, {user_info.get('label', current_user_key)}!**")

        if is_admin:
            st.info("🛠️ **Modo Administrador:** Você pode gerenciar as quantidades da coluna **'Tenho'** e moderar os produtos.")
        else:
            st.success("💖 **Modo Usuário:** Você pode visualizar os itens, votar com **Like/Dislike** e sugerir novidades!")

        st.markdown("---")
        st.markdown("### 🧭 Navegação")
        page_options = [
            "🛍️ Produtos & Sugestões",
            "📖 Guia do Enxoval (final.txt & Tabela)",
        ]
        if st.session_state.current_page not in page_options:
            st.session_state.current_page = page_options[0]

        selected_page = st.radio(
            "Selecione a página:",
            page_options,
            index=page_options.index(st.session_state.current_page),
            key="sidebar_page_selector",
        )
        if selected_page != st.session_state.current_page:
            st.session_state.current_page = selected_page
            st.rerun()

        st.markdown("---")
        total_prods = len(st.session_state.products)
        itens_comprados = sum(1 for p in st.session_state.products if p.get("tenho", 0) > 0)
        total_likes = sum(p.get("likes", 0) for p in st.session_state.products)

        col_m1, col_m2 = st.columns(2)
        col_m1.metric("Produtos", total_prods)
        col_m2.metric("Já Temos", itens_comprados)
        st.metric("Total de Likes", total_likes)

        st.markdown("---")
        # Status da conexão com Google Sheets
        if get_gsheets_url():
            st.caption("🟢 **Banco de Dados:** Conectado à Google Sheet")
        else:
            st.caption("📁 **Banco de Dados:** Arquivo Local (`products.json`)")

        if st.button("🔄 Sincronizar Produtos", width="stretch", help="Recarrega a lista mais recente do Google Sheets"):
            st.session_state.products = load_products()
            st.toast("Lista de produtos sincronizada!")
            st.rerun()

        st.markdown("---")
        if st.button("🚪 Sair do Sistema (Logout)", width="stretch"):
            handle_logout()

    # --- RENDERIZAÇÃO DA PÁGINA ESCOLHIDA ---
    if st.session_state.current_page == "📖 Guia do Enxoval (final.txt & Tabela)":
        render_enxoval_guide_page()
    else:
        render_products_page(role, is_admin)


# -----------------------------------------------------------------------------
# Ponto de Entrada da Aplicação
# -----------------------------------------------------------------------------
def main() -> None:
    st.set_page_config(
        page_title="Enxoval Lina & Lara",
        page_icon="🍼",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    init_session_state()

    if not st.session_state.logged_in:
        render_login_page()
    else:
        render_main_page()


if __name__ == "__main__":
    main()
