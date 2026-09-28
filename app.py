import base64
import json
import os
import zlib
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

# -----------------------------------------------------------------------------
# Base de Dados do Guia de Enxoval (Fallback Embutido de Alta Disponibilidade)
# -----------------------------------------------------------------------------
# Dados do Guia de Enxoval e dos 79 itens comprimidos como fallback de segurança
EMBEDDED_TXT_B64 = "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"
EMBEDDED_JSON_B64 = "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"


def get_embedded_final_txt() -> str:
    """Retorna o texto de final.txt a partir dos dados comprimidos embutidos."""
    try:
        return zlib.decompress(base64.b64decode(EMBEDDED_TXT_B64)).decode("utf-8")
    except Exception:
        return "Guia Consolidado de Enxoval das Gêmeas Lina & Lara."


def get_embedded_enxoval_df() -> pd.DataFrame:
    """Retorna o DataFrame dos 79 itens a partir dos dados comprimidos embutidos."""
    try:
        raw_json = zlib.decompress(base64.b64decode(EMBEDDED_JSON_B64)).decode("utf-8")
        return pd.DataFrame(json.loads(raw_json))
    except Exception:
        return pd.DataFrame()


def load_enxoval_guide_text() -> str:
    """Carrega o texto do guia (final.txt) de disco ou usa o fallback embutido."""
    txt_path = get_enxoval_file_path("final.txt")
    if txt_path and os.path.exists(txt_path):
        try:
            with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
                return f.read()
        except Exception:
            pass

    for root, dirs, files in os.walk(CURRENT_DIR):
        if "final.txt" in files:
            try:
                with open(os.path.join(root, "final.txt"), "r", encoding="utf-8", errors="replace") as f:
                    return f.read()
            except Exception:
                pass

    return get_embedded_final_txt()


def load_enxoval_dataframe() -> pd.DataFrame:
    """Carrega o DataFrame dos 79 itens de disco ou usa o fallback embutido."""
    csv_path = get_enxoval_file_path("final.csv")
    if csv_path and os.path.exists(csv_path):
        try:
            return pd.read_csv(csv_path, sep=";", encoding="utf-8-sig")
        except Exception:
            pass

    json_path = get_enxoval_file_path("final.json")
    if json_path and os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return pd.DataFrame(json.load(f))
        except Exception:
            pass

    for root, dirs, files in os.walk(CURRENT_DIR):
        if "final.csv" in files:
            try:
                return pd.read_csv(os.path.join(root, "final.csv"), sep=";", encoding="utf-8-sig")
            except Exception:
                pass
        if "final.json" in files:
            try:
                with open(os.path.join(root, "final.json"), "r", encoding="utf-8") as f:
                    return pd.DataFrame(json.load(f))
            except Exception:
                pass

    return get_embedded_enxoval_df()


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

    # Carrega dados com fallback seguro (embutido ou disco)
    txt_content = load_enxoval_guide_text()
    df = load_enxoval_dataframe()

    # Barra superior com atalho e botões de download
    col_nav, col_d1, col_d2, col_d3 = st.columns([1.8, 1, 1, 1], vertical_alignment="center")
    with col_nav:
        if st.button("⬅️ Voltar para Produtos Sugeridos", width="stretch"):
            st.session_state.current_page = "🛍️ Produtos & Sugestões"
            st.rerun()

    with col_d1:
        st.download_button(
            label="📥 Baixar final.txt",
            data=txt_content,
            file_name="enxoval_gemeas_final.txt",
            mime="text/plain",
            width="stretch",
        )

    with col_d2:
        st.download_button(
            label="📥 Baixar final.csv",
            data=df.to_csv(sep=";", index=False, encoding="utf-8-sig") if not df.empty else "",
            file_name="enxoval_gemeas_final.csv",
            mime="text/csv",
            width="stretch",
        )

    with col_d3:
        st.download_button(
            label="📥 Baixar final.json",
            data=df.to_json(orient="records", force_ascii=False, indent=2) if not df.empty else "[]",
            file_name="enxoval_gemeas_final.json",
            mime="application/json",
            width="stretch",
        )

    # -------------------------------------------------------------------------
    # PARTE 1: CONTEÚDO DO final.txt (em expander)
    # -------------------------------------------------------------------------
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

    st.markdown("---")

    # -------------------------------------------------------------------------
    # PARTE 2: TABELA DE ITENS (final.json / final.csv)
    # -------------------------------------------------------------------------
    st.markdown("### 📊 Tabela Consolidada de Itens (`final.json` / `final.csv`)")
    st.write(
        "Abaixo está a tabela interativa contendo todos os **79 itens** do compilado de enxoval para as gêmeas. "
        "Filtre por categoria ou prioridade e busque por qualquer termo."
    )

    if not df.empty:
        # Coluna combinada: "{Qtd total} ({Distribuição})"
        if "qtd_distribuicao" not in df.columns and "quantidade_total" in df.columns:
            dist_col = df["por_bebe_ou_compartilhado"] if "por_bebe_ou_compartilhado" in df.columns else ""
            df["qtd_distribuicao"] = (
                df["quantidade_total"].astype(str) + " (" + dist_col.astype(str) + ")"
            )

        # Cards de métricas
        m1, m2, m3, m4 = st.columns(4)
        total_itens = len(df)
        essenciais = int((df["prioridade"] == "Essencial").sum()) if "prioridade" in df.columns else 0
        total_pecas = int(pd.to_numeric(df["quantidade_total"], errors="coerce").fillna(0).sum()) if "quantidade_total" in df.columns else 0
        num_categorias = int(df["categoria"].nunique()) if "categoria" in df.columns else 0

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
    else:
        st.warning("Não foi possível carregar a tabela consolidada de itens.")


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
