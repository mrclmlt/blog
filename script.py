import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime
from bs4 import BeautifulSoup
from markdownify import markdownify as md


def format_date(pub_date_str):
    """
    Converte a data do formato RSS para o formato exigido pelo Jekyll.
    """
    try:
        if "," in pub_date_str:
            pub_date_str = pub_date_str.split(",")[1].strip()
        dt = datetime.strptime(pub_date_str, "%d %b %Y %H:%M:%S %z")
        return dt.strftime("%Y-%m-%d %H:%M:%S %z"), dt
    except Exception as e:
        print(f"Erro ao formatar data '{pub_date_str}': {e}")
        # Retorna a string original e a data atual como fallback para não quebrar a ordenação
        return pub_date_str, datetime.now()


def extract_and_treat_image(soup):
    """
    Busca a primeira tag <img> dentro do HTML processado pelo BeautifulSoup.
    """
    base_domain = "https://mrclmlt.com.br"
    fallback_image = "https://mrclmlt.com.br/capa.jpg"

    img_tag = soup.find("img")

    if img_tag and img_tag.get("src"):
        src = img_tag["src"].strip()
        if src.startswith("http://") or src.startswith("https://"):
            return src
        else:
            if src.startswith("/"):
                return f"{base_domain}{src}"
            else:
                return f"{base_domain}/{src}"

    return fallback_image


def clean_html_body(soup):
    """
    Remove o primeiro parágrafo se ele for o link de retorno.
    """
    first_p = soup.find("p")
    if first_p:
        a_tag = first_p.find("a")
        if (
            a_tag
            and a_tag.get("href") == "/"
            and a_tag.get_text().strip() == "Voltar para o início"
        ):
            first_p.decompose()


def process_xml_to_md(xml_path):
    """
    Lê o arquivo XML, processa os blocos <item>, salva os arquivos .md na pasta 'mds'
    e gera uma lista indexada (index.md) ordenada por data decrescente.
    """
    output_dir = os.path.join(os.path.dirname(__file__), "mds")
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
    except Exception as e:
        print(f"Erro ao ler o arquivo XML: {e}")
        return

    items = root.findall(".//item")
    print(f"Total de itens encontrados para processamento: {len(items)}")

    # Lista para guardar os dados necessários para gerar o índice depois
    post_list_for_index = []

    count = 0
    for item in items:
        title = (
            item.find("title").text if item.find("title") is not None else ""
        )
        guid = item.find("guid").text if item.find("guid") is not None else ""
        pub_date = (
            item.find("pubDate").text
            if item.find("pubDate") is not None
            else ""
        )
        description = (
            item.find("description").text
            if item.find("description") is not None
            else ""
        )

        if not guid:
            continue

        soup = BeautifulSoup(description, "html.parser")
        og_image = extract_and_treat_image(soup)
        clean_html_body(soup)

        # O format_date agora retorna a string formatada E o objeto datetime (para ordenação)
        formatted_date, dt_object = format_date(pub_date)

        markdown_body = md(str(soup), heading_style="ATX").strip()

        front_matter = (
            "---\n"
            "layout: single\n"
            f'title: "{title}"\n'
            f"date: {formatted_date}\n"
            f"permalink: /{guid}/\n"
            "header:\n"
            f'  og_image: "{og_image}"\n'
            "---\n\n"
        )

        content_final = front_matter + markdown_body

        filename = f"{guid}.md"
        file_path = os.path.join(output_dir, filename)

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content_final)

        # Guarda os dados necessários para o index.md
        post_list_for_index.append(
            {"title": title, "guid": guid, "date_obj": dt_object}
        )

        count += 1

    # --- GERAÇÃO DA LISTA EM MARKDOWN (INDEX) ---

    # Ordena a lista: do mais recente (maior data) para o mais antigo (menor data)
    post_list_for_index.sort(key=lambda x: x["date_obj"], reverse=True)

    index_lines = []
    for post in post_list_for_index:
        # Formata o objeto de data para dd/mm/aa conforme solicitado
        date_dd_mm_yy = post["date_obj"].strftime("%d/%m/%y")

        # Se o seu <title> já vem escrito como "Cena 1", a linha abaixo gera: [Cena 1 10/07/26](mds/guid.md)
        # Ajustei com um espaço entre o título e a data para ficar legível.
        line = f"[{post['title']} {date_dd_mm_yy}](mds/{post['guid']}.md)"
        index_lines.append(line)

    # Une todas as linhas com quebras de página e salva o arquivo index.md
    index_content = "\n".join(index_lines)
    index_path = os.path.join(os.path.dirname(__file__), "index.md")

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(index_content)

    print(
        f"Sucesso! {count} arquivos Markdown salvos na pasta: '{output_dir}'"
    )
    print(f"Lista gerada com sucesso em: '{index_path}'")


if __name__ == "__main__":
    xml_filename = "blog.xml"

    if os.path.exists(xml_filename):
        process_xml_to_md(xml_filename)
    else:
        print(
            f"Arquivo '{xml_filename}' não encontrado na raiz do script. Por favor, verifique."
        )
