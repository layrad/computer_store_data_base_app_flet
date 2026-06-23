import flet as ft
import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import backend.api as api_mod
from backend.api import (
    get_products,
    get_sales,
    get_last_update,
    create_product,
    update_product,
    delete_product,
    create_sale,
    search_products,
    load_all_data_if_needed,
)

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

EMPLOYEES = [
    "Иванов Алексей Сергеевич",
    "Петрова Мария Андреевна",
    "Сидоров Дмитрий Олегович",
    "Козлова Елена Викторовна",
    "Новиков Артём Павлович",
    "Морозова Ольга Николаевна",
    "Волков Игорь Дмитриевич",
    "Соколова Татьяна Александровна",
]

PAYMENT_TYPES = ["наличные", "карта", "СБП", "рассрочка"]
SALE_STATUSES = ["выполнен", "возврат", "отменён"]
PRODUCT_STATUSES = ["в наличии", "под заказ", "нет в наличии"]

PRODUCT_SORT_KEYS = {
    0: "sku",
    1: "name",
    2: "category_id",
    3: "subcategory",
    4: "brand",
    5: "model",
    6: "description",
    7: "purchase_price",
    8: "retail_price",
    9: "discount",
    10: "price_with_discount",
    11: "stock",
    12: "warranty_months",
    13: "rating",
    14: "popularity",
    15: "weight_kg",
    16: "dimensions",
    17: "status",
    18: "compatibility",
    19: "notes",
}

SALE_SORT_KEYS = {
    0: "order_number",
    1: "product_id",
    2: "quantity",
    3: "price_per_unit",
    4: "discount",
    5: "total_amount",
    6: "seller_name",
    7: "sale_date",
    8: "payment_type",
    9: "order_status",
    10: "comment",
}


class TableView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.main_page = page
        self.expand = True
        self.padding = 20
        self.last_timestamp = 0.0
        self.is_saving = False

        self.local_products = []
        self.local_sales = []

        self.products_rows = []
        self.sales_rows = []

        self.products_sort_ascending = True
        self.sales_sort_ascending = True

        self.pending_changes = {
            "products": {"add": [], "update": [], "delete": []},
            "sales": {"add": []},
        }

        self.tabs = ft.Tabs(
            selected_index=0,
            length=2,
            expand=True,
            content=ft.Column(
                expand=True,
                controls=[
                    ft.TabBar(
                        tabs=[
                            ft.Tab(label="Товары"),
                            ft.Tab(label="Продажи"),
                        ]
                    ),
                    ft.TabBarView(
                        expand=True,
                        controls=[
                            self.build_products_tab(),
                            self.build_sales_tab(),
                        ],
                    ),
                ],
            ),
        )

        self.content = ft.Column(
            [
                ft.Row(
                    [
                        ft.Text("База данных", size=24, weight=ft.FontWeight.BOLD),
                        ft.Row(
                            [
                                ft.ElevatedButton(
                                    "Добавить товар",
                                    icon=ft.Icons.ADD_BOX,
                                    bgcolor="#2E2E2E",
                                    color=ft.Colors.WHITE,
                                    on_click=lambda _: self.open_product_dialog(),
                                ),
                                ft.ElevatedButton(
                                    "Добавить продажу",
                                    icon=ft.Icons.SHOPPING_CART,
                                    bgcolor="#2E2E2E",
                                    color=ft.Colors.WHITE,
                                    on_click=lambda _: self.open_sale_dialog(),
                                ),
                                ft.ElevatedButton(
                                    "Сохранить изменения",
                                    icon=ft.Icons.SAVE,
                                    bgcolor="#2E2E2E",
                                    color=ft.Colors.WHITE,
                                    on_click=self.save_all_changes,
                                ),
                            ],
                            wrap=True,
                            spacing=10,
                            run_spacing=10,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                    wrap=True,
                    spacing=10,
                    run_spacing=10,
                ),
                self.tabs,
            ],
            expand=True,
        )

    def generate_sequential_sku(self, category_id: str) -> str:
        cat_info = CATEGORIES.get(category_id)
        if not cat_info:
            return "UNKNOWN"
        prefix = cat_info["prefix"]

        max_num = 0
        all_current = self.local_products + self.pending_changes["products"]["add"]
        for p in all_current:
            sku = p.get("sku", "")
            if sku and sku.startswith(f"{prefix}-"):
                try:
                    num_str = sku.split("-")[1]
                    num_part = int(num_str)
                    if num_part > max_num:
                        max_num = num_part
                except (IndexError, ValueError):
                    pass

        next_num = max_num + 1
        return f"{prefix}-{next_num:03d}"

    def generate_sequential_order_number(self) -> str:
        max_num = 999
        all_current = self.local_sales + self.pending_changes["sales"]["add"]
        for s in all_current:
            order_num = s.get("order_number", "")
            if order_num and order_num.startswith("ЗК-"):
                try:
                    num_part = int(order_num.split("-")[1])
                    if num_part > max_num:
                        max_num = num_part
                except (IndexError, ValueError):
                    pass
        next_num = max_num + 1
        return f"ЗК-{next_num}"

    def did_mount(self):
        self.load_data()

    def load_data(self):
        threading.Thread(target=self._load_data_thread, daemon=True).start()

    def _load_data_thread(self):
        try:
            self.local_products, self.local_sales, self.last_timestamp = (
                load_all_data_if_needed()
            )

            self.products_rows = []
            for p in self.local_products:
                row = self.create_product_row(p)
                row.data = p
                self.products_rows.append(row)

            self.sales_rows = []
            for s in self.local_sales:
                row = self.create_sale_row(s)
                row.data = s
                self.sales_rows.append(row)

            self.refresh_tables()
        except Exception as ex:
            self.show_snack(f"Ошибка загрузки: {str(ex)}", ft.Colors.RED_700)

    def refresh_tables(self):
        self.products_table.rows = self.products_rows
        self.sales_table.rows = self.sales_rows
        self.main_page.update()

    def sort_products(self, e):
        self.products_sort_ascending = not self.products_sort_ascending
        col_index = e.column_index
        key = PRODUCT_SORT_KEYS.get(col_index)
        if key:

            def get_sort_val(r):
                val = r.data.get(key)
                if val is None:
                    return "" if isinstance(key, str) else 0
                if isinstance(val, str):
                    return val.lower()
                return val

            self.products_rows.sort(
                key=get_sort_val, reverse=not self.products_sort_ascending
            )

        self.products_table.sort_column_index = col_index
        self.products_table.sort_ascending = self.products_sort_ascending
        self.refresh_tables()

    def sort_sales(self, e):
        self.sales_sort_ascending = not self.sales_sort_ascending
        col_index = e.column_index
        key = SALE_SORT_KEYS.get(col_index)
        if key:

            def get_sort_val(r):
                val = r.data.get(key)
                if val is None:
                    return "" if isinstance(key, str) else 0
                if isinstance(val, str):
                    return val.lower()
                return val

            self.sales_rows.sort(
                key=get_sort_val, reverse=not self.sales_sort_ascending
            )

        self.sales_table.sort_column_index = col_index
        self.sales_table.sort_ascending = self.sales_sort_ascending
        self.refresh_tables()

    def build_products_tab(self):
        self.products_search = ft.TextField(
            hint_text="Введите поисковый запрос и нажмите Enter...",
            prefix_icon=ft.Icons.SEARCH,
            expand=True,
            on_submit=self.on_product_search,
            border_color="#333333",
        )

        self.products_table = ft.DataTable(
            sort_column_index=0,
            sort_ascending=True,
            column_spacing=20,
            horizontal_margin=10,
            columns=[
                ft.DataColumn(ft.Text("SKU"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Название"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Категория"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Подкатегория"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Бренд"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Модель"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Описание"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Закупка"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Розничная"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Скидка"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Цена со скидкой"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Остаток"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Гарантия"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Рейтинг"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Популярность"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Вес"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Размеры"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Статус"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Совместимость"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Заметки"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Действия")),
            ],
            rows=[],
        )

        return ft.Column(
            expand=True,
            controls=[
                ft.Container(height=10),
                ft.Row([self.products_search]),
                ft.Container(height=10),
                ft.Row(
                    expand=True,
                    scroll=ft.ScrollMode.ALWAYS,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(
                            scroll=ft.ScrollMode.ALWAYS, controls=[self.products_table]
                        )
                    ],
                ),
            ],
        )

    def build_sales_tab(self):
        self.sales_table = ft.DataTable(
            sort_column_index=0,
            sort_ascending=True,
            column_spacing=20,
            horizontal_margin=10,
            columns=[
                ft.DataColumn(ft.Text("Заказ"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("SKU товара"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Кол-во"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Цена за ед."), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Скидка"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Сумма"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Продавец"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Дата"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Тип оплаты"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Статус"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Комментарий"), on_sort=self.sort_sales),
            ],
            rows=[],
        )

        return ft.Column(
            expand=True,
            controls=[
                ft.Container(height=10),
                ft.Row(
                    expand=True,
                    scroll=ft.ScrollMode.ALWAYS,
                    vertical_alignment=ft.CrossAxisAlignment.START,
                    controls=[
                        ft.Column(
                            scroll=ft.ScrollMode.ALWAYS, controls=[self.sales_table]
                        )
                    ],
                ),
            ],
        )

    def create_product_row(self, p):
        sku = p.get("sku", "")
        cat_name = CATEGORIES.get(str(p.get("category_id", "")), {}).get(
            "name", str(p.get("category_id", ""))
        )

        purch_price = f"{float(p.get('purchase_price') if p.get('purchase_price') is not None else 0.0):.2f}"
        retail_price = f"{float(p.get('retail_price') if p.get('retail_price') is not None else 0.0):.2f}"
        discount = (
            f"{float(p.get('discount') if p.get('discount') is not None else 0.0):.2f}"
        )
        price_with_discount = f"{float(p.get('price_with_discount') if p.get('price_with_discount') is not None else 0.0):.2f}"

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(sku, size=12)),
                ft.DataCell(
                    ft.Text(
                        str(p.get("name") if p.get("name") is not None else ""), size=12
                    )
                ),
                ft.DataCell(ft.Text(cat_name, size=12)),
                ft.DataCell(ft.Text(str(p.get("subcategory") or "-"), size=12)),
                ft.DataCell(
                    ft.Text(
                        str(p.get("brand") if p.get("brand") is not None else ""),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(p.get("model") if p.get("model") is not None else ""),
                        size=12,
                    )
                ),
                ft.DataCell(ft.Text(str(p.get("description") or "-"), size=12)),
                ft.DataCell(ft.Text(purch_price, size=12)),
                ft.DataCell(ft.Text(retail_price, size=12)),
                ft.DataCell(ft.Text(discount, size=12)),
                ft.DataCell(ft.Text(price_with_discount, size=12)),
                ft.DataCell(
                    ft.Text(
                        str(p.get("stock") if p.get("stock") is not None else 0),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(
                            p.get("warranty_months")
                            if p.get("warranty_months") is not None
                            else 12
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(p.get("rating") if p.get("rating") is not None else 0.0),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(
                            p.get("popularity")
                            if p.get("popularity") is not None
                            else 0
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(ft.Text(str(p.get("weight_kg") or "-"), size=12)),
                ft.DataCell(ft.Text(str(p.get("dimensions") or "-"), size=12)),
                ft.DataCell(ft.Text(str(p.get("status") or "в наличии"), size=12)),
                ft.DataCell(ft.Text(str(p.get("compatibility") or "-"), size=12)),
                ft.DataCell(ft.Text(str(p.get("notes") or "-"), size=12)),
                ft.DataCell(
                    ft.Row(
                        [
                            ft.IconButton(
                                ft.Icons.EDIT,
                                icon_color=ft.Colors.BLUE_400,
                                icon_size=18,
                                on_click=lambda e: self.open_product_dialog(p),
                            ),
                            ft.IconButton(
                                ft.Icons.DELETE,
                                icon_color=ft.Colors.RED_400,
                                icon_size=18,
                                on_click=lambda e: self.mark_product_deleted(p),
                            ),
                        ],
                        spacing=0,
                    )
                ),
            ]
        )

    def open_dlg(self, dlg):
        if dlg not in self.main_page.overlay:
            self.main_page.overlay.append(dlg)
        dlg.open = True
        self.main_page.update()

    def close_dlg(self, dlg):
        dlg.open = False
        self.main_page.update()

    def open_product_dialog(self, p=None):
        is_new = p is None
        if is_new:
            p = {
                "sku": "Авто",
                "name": "",
                "category_id": 1,
                "subcategory": "",
                "brand": "",
                "model": "",
                "description": "",
                "purchase_price": 0.0,
                "retail_price": 0.0,
                "discount": 0.0,
                "price_with_discount": 0.0,
                "stock": 0,
                "warranty_months": 12,
                "rating": 0.0,
                "popularity": 0,
                "weight_kg": None,
                "dimensions": "",
                "status": "в наличии",
                "compatibility": "",
                "notes": "",
            }

        sku_input = ft.TextField(label="SKU", value=p.get("sku"), read_only=True)
        name_input = ft.TextField(label="Название", value=p.get("name"))

        def on_cat_select(e):
            if is_new:
                sku_input.value = self.generate_sequential_sku(cat_dropdown.value)
                sku_input.update()

        cat_dropdown = ft.Dropdown(
            label="Категория",
            options=[
                ft.dropdown.Option(key=k, text=v["name"]) for k, v in CATEGORIES.items()
            ],
            value=str(p.get("category_id")),
            on_select=on_cat_select,
        )
        if is_new:
            sku_input.value = self.generate_sequential_sku("1")

        subcat_input = ft.TextField(
            label="Подкатегория", value=p.get("subcategory") or ""
        )
        brand_input = ft.TextField(label="Бренд", value=p.get("brand"))
        model_input = ft.TextField(label="Модель", value=p.get("model"))
        desc_input = ft.TextField(
            label="Описание", value=p.get("description") or "", multiline=True
        )

        purch_input = ft.TextField(
            label="Закупочная цена", value=f"{float(p.get('purchase_price', 0.0)):.2f}"
        )
        retail_input = ft.TextField(
            label="Розничная цена", value=f"{float(p.get('retail_price', 0.0)):.2f}"
        )
        disc_input = ft.TextField(
            label="Скидка %", value=f"{float(p.get('discount', 0.0)):.2f}"
        )

        price_with_disc_text = ft.Text(
            f"Цена со скидкой: {float(p.get('price_with_discount', 0.0)):.2f}",
            size=16,
            weight=ft.FontWeight.BOLD,
        )

        def recalc_price(e):
            try:
                r = (
                    float(retail_input.value.replace(",", "."))
                    if retail_input.value
                    else 0.0
                )
                d = (
                    float(disc_input.value.replace(",", "."))
                    if disc_input.value
                    else 0.0
                )
                price_with_disc_text.value = f"Цена со скидкой: {r * (1 - d / 100):.2f}"
                price_with_disc_text.update()
            except ValueError:
                pass

        retail_input.on_change = recalc_price
        disc_input.on_change = recalc_price

        stock_input = ft.TextField(label="Остаток", value=str(p.get("stock")))
        warranty_input = ft.TextField(
            label="Гарантия (мес)", value=str(p.get("warranty_months"))
        )
        rating_input = ft.TextField(label="Рейтинг", value=str(p.get("rating")))
        pop_input = ft.TextField(label="Популярность", value=str(p.get("popularity")))
        weight_input = ft.TextField(
            label="Вес (кг)", value=str(p.get("weight_kg") or "")
        )
        dim_input = ft.TextField(label="Размеры", value=p.get("dimensions") or "")
        status_dropdown = ft.Dropdown(
            label="Статус",
            options=[ft.dropdown.Option(text=st) for st in PRODUCT_STATUSES],
            value=p.get("status", "в наличии"),
        )
        compat_input = ft.TextField(
            label="Совместимость", value=p.get("compatibility") or ""
        )
        notes_input = ft.TextField(label="Заметки", value=p.get("notes") or "")

        def on_save(e):
            try:
                r_val = (
                    float(retail_input.value.replace(",", "."))
                    if retail_input.value
                    else 0.0
                )
                d_val = (
                    float(disc_input.value.replace(",", "."))
                    if disc_input.value
                    else 0.0
                )
                p_with_disc = round(r_val * (1 - d_val / 100), 2)

                p["name"] = name_input.value
                p["category_id"] = int(cat_dropdown.value)
                p["subcategory"] = subcat_input.value or None
                p["brand"] = brand_input.value
                p["model"] = model_input.value
                p["description"] = desc_input.value or None
                p["purchase_price"] = (
                    float(purch_input.value.replace(",", "."))
                    if purch_input.value
                    else 0.0
                )
                p["retail_price"] = r_val
                p["discount"] = d_val
                p["price_with_discount"] = p_with_disc
                p["stock"] = int(stock_input.value) if stock_input.value else 0
                p["warranty_months"] = (
                    int(warranty_input.value) if warranty_input.value else 12
                )
                p["rating"] = (
                    float(rating_input.value.replace(",", "."))
                    if rating_input.value
                    else 0.0
                )
                p["popularity"] = int(pop_input.value) if pop_input.value else 0
                p["weight_kg"] = (
                    float(weight_input.value.replace(",", "."))
                    if weight_input.value
                    else None
                )
                p["dimensions"] = dim_input.value or None
                p["status"] = status_dropdown.value
                p["compatibility"] = compat_input.value or None
                p["notes"] = notes_input.value or None

                if is_new:
                    p["sku"] = sku_input.value
                    self.local_products.append(p)
                    self.pending_changes["products"]["add"].append(p)

                    row = self.create_product_row(p)
                    row.data = p
                    self.products_rows.append(row)
                else:
                    if not any(
                        x.get("sku") == p["sku"]
                        for x in self.pending_changes["products"]["update"]
                    ):
                        self.pending_changes["products"]["update"].append(p)

                    for i, r in enumerate(self.products_rows):
                        if r.data.get("sku") == p["sku"]:
                            updated_row = self.create_product_row(p)
                            updated_row.data = p
                            self.products_rows[i] = updated_row
                            break

                self.close_dlg(dlg)
                self.refresh_tables()
            except ValueError:
                self.show_snack(
                    "Проверьте правильность числовых значений!", ft.Colors.RED_700
                )

        dlg = ft.AlertDialog(
            title=ft.Text(
                "Добавить товар" if is_new else f"Редактировать {p.get('sku')}"
            ),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        sku_input,
                        name_input,
                        cat_dropdown,
                        subcat_input,
                        brand_input,
                        model_input,
                        desc_input,
                        purch_input,
                        retail_input,
                        disc_input,
                        price_with_disc_text,
                        stock_input,
                        warranty_input,
                        rating_input,
                        pop_input,
                        weight_input,
                        dim_input,
                        status_dropdown,
                        compat_input,
                        notes_input,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=15,
                ),
                width=500,
                height=600,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.close_dlg(dlg)),
                ft.ElevatedButton(
                    "Сохранить",
                    bgcolor="#2E2E2E",
                    color=ft.Colors.WHITE,
                    on_click=on_save,
                ),
            ],
        )
        self.open_dlg(dlg)

    def on_close_dialog(self, dlg):
        dlg.open = False
        self.main_page.update()

    def create_sale_row(self, s):
        dt_val = s.get("sale_date", "")
        dt_str = (
            dt_val.split("T")[0]
            if isinstance(dt_val, str)
            else (dt_val.strftime("%Y-%m-%d") if dt_val else "")
        )

        price_per_unit = f"{float(s.get('price_per_unit') if s.get('price_per_unit') is not None else 0.0):.2f}"
        discount = (
            f"{float(s.get('discount') if s.get('discount') is not None else 0.0):.2f}"
        )
        total_amount = f"{float(s.get('total_amount') if s.get('total_amount') is not None else 0.0):.2f}"

        return ft.DataRow(
            cells=[
                ft.DataCell(
                    ft.Text(
                        str(
                            s.get("order_number")
                            if s.get("order_number") is not None
                            else ""
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(
                            s.get("product_id")
                            if s.get("product_id") is not None
                            else ""
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(s.get("quantity") if s.get("quantity") is not None else ""),
                        size=12,
                    )
                ),
                ft.DataCell(ft.Text(price_per_unit, size=12)),
                ft.DataCell(ft.Text(discount, size=12)),
                ft.DataCell(ft.Text(total_amount, size=12)),
                ft.DataCell(
                    ft.Text(
                        str(
                            s.get("seller_name")
                            if s.get("seller_name") is not None
                            else ""
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(ft.Text(dt_str, size=12)),
                ft.DataCell(
                    ft.Text(
                        str(
                            s.get("payment_type")
                            if s.get("payment_type") is not None
                            else ""
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(
                    ft.Text(
                        str(
                            s.get("order_status")
                            if s.get("order_status") is not None
                            else ""
                        ),
                        size=12,
                    )
                ),
                ft.DataCell(ft.Text(str(s.get("comment") or "-"), size=12)),
            ]
        )

    def open_sale_dialog(self):
        order_num = self.generate_sequential_order_number()

        sku_options = [
            ft.dropdown.Option(
                key=p.get("sku"), text=f"{p.get('sku')} - {p.get('name')[:30]}"
            )
            for p in self.local_products
        ]

        price_input = ft.TextField(label="Цена за ед.", value="0.00", read_only=True)
        disc_input = ft.TextField(label="Скидка %", value="0.00", read_only=True)
        amount_input = ft.TextField(label="Сумма", value="0.00", read_only=True)
        qty_input = ft.TextField(label="Количество", value="1")

        def on_prod_select(e):
            prod = next(
                (p for p in self.local_products if p.get("sku") == prod_dropdown.value),
                None,
            )
            if prod:
                disc = float(prod.get("discount", 0.0))
                price = float(prod.get("retail_price", 0.0))
                price_each = round(price * (1 - disc / 100), 2)
                price_input.value = f"{price_each:.2f}"
                disc_input.value = f"{disc:.2f}"

                try:
                    qty = int(qty_input.value) if qty_input.value else 1
                except ValueError:
                    qty = 1

                amount_input.value = f"{price_each * qty:.2f}"
                price_input.update()
                disc_input.update()
                amount_input.update()

        def on_qty_change(e):
            try:
                qty = int(qty_input.value) if qty_input.value else 1
                p_each = float(price_input.value) if price_input.value else 0.0
                amount_input.value = f"{p_each * qty:.2f}"
                amount_input.update()
            except ValueError:
                pass

        prod_dropdown = ft.Dropdown(
            label="Выберите товар", options=sku_options, on_select=on_prod_select
        )
        qty_input.on_change = on_qty_change

        seller_dropdown = ft.Dropdown(
            label="Продавец",
            options=[ft.dropdown.Option(text=emp) for emp in EMPLOYEES],
            value=EMPLOYEES[0],
        )

        payment_dropdown = ft.Dropdown(
            label="Способ оплаты",
            options=[ft.dropdown.Option(text=pt) for pt in PAYMENT_TYPES],
            value="карта",
        )

        status_dropdown = ft.Dropdown(
            label="Статус",
            options=[ft.dropdown.Option(text=st) for st in SALE_STATUSES],
            value="выполнен",
        )

        comment_input = ft.TextField(label="Комментарий")

        def on_save(e):
            if not prod_dropdown.value:
                self.show_snack("Выберите товар!", ft.Colors.RED_700)
                return
            try:
                qty = int(qty_input.value) if qty_input.value else 1
                price_each = float(price_input.value)
                discount = float(disc_input.value)
                total_amount = float(amount_input.value)
            except ValueError:
                self.show_snack("Неверный формат числовых полей!", ft.Colors.RED_700)
                return

            new_s = {
                "order_number": order_num,
                "product_id": prod_dropdown.value,
                "quantity": qty,
                "price_per_unit": price_each,
                "discount": discount,
                "total_amount": total_amount,
                "seller_name": seller_dropdown.value,
                "sale_date": datetime.utcnow().isoformat(),
                "payment_type": payment_dropdown.value,
                "order_status": status_dropdown.value,
                "comment": comment_input.value or None,
            }

            self.local_sales.append(new_s)
            self.pending_changes["sales"]["add"].append(new_s)

            row = self.create_sale_row(new_s)
            row.data = new_s
            self.sales_rows.append(row)

            self.close_dlg(dlg)
            self.refresh_tables()

        dlg = ft.AlertDialog(
            title=ft.Text(f"Добавить продажу {order_num}"),
            content=ft.Container(
                content=ft.Column(
                    controls=[
                        prod_dropdown,
                        qty_input,
                        price_input,
                        disc_input,
                        amount_input,
                        seller_dropdown,
                        payment_dropdown,
                        status_dropdown,
                        comment_input,
                    ],
                    scroll=ft.ScrollMode.AUTO,
                    spacing=15,
                ),
                width=450,
                height=550,
            ),
            actions=[
                ft.TextButton("Отмена", on_click=lambda _: self.close_dlg(dlg)),
                ft.ElevatedButton(
                    "Добавить",
                    bgcolor="#2E2E2E",
                    color=ft.Colors.WHITE,
                    on_click=on_save,
                ),
            ],
        )
        self.open_dlg(dlg)

    def mark_product_deleted(self, p):
        if p.get("sku"):
            self.pending_changes["products"]["delete"].append(p)
        if p in self.local_products:
            self.local_products.remove(p)

        self.products_rows = [row for row in self.products_rows if row.data != p]
        self.refresh_tables()

    def on_product_search(self, e):
        query = self.products_search.value
        threading.Thread(
            target=self._on_product_search_thread, args=(query,), daemon=True
        ).start()

    def _on_product_search_thread(self, query):
        try:
            filtered_products = search_products(query)

            self.products_rows = []
            for p in filtered_products:
                row = self.create_product_row(p)
                row.data = p
                self.products_rows.append(row)

            self.refresh_tables()
        except Exception as ex:
            self.show_snack(f"Ошибка поиска: {str(ex)}", ft.Colors.RED_700)

    def save_all_changes(self, e):
        if getattr(self, "is_saving", False):
            return

        has_changes = (
            len(self.pending_changes["products"]["add"]) > 0
            or len(self.pending_changes["products"]["update"]) > 0
            or len(self.pending_changes["products"]["delete"]) > 0
            or len(self.pending_changes["sales"]["add"]) > 0
        )
        if not has_changes:
            self.show_snack("Нет изменений для сохранения", ft.Colors.GREY_700)
            return

        self.is_saving = True
        e.control.disabled = True
        self.main_page.update()

        threading.Thread(
            target=self._save_all_changes_thread, args=(e,), daemon=True
        ).start()

    def _save_all_changes_thread(self, e):
        try:
            current_db_ts = get_last_update()
            if current_db_ts > self.last_timestamp:
                self.show_snack(
                    "Данные изменены на сервере другими пользователями.",
                    ft.Colors.RED_700,
                )
                return

            added_products_from_server = []
            updated_products_from_server = {}
            added_sales_from_server = []

            with ThreadPoolExecutor(max_workers=10) as executor:
                delete_futures = [
                    executor.submit(delete_product, p["sku"])
                    for p in self.pending_changes["products"]["delete"]
                ]

                add_product_futures = {
                    executor.submit(create_product, p): p
                    for p in self.pending_changes["products"]["add"]
                }

                update_product_futures = {
                    executor.submit(update_product, p["sku"], p): p
                    for p in self.pending_changes["products"]["update"]
                }

                create_sale_futures = {
                    executor.submit(create_sale, s_payload): s
                    for s in self.pending_changes["sales"]["add"]
                    for s_payload in [s.copy()]
                    if s_payload.pop("sale_date", None) or True
                }

                for f in delete_futures:
                    f.result()

                for f, p in add_product_futures.items():
                    res = f.result()
                    if res and isinstance(res, dict):
                        added_products_from_server.append(res)
                    else:
                        added_products_from_server.append(p)

                for f, p in update_product_futures.items():
                    res = f.result()
                    if res and isinstance(res, dict):
                        updated_products_from_server[p["sku"]] = res
                    else:
                        updated_products_from_server[p["sku"]] = p

                for f, s in create_sale_futures.items():
                    res = f.result()
                    if res and isinstance(res, dict):
                        added_sales_from_server.append(res)
                    else:
                        added_sales_from_server.append(s)

            new_db_ts = get_last_update()

            deleted_skus = {
                p["sku"] for p in self.pending_changes["products"]["delete"]
            }
            new_local_products = [
                p for p in self.local_products if p.get("sku") not in deleted_skus
            ]

            for i, p in enumerate(new_local_products):
                sku = p.get("sku")
                if sku in updated_products_from_server:
                    new_local_products[i] = updated_products_from_server[sku]

            added_skus = {p["sku"] for p in self.pending_changes["products"]["add"]}
            new_local_products = [
                p for p in new_local_products if p.get("sku") not in added_skus
            ]
            new_local_products.extend(added_products_from_server)

            self.local_products = new_local_products

            added_sales_orders = {
                s["order_number"] for s in self.pending_changes["sales"]["add"]
            }
            new_local_sales = [
                s
                for s in self.local_sales
                if s.get("order_number") not in added_sales_orders
            ]
            new_local_sales.extend(added_sales_from_server)
            self.local_sales = new_local_sales

            self.pending_changes = {
                "products": {"add": [], "update": [], "delete": []},
                "sales": {"add": []},
            }

            self.last_timestamp = new_db_ts
            api_mod._cached_products = self.local_products
            api_mod._cached_sales = self.local_sales
            api_mod._cached_timestamp = new_db_ts

            for r in self.products_rows:
                sku = r.data.get("sku")
                if sku in updated_products_from_server:
                    r.data = updated_products_from_server[sku]
                for sp in added_products_from_server:
                    if sp.get("sku") == sku:
                        r.data = sp
                        break

            for r in self.sales_rows:
                order_num = r.data.get("order_number")
                for ss in added_sales_from_server:
                    if ss.get("order_number") == order_num:
                        r.data = ss
                        break

            self.main_page.update()
            self.show_snack("Изменения успешно сохранены", ft.Colors.GREEN_700)

        except Exception as ex:
            self.show_snack(f"Ошибка при сохранении: {str(ex)}", ft.Colors.RED_700)

        finally:
            e.control.disabled = False
            self.is_saving = False
            self.main_page.update()

    def show_snack(self, text, color):
        snack = ft.SnackBar(content=ft.Text(text, color=ft.Colors.WHITE), bgcolor=color)
        try:
            if hasattr(self.main_page, "show_dialog"):
                self.main_page.show_dialog(snack)
            elif hasattr(self.main_page, "open"):
                self.main_page.open(snack)
            else:
                self.main_page.snack_bar = snack
                snack.open = True
                self.main_page.update()
        except Exception as ex:
            print(f"Failed to show SnackBar: {ex}")


def get_table_view(page: ft.Page):
    return TableView(page)
