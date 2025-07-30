import pdfplumber
from pdfplumber.page import Page
from pdfplumber.pdf import PDF
from pdfplumber._typing import T_bbox, T_num, T_obj_list
import re

from ...utils.logger import get_logger

logger = get_logger("extra_shipserv")


def process_shipserv_pdf(pdf_path: str) -> dict:
    """
    处理PDF文件，提取表格数据。

    Args:
        pdf_path (str): PDF文件的路径。
    Returns:
        dict: 返回一个字典，包含以下键：
            - 'table_data': list[list[str]] - 表格数据
            - 'section_data': list[dict] - "section"部分的键值对数据
            - 'meta_data': list[dict] - 附件元数据的键值对数据
    """

    try:
        meta_data = {}
        table_data = []
        section_data = []

        with pdfplumber.open(pdf_path) as pdf:
            try:
                # 获取表格数据
                for page in pdf.pages:
                    # 获取表格区域
                    region = get_table_region_in_page(page)
                    if not region:
                        continue

                    # 解析表格
                    header_data, body_data = extract_table_data(page, region)
                    # 如果数据为空，则添加表头数据
                    if not table_data:
                        table_data.extend(header_data)
                    # 添加表体数据
                    table_data.extend(body_data)

                # 提取"section"部分的数据
                section_data = extract_section_data(pdf, table_data)

                # 提取元数据中"subject"部分的数据，并更新元数据
                subject_data = extract_subject_data(pdf)
                meta_data.update(subject_data)

            except Exception as e:
                logger.error(
                    f"Error processing page {page.page_number} in {pdf_path}: {e}")

    except Exception as e:
        logger.error(f"Error opening PDF {pdf_path}: {e}")
        return None

    return {
        'meta_data': meta_data,
        'table_data': table_data,
        'section_data': section_data,
    }


def extract_subject_data(pdf: PDF) -> dict:
    """
    从页面中提取"subject"部分的键值对数据。

    Args:
        pdf (PDF): PDF对象。
    Returns:
        dict: 返回"subject"部分的键值对字典。如果未找到，则返回空字典。
    """
    try:
        for page in pdf.pages:
            # subject信息固定在页面左半侧，裁剪页面避免右半侧数据干扰
            cropped_page = page.crop((0, 0, page.width / 2 - 5, page.height))

            # 查询以'Subject:'开头的主题行
            lines = cropped_page.extract_text_lines()
            matched_lines = [
                line for line in lines if line['text'].startswith('Subject:')]
            if not matched_lines:
                continue
            subject_line = matched_lines[0]

            return extract_dict_from_lines_by_font(page, [subject_line])

        return {}
    except Exception as e:
        logger.error(f"Error extracting subject: {e}")
        return {}


def extract_section_data(pdf: PDF, table_results: list[list[str]]) -> list[dict]:
    """
    从页面中提取"section"部分的键值对数据。

    Args:
        pdf (PDF): PDF对象。
        table_results (list[list[str]]): 表格数据。
    Returns:
        list[dict]: 返回一个"section"部分的键值对数据的字典列表。
    """

    try:
        # 查找以"Equipment Section Name"开头的单元格
        section_cells = [row[0] for row in table_results if row and row[0].startswith(
            "Equipment Section Name")]
        # 保留原本顺序并去重
        section_cells = list(dict.fromkeys(section_cells))
        if not section_cells:
            return []

        # 提取页面中的文本行
        lines = []
        for (pageIndex, page) in enumerate(pdf.pages):
            for line in page.extract_text_lines():
                lines.append((line, pageIndex))

        dicts = []
        for cell in section_cells:
            # 查找与单元格内容匹配的文本行
            # 这里单元格内容是以换行符分隔的
            section_lines_text = cell.split('\n')

            section_lines = []
            pageIndex = None
            for text in section_lines_text:
                for (line, pIndex) in lines:
                    if line['text'] == text:
                        pageIndex = pIndex
                        section_lines.append(line)
                        break

            # 如果没有找到匹配的文本行，则警告并跳过
            if not section_lines:
                logger.warning(
                    f"No matching section lines found for '{cell}'.")
                continue

            # 提取与单元格内容匹配的文本行的字典
            section_dict = extract_dict_from_lines_by_font(
                pdf.pages[pageIndex], section_lines)
            dicts.append(section_dict)

        return dicts
    except Exception as e:
        logger.error(f"Error extracting sections: {e}")
        return []


def extract_table_data(page: Page, region: T_bbox) -> list[list[str]]:
    """
    从页面中提取表格数据。

    Args:
        page (Page): PDF页面对象。
        region (T_bbox): 表格区域的坐标。
    Returns:
        tuple[list[list[str]], list[list[str]]]: 返回表头数据和表体数据
    """

    cropped_page = page.crop(region)

    # 表格区域横纵分割线的坐标
    vertical_xs = []
    horizontal_ys = []

    # 额外添加外围边界
    vertical_xs.extend([region[0], region[2]])
    horizontal_ys.extend([region[1], region[3]])

    # 从页面中的线条对象获取分割线
    for line in cropped_page.lines:
        if abs(line['x0'] - line['x1']) < 1:  # 纵向线
            vertical_xs.append(line['x0'])  # 记录x坐标
        if abs(line['top'] - line['bottom']) < 1:   # 横向线
            horizontal_ys.append(line['top'])  # 记录y坐标

    # 去重并排序
    vertical_xs = sorted(list(set(vertical_xs)))
    horizontal_ys = sorted(list(set(horizontal_ys)))

    # 表头行的横向分割线
    header_line_bottom = horizontal_ys[1]

    # 表头和表体的区域
    header_region = (region[0], region[1], region[2], header_line_bottom)
    body_region = (region[0], header_line_bottom, region[2], region[3])

    # 表头数据
    # 由于表头缺少纵向分割线，使用显式的纵向分割线提取表头数据
    header_data = page.crop(header_region).extract_table(dict(
        vertical_strategy='explicit',
        explicit_vertical_lines=vertical_xs,
    ))

    # 表体数据
    # 由于自动检测的横向分割线有时会缺少一部分，使用显式的横向分割线提取表体数据
    body_data = page.crop(body_region).extract_table(dict(
        horizontal_strategy='explicit',
        explicit_horizontal_lines=horizontal_ys[1:],  # 跳过表头行
    ))

    return (header_data, body_data)


def get_table_region_in_page(page: Page) -> T_bbox | None:
    """
    获取页面中表格的区域。

    Args:
        page (Page): PDF页面对象。
    Returns:
        T_bbox | None: 返回表格区域的坐标。如果未找到表格区域，则返回None。
    """

    tables = page.find_tables()
    if not tables:
        return None

    # 获取表格区域的上下边界
    # 注意：此时的上边界不包含表头
    tables_top = tables[0].bbox[1]
    tables_bottom = tables[-1].bbox[3]

    # 裁剪页面以仅包含表格区域
    # 并获取表格区域的左右边界
    cropped_page = page.crop((0, tables_top, page.width, tables_bottom))
    lines = cropped_page.lines
    left = min(line['x0'] for line in lines)
    right = max(line['x1'] for line in lines)

    # 查找表头行的顶部位置
    header_top = find_header_top(page, tables_top)
    # 如果找到了表头行的顶部位置，则更新表格区域的上边界
    if not header_top:
        raise RuntimeError("No header found")
    tables_top = header_top

    return (left, tables_top, right, tables_bottom)


def find_header_top(page: Page, tables_top: T_num) -> T_num | None:
    """
    查找表格区域上方的表头行的顶部位置。

    Args:
        page (Page): PDF页面对象。
        tables_top (T_num): 表格区域的上边界。
    Returns:
        T_num | None: 返回表头行的顶部位置。如果未找到表头行，则返回None。
    """

    # 表头特征：以"# Part Type"或"Part"开头的行
    pattern = re.compile(r'^(# Part Type|Part)', re.IGNORECASE)

    # 获取表格区域上方的符合表头特征的文本行
    matching_lines = []
    for line in page.extract_text_lines():
        if line['top'] < tables_top and pattern.search(line['text']):
            matching_lines.append(line)

    if not matching_lines:
        return None

    # 表头行应是符合要求的行中，最接近表格区域上边界的行
    header_top = max(line['top'] for line in matching_lines)

    # 返回该行的顶部位置
    return header_top


def extract_dict_from_lines_by_font(page: Page, lines: T_obj_list) -> dict:
    """
    从页面中的文本行提取键值对字典，使用字体类型区分键和值。

    Args:
        page (Page): PDF页面对象。
        lines (T_obj_list): 页面中的文本行列表。
    Returns:
        dict: 返回一个包含键值对的字典，键和值根据字体类型区分。
    """
    words = []

    for line in lines:
        bbox = pdfplumber.utils.obj_to_bbox(line)
        words.extend(page.crop(bbox).extract_words(
            return_chars=True, x_tolerance=2))

    return extract_dict_from_words_by_font(words)


def extract_dict_from_words_by_font(words: T_obj_list) -> dict:
    """
    从单词列表中提取键值对字典，使用字体类型区分键和值。

    Args:
        words (T_obj_list): 单词列表，每个单词包含文本以及字符列表，每个字符包含字体信息。
    Returns:
        dict: 返回一个包含键值对的字典，键和值根据字体类型区分。
    """

    result = {}
    item = dict(key="", value="")
    state = "key"  # 当前是key还是value

    for word in words:
        font_name = word['chars'][0]['fontname']
        text = word.get('text', '')
        text += ' '  # 单词之间使用空格分割，多余的空格后续会消除

        # 判断字体类型
        if 'Bold' in font_name:
            # 如果当前状态是value且有内容，则保存之前的键值对
            if state == 'value' and item['key'] and item['value']:
                # 保存之前的键值对
                result[item['key'].strip()] = item['value'].strip()
                item['key'] = ""
                item['value'] = ""

            # 切换到粗体状态
            state = 'key'
        elif 'Regular' in font_name:
            # 切换到常规体状态
            state = 'value'
        else:
            # 如果不是粗体或常规体，跳过
            continue

        # 根据当前状态添加文本
        item[state] += text

    # 处理最后一对键值
    if item['key'] and item['value']:
        result[item['key'].strip()] = item['value'].strip()

    return result
