import flet as ft
import math
import os
import threading
import unicodedata
from datetime import datetime
from backend.api import load_all_data_if_needed, parse_nlp_query

CATEGORIES = {
    "1": {"name": "Процессоры", "prefix": "PRC"},
    "2": {"name": "Видеокарты", "prefix": "VGA"},
    "3": {"name": "Оперативная память", "prefix": "RAM"},
    "4": {"name": "Накопители SSD", "prefix": "SSD"},
    "5": {"name": "Жёсткие диски", "prefix": "HDD"},
    "6": {"name": "Материнские платы", "prefix": "MBD"},
    "7": {"name": "Блоки питания", "prefix": "PSU"},
    "8": {"name": "Корпуса", "prefix": "CAS"},
    "9": {"name": "Системы охлаждения", "prefix": "CLC"},
    "10": {"name": "Мониторы", "prefix": "MON"},
    "11": {"name": "Ноутбуки", "prefix": "NBT"},
    "12": {"name": "Клавиатуры", "prefix": "KBD"},
    "13": {"name": "Мыши", "prefix": "MOU"},
    "14": {"name": "Наушники и гарнитуры", "prefix": "HDR"},
    "15": {"name": "Веб-камеры", "prefix": "WBC"},
    "16": {"name": "Микрофоны", "prefix": "MIC"},
    "17": {"name": "Акустика", "prefix": "SPK"},
    "18": {"name": "Коврики для мыши", "prefix": "PAD"},
    "19": {"name": "Принтеры и МФУ", "prefix": "PRT"},
    "20": {"name": "Сетевое оборудование", "prefix": "NET"},
    "21": {"name": "ИБП", "prefix": "UPS"},
    "22": {"name": "Кабели и переходники", "prefix": "CBL"},
    "23": {"name": "Внешние накопители", "prefix": "EXT"},
    "24": {"name": "Оптические приводы", "prefix": "ODD"},
}


def show_snack(page: ft.Page, text: str, color_hex: str):
    snack = ft.SnackBar(content=ft.Text(text, color="#FFFFFF"), bgcolor=color_hex)
    try:
        if hasattr(page, "open"):
            page.open(snack)
        elif hasattr(page, "show_dialog"):
            page.show_dialog(snack)
        else:
            page.snack_bar = snack
            snack.open = True
            page.update()
    except Exception as ex:
        print(f"Failed to show SnackBar: {ex}")


def visual_len(text):
    return len(unicodedata.normalize("NFC", str(text)))


def format_as_text_table(headers, rows):
    if not rows:
        return "Таблица пуста."
    col_widths = [visual_len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            col_widths[idx] = max(col_widths[idx], visual_len(str(cell)))

    header_parts = []
    for i, h in enumerate(headers):
        padding_needed = col_widths[i] - visual_len(str(h))
        header_parts.append(str(h) + (" " * padding_needed))
    header_line = " | ".join(header_parts)

    separator = "-+-".join("-" * col_widths[i] for i in range(len(headers)))

    data_lines = []
    for row in rows:
        row_parts = []
        for i, cell in enumerate(row):
            padding_needed = col_widths[i] - visual_len(str(cell))
            row_parts.append(str(cell) + (" " * padding_needed))
        data_lines.append(" | ".join(row_parts))

    return f"{header_line}\n{separator}\n" + "\n".join(data_lines)


def save_as_txt(file_path: str, text_content: str):
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(text_content)


def save_as_pdf(file_path: str, text_content: str):
    from fpdf import FPDF

    pdf = FPDF()
    pdf.add_page()

    font_file = os.path.join(
        os.path.dirname(os.path.dirname(__file__)), "assets", "Consolas.ttf"
    )
    font_name = "ConsolasMono"

    if os.path.exists(font_file):
        pdf.add_font(font_name, style="", fname=font_file)
        pdf.set_font(font_name, size=9)
    else:
        pdf.set_font("helvetica", size=9)

    for line in text_content.split("\n"):
        try:
            pdf.cell(0, 5, text=line, ln=True)
        except Exception:
            safe_line = line.encode("ascii", "ignore").decode("ascii")
            pdf.cell(0, 5, text=safe_line, ln=True)

    pdf.output(file_path)


def get_reports_view(page: ft.Page):
    if page.fonts is None:
        page.fonts = {}
    page.fonts["CyrillicMono"] = "Consolas.ttf"
    page.update()

    options = [
        "1. ABC-анализ продаж (по выручке)",
        "2. XYZ-анализ стабильности спроса",
        "3. Рейтинг эффективности продавцов",
        "4. Анализ продаж по категориям товаров",
        "5. Динамика продаж по месяцам",
        "6. Анализ прибыльности по брендам",
        "7. Анализ возвратов и отмен",
        "8. Популярность типов оплаты",
        "9. ABC-анализ по количеству сделок",
        "10. Анализ ценовых диапазонов",
        "11. Продажи по дням недели",
        "12. Товары с критически низким запасом",
        "13. Анализ скидок и упущенной выгоды",
        "14. Анализ гарантийного риска (Возвраты по категориям)",
        "15. Топ-10 самых дорогих единичных продаж",
        "Свой вариант...",
    ]

    last_report_text = [""]

    dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(text=opt) for opt in options],
        width=400,
        hint_text="Выберите тип отчета",
        border_color="#333333",
        color="#FFFFFF",
    )

    custom_input = ft.TextField(
        visible=False,
        width=600,
        hint_text="Например: 'Какой продавец продал больше всего видеокарт в декабре?'",
        border_color="#333333",
    )

    generate_btn = ft.ElevatedButton(
        "Составить отчет",
        icon=ft.Icons.ANALYTICS,
        bgcolor="#2E2E2E",
        color="#FFFFFF",
    )

    progress_ring = ft.ProgressRing(visible=False, width=20, height=20)

    report_output = ft.TextField(
        multiline=True,
        expand=True,
        read_only=True,
        border_color="#222222",
        text_size=12,
        text_style=ft.TextStyle(font_family="CyrillicMono", color="#E0E0E0"),
    )

    file_picker = ft.FilePicker()
    if hasattr(page, "services"):
        page.services.append(file_picker)
    else:
        try:
            page._services.append(file_picker)
        except:
            page.overlay.append(file_picker)

    async def on_save_txt_click(e):
        if not last_report_text[0]:
            show_snack(page, "Сначала составьте отчет!", "#D32F2F")
            return
        path = await file_picker.save_file(
            dialog_title="Сохранить как TXT",
            file_name="report.txt",
            allowed_extensions=["txt"],
        )
        if path:
            if not path.lower().endswith(".txt"):
                path += ".txt"
            try:
                save_as_txt(path, last_report_text[0])
                show_snack(page, f"TXT сохранен: {path}", "#388E3C")
            except Exception as ex:
                show_snack(page, f"Ошибка сохранения TXT: {ex}", "#D32F2F")

    async def on_save_pdf_click(e):
        if not last_report_text[0]:
            show_snack(page, "Сначала составьте отчет!", "#D32F2F")
            return
        path = await file_picker.save_file(
            dialog_title="Сохранить как PDF",
            file_name="report.pdf",
            allowed_extensions=["pdf"],
        )
        if path:
            if not path.lower().endswith(".pdf"):
                path += ".pdf"
            try:
                save_as_pdf(path, last_report_text[0])
                show_snack(page, f"PDF сохранен: {path}", "#388E3C")
            except Exception as ex:
                show_snack(page, f"Ошибка сохранения PDF: {ex}", "#D32F2F")

    save_txt_btn = ft.IconButton(
        icon=ft.Icons.SAVE_ALT,
        tooltip="Сохранить как TXT",
        icon_color="#2196F3",
        on_click=on_save_txt_click,
    )

    save_pdf_btn = ft.IconButton(
        icon=ft.Icons.PICTURE_AS_PDF,
        tooltip="Сохранить как PDF",
        icon_color="#E53935",
        on_click=on_save_pdf_click,
    )

    def on_dropdown_change(e):
        custom_input.visible = dropdown.value == "Свой вариант..."
        custom_input.update()

    dropdown.on_select = on_dropdown_change

    def parse_date(d_str):
        if not d_str:
            return None
        try:
            return datetime.fromisoformat(d_str.replace("Z", "+00:00")).date()
        except:
            try:
                return datetime.strptime(d_str.split("T")[0], "%Y-%m-%d").date()
            except:
                return None

    def execute_nlp_interpreter(sales, products, req):
        if not req.get("is_valid", False):
            return f"Ошибка: {req.get('error_message', 'Неизвестная ошибка парсинга запроса.')}"

        start_date = parse_date(req.get("start_date"))
        end_date = parse_date(req.get("end_date"))
        min_qty = req.get("min_quantity")
        max_qty = req.get("max_quantity")
        min_amt = req.get("min_amount")
        max_amt = req.get("max_amount")
        categories = req.get("product_categories")
        product_query = req.get("product_query")
        seller_name = req.get("seller_name")
        payment_types = req.get("payment_types")
        order_statuses = req.get("order_statuses")

        group_by = req.get("group_by", "none")
        agg_metric = req.get("agg_metric", "sum_revenue")
        sort_by = req.get("sort_by")
        sort_order = req.get("sort_order", "desc")
        limit = req.get("limit")

        filtered = []
        for s in sales:
            prod = next(
                (p for p in products if p.get("sku") == s.get("product_id")), None
            )
            cat_id = str(prod.get("category_id")) if prod else "Unknown"
            cat_name = CATEGORIES.get(cat_id, {}).get("name", "Другие")

            s_date = parse_date(s.get("sale_date"))

            if start_date and s_date and s_date < start_date:
                continue
            if end_date and s_date and s_date > end_date:
                continue

            qty = int(s.get("quantity", 0))
            if min_qty is not None and qty < min_qty:
                continue
            if max_qty is not None and qty > max_qty:
                continue

            amt = float(s.get("total_amount", 0.0))
            if min_amt is not None and amt < min_amt:
                continue
            if max_amt is not None and amt > max_amt:
                continue

            if categories and cat_name not in categories:
                continue

            if product_query:
                pq_low = product_query.lower()
                p_name = prod.get("name", "").lower() if prod else ""
                p_sku = s.get("product_id", "").lower()
                if pq_low not in p_name and pq_low not in p_sku:
                    continue

            if seller_name:
                if seller_name.lower() not in s.get("seller_name", "").lower():
                    continue

            if payment_types and s.get("payment_type") not in payment_types:
                continue

            if order_statuses and s.get("order_status") not in order_statuses:
                continue

            filtered.append((s, prod, cat_name))

        if not filtered:
            return "Сделки, удовлетворяющие критериям поиска, не обнаружены."

        if not group_by or group_by == "none":
            records = []
            for s, prod, cat_name in filtered:
                records.append(
                    {
                        "order": s.get("order_number"),
                        "sku": s.get("product_id"),
                        "name": prod.get("name") if prod else "Неизвестно",
                        "qty": s.get("quantity", 1),
                        "price": s.get("price_per_unit", 0.0),
                        "total": s.get("total_amount", 0.0),
                        "seller": s.get("seller_name", ""),
                        "date": (
                            s.get("sale_date", "").split("T")[0]
                            if isinstance(s.get("sale_date"), str)
                            else ""
                        ),
                    }
                )

            sort_key_map = {
                "quantity": "qty",
                "price_per_unit": "price",
                "total_amount": "total",
                "sale_date": "date",
            }
            real_key = sort_key_map.get(sort_by, "total")
            records.sort(
                key=lambda x: x.get(real_key, 0.0), reverse=(sort_order == "desc")
            )

            if limit:
                records = records[:limit]

            headers = [
                "Заказ",
                "SKU",
                "Товар",
                "Кол-во",
                "Цена",
                "Сумма",
                "Продавец",
                "Дата",
            ]
            rows = []
            for r in records:
                rows.append(
                    [
                        r["order"],
                        r["sku"],
                        r["name"][:20],
                        str(r["qty"]),
                        f"{r['price']:.2f}",
                        f"{r['total']:.2f}",
                        r["seller"],
                        r["date"],
                    ]
                )

            output = (
                f"=== ДЕТАЛЬНЫЙ ОТЧЕТ ПО СДЕЛКАМ (Найдено: {len(filtered)}) ===\n\n"
            )
            output += format_as_text_table(headers, rows)
            return output

        else:
            groups = {}
            for s, prod, cat_name in filtered:
                if group_by == "product":
                    g_key = s.get("product_id")
                    g_label = prod.get("name")[:30] if prod else "Неизвестный товар"
                elif group_by == "seller":
                    g_key = s.get("seller_name")
                    g_label = g_key
                elif group_by == "category":
                    g_key = cat_name
                    g_label = g_key
                elif group_by == "payment_type":
                    g_key = s.get("payment_type")
                    g_label = g_key
                elif group_by == "order_status":
                    g_key = s.get("order_status")
                    g_label = g_key
                elif group_by == "date_month":
                    dt_str = s.get("sale_date")
                    g_key = dt_str.split("T")[0][:7] if dt_str else "Неизвестный месяц"
                    g_label = g_key
                else:
                    g_key = "Итого"
                    g_label = "Итого"

                if g_key not in groups:
                    groups[g_key] = {"label": g_label, "sales": []}
                groups[g_key]["sales"].append((s, prod, cat_name))

            records = []
            for g_key, data in groups.items():
                sales_in_group = data["sales"]
                sum_rev = sum(
                    float(x[0].get("total_amount", 0.0)) for x in sales_in_group
                )
                sum_qty = sum(int(x[0].get("quantity", 0)) for x in sales_in_group)
                cnt = len(sales_in_group)
                avg_p = (
                    sum(float(x[0].get("price_per_unit", 0.0)) for x in sales_in_group)
                    / cnt
                    if cnt > 0
                    else 0.0
                )

                records.append(
                    {
                        "key": g_key,
                        "label": data["label"],
                        "sum_revenue": sum_rev,
                        "sum_quantity": sum_qty,
                        "count_sales": cnt,
                        "avg_price": avg_p,
                    }
                )

            s_key = (
                sort_by
                if sort_by
                in ["sum_revenue", "sum_quantity", "count_sales", "avg_price"]
                else agg_metric
            )
            if s_key not in [
                "sum_revenue",
                "sum_quantity",
                "count_sales",
                "avg_price",
            ]:
                s_key = "sum_revenue"

            records.sort(key=lambda x: x.get(s_key, 0), reverse=(sort_order == "desc"))

            if limit:
                records = records[:limit]

            headers = [
                "Группа",
                "Выручка (руб.)",
                "Продано (шт)",
                "Сделок",
                "Ср. цена за шт.",
            ]
            rows = []
            for r in records:
                rows.append(
                    [
                        f"{r['key']} ({r['label']})",
                        f"{r['sum_revenue']:.2f}",
                        str(r["sum_quantity"]),
                        str(r["count_sales"]),
                        f"{r['avg_price']:.2f}",
                    ]
                )

            output = f"=== АГРЕГИРОВАННЫЙ СВОДНЫЙ ОТЧЕТ (Групп: {len(groups)}) ===\n\n"
            output += format_as_text_table(headers, rows)
            return output

    def on_generate_thread():
        try:
            products, sales, _ = load_all_data_if_needed()
            if not sales:
                report_output.value = "Ошибка: данные о продажах недоступны."
                report_output.update()
                return

            choice = dropdown.value
            if not choice:
                report_output.value = "Пожалуйста, выберите тип отчета."
                report_output.update()
                return

            if choice.startswith("1."):
                product_revenue = {}
                for s in sales:
                    sku = s.get("product_id")
                    product_revenue[sku] = product_revenue.get(sku, 0.0) + float(
                        s.get("total_amount", 0.0)
                    )

                sorted_rev = sorted(
                    product_revenue.items(), key=lambda x: x[1], reverse=True
                )
                total_rev = sum(product_revenue.values())

                if total_rev == 0:
                    report_output.value = "Недостаточно данных для ABC-анализа."
                    report_output.update()
                    return

                headers = [
                    "Ранг",
                    "SKU",
                    "Название товара",
                    "Выручка (руб.)",
                    "Доля %",
                    "Накоп. %",
                    "Группа",
                ]
                rows = []
                cum_pct = 0.0
                for rank, (sku, rev) in enumerate(sorted_rev, 1):
                    prod = next((p for p in products if p.get("sku") == sku), None)
                    name = prod.get("name")[:30] if prod else "Неизвестный товар"
                    pct = (rev / total_rev) * 100
                    cum_pct += pct

                    if cum_pct <= 80.05:
                        grp = "A (Высокая значимость)"
                    elif cum_pct <= 95.05:
                        grp = "B (Средняя значимость)"
                    else:
                        grp = "C (Низкая значимость)"

                    rows.append(
                        [
                            str(rank),
                            sku,
                            name,
                            f"{rev:.2f}",
                            f"{pct:.2f}%",
                            f"{min(100.0, cum_pct):.2f}%",
                            grp,
                        ]
                    )

                out = f"=== ABC-АНАЛИЗ ПРОДАЖ ===\nОбщая выручка: {total_rev:.2f} руб.\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("2."):
                sku_weekly_qty = {}
                all_weeks = set()
                for s in sales:
                    sku = s.get("product_id")
                    qty = int(s.get("quantity", 0))
                    dt_val = s.get("sale_date")
                    if not dt_val:
                        continue
                    try:
                        dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
                        yr_wk = f"{dt.year}-W{dt.isocalendar()[1]:02d}"
                        all_weeks.add(yr_wk)
                        if sku not in sku_weekly_qty:
                            sku_weekly_qty[sku] = {}
                        sku_weekly_qty[sku][yr_wk] = (
                            sku_weekly_qty[sku].get(yr_wk, 0) + qty
                        )
                    except:
                        continue

                if not all_weeks:
                    report_output.value = (
                        "Ошибка: нет достаточных временных данных для XYZ-анализа."
                    )
                    report_output.update()
                    return

                sorted_weeks = sorted(list(all_weeks))
                headers = [
                    "SKU",
                    "Название товара",
                    "Продано (шт)",
                    "Ср. в неделю",
                    "СКО",
                    "Коэфф. вариации CV %",
                    "Класс спроса",
                ]
                rows = []

                for sku, weekly_data in sku_weekly_qty.items():
                    qtys = [weekly_data.get(w, 0) for w in sorted_weeks]
                    total_qty = sum(qtys)
                    n = len(qtys)
                    if n < 2 or total_qty == 0:
                        continue

                    mean = total_qty / n
                    variance = sum((x - mean) ** 2 for x in qtys) / n
                    std_dev = math.sqrt(variance)
                    cv = std_dev / mean if mean > 0 else 0.0

                    if cv <= 0.10:
                        grp = "X (Стабильный)"
                    elif cv <= 0.25:
                        grp = "Y (Колеблющийся)"
                    else:
                        grp = "Z (Случайный)"

                    prod = next((p for p in products if p.get("sku") == sku), None)
                    name = prod.get("name")[:30] if prod else "Неизвестный товар"

                    rows.append(
                        [
                            sku,
                            name,
                            str(total_qty),
                            f"{mean:.2f}",
                            f"{std_dev:.2f}",
                            f"{cv * 100:.1f}%",
                            grp,
                        ]
                    )

                rows.sort(key=lambda x: float(x[5].replace("%", "")))
                out = f"=== XYZ-АНАЛИЗ СТАБИЛЬНОСТИ СПРОСА ===\nПериод расчета: {len(sorted_weeks)} нед. ({sorted_weeks[0]} - {sorted_weeks[-1]})\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("3."):
                seller_stats = {}
                for s in sales:
                    name = s.get("seller_name", "Неизвестно")
                    rev = float(s.get("total_amount", 0.0))
                    qty = int(s.get("quantity", 0))

                    if name not in seller_stats:
                        seller_stats[name] = {"rev": 0.0, "qty": 0, "cnt": 0}
                    seller_stats[name]["rev"] += rev
                    seller_stats[name]["qty"] += qty
                    seller_stats[name]["cnt"] += 1

                headers = [
                    "Продавец",
                    "Выручка (руб.)",
                    "Штук продано",
                    "Сделок",
                    "Ср. чек",
                ]
                rows = []
                for name, stats in seller_stats.items():
                    avg_chk = stats["rev"] / stats["cnt"] if stats["cnt"] > 0 else 0.0
                    rows.append(
                        [
                            name,
                            f"{stats['rev']:.2f}",
                            str(stats["qty"]),
                            str(stats["cnt"]),
                            f"{avg_chk:.2f}",
                        ]
                    )

                rows.sort(key=lambda x: float(x[1]), reverse=True)
                out = "=== РЕЙТИНГ ЭФФЕКТИВНОСТИ ПРОДАВЦОВ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("4."):
                cat_stats = {}
                tot_rev = 0.0
                for s in sales:
                    sku = s.get("product_id")
                    rev = float(s.get("total_amount", 0.0))
                    qty = int(s.get("quantity", 0))

                    prod = next((p for p in products if p.get("sku") == sku), None)
                    cat_id = str(prod.get("category_id")) if prod else "Unknown"
                    cat_name = CATEGORIES.get(cat_id, {}).get("name", "Другие")

                    if cat_name not in cat_stats:
                        cat_stats[cat_name] = {"rev": 0.0, "qty": 0, "cnt": 0}
                    cat_stats[cat_name]["rev"] += rev
                    cat_stats[cat_name]["qty"] += qty
                    cat_stats[cat_name]["cnt"] += 1
                    tot_rev += rev

                headers = [
                    "Категория",
                    "Выручка (руб.)",
                    "Доля %",
                    "Продано (шт)",
                    "Сделок",
                ]
                rows = []
                for name, stats in cat_stats.items():
                    pct = (stats["rev"] / tot_rev * 100) if tot_rev > 0 else 0.0
                    rows.append(
                        [
                            name,
                            f"{stats['rev']:.2f}",
                            f"{pct:.2f}%",
                            str(stats["qty"]),
                            str(stats["cnt"]),
                        ]
                    )

                rows.sort(key=lambda x: float(x[1]), reverse=True)
                out = "=== АНАЛИЗ ПРОДАЖ ПО КАТЕГОРИЯМ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("5."):
                month_stats = {}
                for s in sales:
                    dt_val = s.get("sale_date")
                    if not dt_val:
                        continue
                    try:
                        month = dt_val.split("T")[0][:7]
                        rev = float(s.get("total_amount", 0.0))
                        if month not in month_stats:
                            month_stats[month] = {"rev": 0.0, "cnt": 0}
                        month_stats[month]["rev"] += rev
                        month_stats[month]["cnt"] += 1
                    except:
                        continue

                sorted_m = sorted(month_stats.keys())
                headers = ["Месяц", "Выручка (руб.)", "Прирост %", "Сделок"]
                rows = []
                prev_rev = None

                for m in sorted_m:
                    rev = month_stats[m]["rev"]
                    cnt = month_stats[m]["cnt"]

                    if prev_rev is None or prev_rev == 0:
                        growth = "-"
                    else:
                        pct = ((rev - prev_rev) / prev_rev) * 100
                        growth = f"{'+' if pct >= 0 else ''}{pct:.1f}%"

                    rows.append([m, f"{rev:.2f}", growth, str(cnt)])
                    prev_rev = rev

                out = "=== ДИНАМИКА ПРОДАЖ ПО МЕСЯЦАМ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("6."):
                brand_revenue = {}
                brand_cost = {}
                brand_qty = {}
                for s in sales:
                    sku = s.get("product_id")
                    qty = int(s.get("quantity", 0))
                    rev = float(s.get("total_amount", 0.0))

                    prod = next((p for p in products if p.get("sku") == sku), None)
                    brand = prod.get("brand", "Неизвестно") if prod else "Неизвестно"
                    purch_p = float(prod.get("purchase_price", 0.0)) if prod else 0.0

                    brand_revenue[brand] = brand_revenue.get(brand, 0.0) + rev
                    brand_cost[brand] = brand_cost.get(brand, 0.0) + (purch_p * qty)
                    brand_qty[brand] = brand_qty.get(brand, 0) + qty

                headers = [
                    "Бренд",
                    "Выручка",
                    "Себест.",
                    "Прибыль",
                    "Маржа %",
                    "Продано (шт)",
                ]
                rows = []
                for b in brand_revenue.keys():
                    rev = brand_revenue[b]
                    cost = brand_cost[b]
                    profit = rev - cost
                    margin = (profit / rev * 100) if rev > 0 else 0.0
                    rows.append(
                        [
                            b,
                            f"{rev:.2f}",
                            f"{cost:.2f}",
                            f"{profit:.2f}",
                            f"{margin:.2f}%",
                            str(brand_qty[b]),
                        ]
                    )
                rows.sort(key=lambda x: float(x[3]), reverse=True)
                out = "=== АНАЛИЗ ПРИБЫЛЬНОСТИ ПО БРЕНДАМ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("7."):
                ret_sales = [
                    s for s in sales if s.get("order_status") in ["возврат", "отменён"]
                ]
                headers = [
                    "Заказ",
                    "Товар (SKU)",
                    "Кол-во",
                    "Сумма потеряна",
                    "Статус",
                    "Комментарий",
                ]
                rows = []
                tot_lost = 0.0
                for s in ret_sales:
                    tot_lost += float(s.get("total_amount", 0.0))
                    rows.append(
                        [
                            s.get("order_number"),
                            s.get("product_id"),
                            str(s.get("quantity", 0)),
                            f"{float(s.get('total_amount', 0.0)):.2f}",
                            s.get("order_status"),
                            s.get("comment") or "-",
                        ]
                    )
                out = f"=== АНАЛИЗ ВОЗВРАТОВ И ОТМЕН ===\nИтого упущенная выгода: {tot_lost:.2f} руб.\nВсего проблемных заказов: {len(ret_sales)}\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("8."):
                pay_stats = {}
                tot_rev = 0.0
                for s in sales:
                    pt = s.get("payment_type", "Не указан")
                    rev = float(s.get("total_amount", 0.0))
                    qty = int(s.get("quantity", 0))
                    if pt not in pay_stats:
                        pay_stats[pt] = {"rev": 0.0, "qty": 0, "cnt": 0}
                    pay_stats[pt]["rev"] += rev
                    pay_stats[pt]["qty"] += qty
                    pay_stats[pt]["cnt"] += 1
                    tot_rev += rev
                headers = ["Тип оплаты", "Выручка", "Доля %", "Продано (шт)", "Сделок"]
                rows = []
                for pt, stats in pay_stats.items():
                    pct = (stats["rev"] / tot_rev * 100) if tot_rev > 0 else 0.0
                    rows.append(
                        [
                            pt,
                            f"{stats['rev']:.2f}",
                            f"{pct:.2f}%",
                            str(stats["qty"]),
                            str(stats["cnt"]),
                        ]
                    )
                rows.sort(key=lambda x: float(x[1]), reverse=True)
                out = "=== ПОПУЛЯРНОСТЬ ТИПОВ ОПЛАТЫ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("9."):
                prod_cnt = {}
                for s in sales:
                    sku = s.get("product_id")
                    prod_cnt[sku] = prod_cnt.get(sku, 0) + 1
                sorted_cnt = sorted(prod_cnt.items(), key=lambda x: x[1], reverse=True)
                tot_cnt = sum(prod_cnt.values())
                headers = [
                    "Ранг",
                    "SKU",
                    "Название",
                    "Кол-во сделок",
                    "Доля %",
                    "Накоп. %",
                    "Класс",
                ]
                rows = []
                cum_pct = 0.0
                for rank, (sku, cnt) in enumerate(sorted_cnt, 1):
                    prod = font_name = next(
                        (p for p in products if p.get("sku") == sku), None
                    )
                    name = prod.get("name")[:30] if prod else "Неизвестный товар"
                    pct = (cnt / tot_cnt) * 100
                    cum_pct += pct
                    if cum_pct <= 80.05:
                        grp = "A (Частые сделки)"
                    elif cum_pct <= 95.05:
                        grp = "B (Средние)"
                    else:
                        grp = "C (Редкие)"
                    rows.append(
                        [
                            str(rank),
                            sku,
                            name,
                            str(cnt),
                            f"{pct:.2f}%",
                            f"{min(100.0, cum_pct):.2f}%",
                            grp,
                        ]
                    )
                out = f"=== ABC-АНАЛИЗ ПО КОЛИЧЕСТВУ СДЕЛОК ===\nВсего сделок: {tot_cnt}\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("10."):
                ranges = {
                    "Бюджетный (до 10к)": {"rev": 0.0, "qty": 0, "cnt": 0},
                    "Средний (10к - 50к)": {"rev": 0.0, "qty": 0, "cnt": 0},
                    "Премиальный (50к - 100к)": {"rev": 0.0, "qty": 0, "cnt": 0},
                    "Ультра (более 100к)": {"rev": 0.0, "qty": 0, "cnt": 0},
                }
                for s in sales:
                    unit_p = float(s.get("price_per_unit", 0.0))
                    rev = float(s.get("total_amount", 0.0))
                    qty = int(s.get("quantity", 0))
                    if unit_p < 10000:
                        seg = "Бюджетный (до 10к)"
                    elif unit_p < 50000:
                        seg = "Средний (10к - 50к)"
                    elif unit_p < 100000:
                        seg = "Премиальный (50к - 100к)"
                    else:
                        seg = "Ультра (более 100к)"
                    ranges[seg]["rev"] += rev
                    ranges[seg]["qty"] += qty
                    ranges[seg]["cnt"] += 1
                headers = ["Ценовой диапазон", "Выручка", "Продано (шт)", "Сделок"]
                rows = []
                for k, v in ranges.items():
                    rows.append([k, f"{v['rev']:.2f}", str(v["qty"]), str(v["cnt"])])
                out = "=== АНАЛИЗ ЦЕНОВЫХ ДИАПАЗОНОВ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("11."):
                days_map = {
                    0: "Понедельник",
                    1: "Вторник",
                    2: "Среда",
                    3: "Четверг",
                    4: "Пятница",
                    5: "Суббота",
                    6: "Воскресенье",
                }
                days_stats = {d: {"rev": 0.0, "cnt": 0} for d in days_map.values()}
                for s in sales:
                    dt_val = s.get("sale_date")
                    if not dt_val:
                        continue
                    try:
                        dt = datetime.fromisoformat(dt_val.replace("Z", "+00:00"))
                        day_name = days_map[dt.weekday()]
                        days_stats[day_name]["rev"] += float(s.get("total_amount", 0.0))
                        days_stats[day_name]["cnt"] += 1
                    except:
                        continue
                headers = ["День недели", "Выручка", "Кол-во сделок"]
                rows = []
                for d in days_map.values():
                    rows.append(
                        [d, f"{days_stats[d]['rev']:.2f}", str(days_stats[d]["cnt"])]
                    )
                out = "=== ПРОДАЖИ ПО ДНЯМ НЕДЕЛИ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("12."):
                low_stock = [p for p in products if int(p.get("stock", 0)) < 5]
                prod_sales_cnt = {}
                for s in sales:
                    sku = s.get("product_id")
                    prod_sales_cnt[sku] = prod_sales_cnt.get(sku, 0) + int(
                        s.get("quantity", 0)
                    )
                headers = [
                    "SKU",
                    "Название",
                    "Остаток на складе",
                    "Продано всего (шт)",
                    "Статус",
                ]
                rows = []
                for p in low_stock:
                    sku = p.get("sku")
                    sold = prod_sales_cnt.get(sku, 0)
                    rows.append(
                        [
                            sku,
                            p.get("name")[:30],
                            str(p.get("stock", 0)),
                            str(sold),
                            "КРИТИЧЕСКИЙ" if int(p.get("stock", 0)) == 0 else "МАЛО",
                        ]
                    )
                rows.sort(key=lambda x: int(x[3]), reverse=True)
                out = "=== ТОВАРЫ С КРИТИЧЕСКИ НИЗКИМ ЗАПАСОМ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("13."):
                cat_discounts = {}
                for s in sales:
                    sku = s.get("product_id")
                    qty = int(s.get("quantity", 0))
                    prod = next((p for p in products if p.get("sku") == sku), None)
                    cat_id = str(prod.get("category_id")) if prod else "Unknown"
                    cat_name = CATEGORIES.get(cat_id, {}).get("name", "Другие")

                    if cat_name not in cat_stats:
                        cat_stats[cat_name] = {"rev": 0.0, "qty": 0, "cnt": 0}

                    rev = float(s.get("total_amount", 0.0))
                    disc = float(s.get("discount", 0.0))
                    if disc > 0 and prod:
                        retail = float(prod.get("retail_price", 0.0))
                        actual = float(s.get("price_per_unit", 0.0))
                        discount_given = (retail - actual) * qty
                        if discount_given > 0:
                            if cat_name not in cat_discounts:
                                cat_discounts[cat_name] = {"lost": 0.0, "qty": 0}
                            cat_discounts[cat_name]["lost"] += discount_given
                            cat_discounts[cat_name]["qty"] += qty

                headers = [
                    "Категория",
                    "Сумма скидок (упущенная выгода)",
                    "Штук со скидкой",
                ]
                rows = []
                for cat, data in cat_discounts.items():
                    rows.append([cat, f"{data['lost']:.2f}", str(data["qty"])])
                rows.sort(key=lambda x: float(x[1]), reverse=True)
                out = "=== АНАЛИЗ СКИДОК И УПУЩЕННОЙ ВЫГОДЫ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("14."):
                cat_total_cnt = {}
                cat_return_cnt = {}
                for s in sales:
                    sku = s.get("product_id")
                    prod = next((p for p in products if p.get("sku") == sku), None)
                    if not prod:
                        continue
                    cat_id = str(prod.get("category_id"))
                    cat_name = CATEGORIES.get(cat_id, {}).get("name", "Другие")

                    cat_total_cnt[cat_name] = cat_total_cnt.get(cat_name, 0) + 1
                    if s.get("order_status") == "возврат":
                        cat_return_cnt[cat_name] = cat_return_cnt.get(cat_name, 0) + 1

                headers = [
                    "Категория",
                    "Всего продаж",
                    "Возвратов по гарантии",
                    "Процент возврата %",
                ]
                rows = []
                for cat, total in cat_total_cnt.items():
                    ret = cat_return_cnt.get(cat, 0)
                    pct = (ret / total * 100) if total > 0 else 0.0
                    rows.append([cat, str(total), str(ret), f"{pct:.2f}%"])
                rows.sort(key=lambda x: float(x[3].replace("%", "")), reverse=True)
                out = "=== АНАЛИЗ ГАРАНТИЙНОГО РИСКА ПО КАТЕГОРИЯМ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice.startswith("15."):
                sorted_sales = sorted(
                    sales, key=lambda x: float(x.get("total_amount", 0.0)), reverse=True
                )
                top_10 = sorted_sales[:10]
                headers = [
                    "Заказ",
                    "SKU товара",
                    "Кол-во",
                    "Цена",
                    "Сумма сделки",
                    "Продавец",
                    "Дата",
                ]
                rows = []
                for s in top_10:
                    rows.append(
                        [
                            s.get("order_number"),
                            s.get("product_id"),
                            str(s.get("quantity", 0)),
                            f"{float(s.get('price_per_unit', 0.0)):.2f}",
                            f"{float(s.get('total_amount', 0.0)):.2f}",
                            s.get("seller_name"),
                            s.get("sale_date").split("T")[0]
                            if s.get("sale_date")
                            else "-",
                        ]
                    )
                out = "=== ТОП-10 САМЫХ ДОРОГИХ ЕДИНИЧНЫХ ПРОДАЖ ===\n\n"
                out += format_as_text_table(headers, rows)
                last_report_text[0] = out
                report_output.value = out

            elif choice == "Свой вариант...":
                query = custom_input.value
                if not query or not query.strip():
                    report_output.value = (
                        "Пожалуйста, введите ваш запрос в текстовое поле."
                    )
                    report_output.update()
                    return

                report_output.value = "Обработка запроса ИИ..."
                report_output.update()

                nlp_result = parse_nlp_query(query)
                out = execute_nlp_interpreter(sales, products, nlp_result)
                last_report_text[0] = out
                report_output.value = out

        except Exception as ex:
            report_output.value = f"Произошла непредвиденная ошибка: {str(ex)}"
        finally:
            progress_ring.visible = False
            generate_btn.disabled = False
            dropdown.disabled = False
            custom_input.disabled = False
            page.update()

    def on_generate(e):
        progress_ring.visible = True
        generate_btn.disabled = True
        dropdown.disabled = True
        custom_input.disabled = True
        page.update()

        threading.Thread(target=on_generate_thread, daemon=True).start()

    generate_btn.on_click = on_generate

    return ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text("Генерация отчетов", size=24, weight=ft.FontWeight.BOLD),
                dropdown,
                custom_input,
                ft.Row(
                    [generate_btn, progress_ring, save_txt_btn, save_pdf_btn],
                    spacing=15,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                report_output,
            ]
        ),
    )
