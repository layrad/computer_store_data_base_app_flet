import flet as ft
from backend.api import (
    get_products,
    get_sales,
    get_last_update,
    create_product,
    update_product,
    delete_product,
    create_sale,
    search_products,
)

CATEGORIES = {
    "1": {"name": "Процессоры", "prefix": "PRC"},
    "2": {"name": "Видеокарты", "prefix": "VGA"},
    "3": {"name": "Оперативная память", "prefix": "RAM"},
    "4": {"name": "Накопители SSD", "prefix": "SSD"},
    "5": {"name": "Жесткие диски", "prefix": "HDD"},
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


class TableView(ft.Container):
    def __init__(self, page: ft.Page):
        super().__init__()
        self.main_page = page
        self.expand = True
        self.padding = 20
        self.last_timestamp = 0.0

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

        self.setup_empty_rows_controls()

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
                        ft.ElevatedButton(
                            "Сохранить изменения",
                            icon=ft.Icons.SAVE,
                            bgcolor="#2E2E2E",
                            color=ft.Colors.WHITE,
                            on_click=self.save_all_changes,
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
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

    def setup_empty_rows_controls(self):
        self.p_sku_field = ft.TextField(
            value="Выберите категорию",
            read_only=True,
            border=ft.InputBorder.NONE,
            text_size=13,
            color=ft.Colors.GREY_500,
            width=150,
        )
        self.p_name_field = ft.TextField(
            hint_text="Название...", border=ft.InputBorder.NONE, text_size=13, width=220
        )
        self.p_price_field = ft.TextField(
            hint_text="Цена...", border=ft.InputBorder.NONE, text_size=13, width=80
        )
        self.p_stock_field = ft.TextField(
            hint_text="Кол-во...", border=ft.InputBorder.NONE, text_size=13, width=60
        )

        def on_category_select(e):
            cat_id = self.p_category_dropdown.value
            if cat_id:
                self.p_sku_field.value = self.generate_sequential_sku(cat_id)
                self.p_sku_field.update()

        self.p_category_dropdown = ft.Dropdown(
            options=[
                ft.dropdown.Option(key=k, text=v["name"]) for k, v in CATEGORIES.items()
            ],
            border=ft.InputBorder.NONE,
            on_select=on_category_select,
            width=200,
            text_size=13,
        )

        self.empty_product_row = ft.DataRow(
            cells=[
                ft.DataCell(self.p_sku_field),
                ft.DataCell(self.p_name_field),
                ft.DataCell(self.p_category_dropdown),
                ft.DataCell(self.p_price_field),
                ft.DataCell(self.p_stock_field),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.ADD_CIRCLE_OUTLINE,
                        icon_color=ft.Colors.GREEN_600,
                        on_click=self.add_product_click,
                    )
                ),
            ]
        )

        self.s_order_field = ft.TextField(
            value="ЗК-1000",
            read_only=True,
            border=ft.InputBorder.NONE,
            text_size=13,
            color=ft.Colors.GREY_500,
            width=120,
        )
        self.s_product_field = ft.TextField(
            hint_text="ID Тов...", border=ft.InputBorder.NONE, text_size=13, width=80
        )
        self.s_qty_field = ft.TextField(
            hint_text="Кол-во...", border=ft.InputBorder.NONE, text_size=13, width=60
        )
        self.s_amount_field = ft.TextField(
            hint_text="Сумма...", border=ft.InputBorder.NONE, text_size=13, width=80
        )
        self.s_status_field = ft.TextField(
            value="выполнен", border=ft.InputBorder.NONE, text_size=13, width=100
        )

        self.empty_sale_row = ft.DataRow(
            cells=[
                ft.DataCell(self.s_order_field),
                ft.DataCell(self.s_product_field),
                ft.DataCell(self.s_qty_field),
                ft.DataCell(self.s_amount_field),
                ft.DataCell(
                    ft.Row(
                        [
                            self.s_status_field,
                            ft.IconButton(
                                ft.Icons.ADD_CIRCLE_OUTLINE,
                                icon_color=ft.Colors.GREEN_600,
                                on_click=self.add_sale_click,
                            ),
                        ]
                    )
                ),
            ]
        )

    def clear_empty_product_inputs(self):
        self.p_sku_field.value = "Выберите категорию"
        self.p_name_field.value = ""
        self.p_category_dropdown.value = None
        self.p_price_field.value = ""
        self.p_stock_field.value = ""

    def clear_empty_sale_inputs(self):
        self.s_product_field.value = ""
        self.s_qty_field.value = ""
        self.s_amount_field.value = ""
        self.s_status_field.value = "выполнен"

    def did_mount(self):
        self.load_data()

    def load_data(self):
        self.last_timestamp = get_last_update()
        self.local_products = get_products()
        self.local_sales = get_sales()
        self.pending_changes = {
            "products": {"add": [], "update": [], "delete": []},
            "sales": {"add": []},
        }

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

    def refresh_tables(self):
        self.s_order_field.value = self.generate_sequential_order_number()

        self.products_table.rows = self.products_rows + [self.empty_product_row]
        self.sales_table.rows = self.sales_rows + [self.empty_sale_row]
        self.main_page.update()

    def sort_products(self, e):
        self.products_sort_ascending = not self.products_sort_ascending
        col_index = e.column_index

        if col_index == 0:
            self.products_rows.sort(
                key=lambda r: str(r.data.get("sku", "")),
                reverse=not self.products_sort_ascending,
            )
        elif col_index == 1:
            self.products_rows.sort(
                key=lambda r: str(r.data.get("name", "")).lower(),
                reverse=not self.products_sort_ascending,
            )
        elif col_index == 2:
            self.products_rows.sort(
                key=lambda r: int(r.data.get("category_id", 0)),
                reverse=not self.products_sort_ascending,
            )
        elif col_index == 3:
            self.products_rows.sort(
                key=lambda r: float(r.data.get("retail_price", 0.0)),
                reverse=not self.products_sort_ascending,
            )
        elif col_index == 4:
            self.products_rows.sort(
                key=lambda r: int(r.data.get("stock", 0)),
                reverse=not self.products_sort_ascending,
            )

        self.products_table.sort_column_index = col_index
        self.products_table.sort_ascending = self.products_sort_ascending
        self.refresh_tables()

    def sort_sales(self, e):
        self.sales_sort_ascending = not self.sales_sort_ascending
        col_index = e.column_index

        if col_index == 0:
            self.sales_rows.sort(
                key=lambda r: str(r.data.get("order_number", "")),
                reverse=not self.sales_sort_ascending,
            )
        elif col_index == 1:
            self.sales_rows.sort(
                key=lambda r: int(r.data.get("product_id", 0)),
                reverse=not self.sales_sort_ascending,
            )
        elif col_index == 2:
            self.sales_rows.sort(
                key=lambda r: int(r.data.get("quantity", 0)),
                reverse=not self.sales_sort_ascending,
            )
        elif col_index == 3:
            self.sales_rows.sort(
                key=lambda r: float(r.data.get("total_amount", 0.0)),
                reverse=not self.sales_sort_ascending,
            )
        elif col_index == 4:
            self.sales_rows.sort(
                key=lambda r: str(r.data.get("order_status", "")).lower(),
                reverse=not self.sales_sort_ascending,
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
                ft.DataColumn(ft.Text("Цена"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Остаток"), on_sort=self.sort_products),
                ft.DataColumn(ft.Text("Удалить")),
            ],
            rows=[],
        )

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                ft.Container(height=10),
                ft.Row([self.products_search]),
                ft.Row(scroll=ft.ScrollMode.ADAPTIVE, controls=[self.products_table]),
            ],
        )

    def build_sales_tab(self):
        self.sales_table = ft.DataTable(
            sort_column_index=0,
            sort_ascending=True,
            column_spacing=20,
            horizontal_margin=10,
            columns=[
                ft.DataColumn(ft.Text("Номер заказа"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("ID Товара"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Количество"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Сумма"), on_sort=self.sort_sales),
                ft.DataColumn(ft.Text("Статус"), on_sort=self.sort_sales),
            ],
            rows=[],
        )

        return ft.Column(
            expand=True,
            scroll=ft.ScrollMode.ADAPTIVE,
            controls=[
                ft.Container(height=10),
                ft.Row(scroll=ft.ScrollMode.ADAPTIVE, controls=[self.sales_table]),
            ],
        )

    def on_product_field_change(self, p, field, value, control: ft.TextField):
        if field == "retail_price":
            try:
                p["retail_price"] = float(value.replace(",", ".")) if value else 0.0
                control.border = ft.InputBorder.NONE
                control.border_color = None
                control.update()
            except ValueError:
                control.border = ft.InputBorder.OUTLINE
                control.border_color = ft.Colors.RED_700
                control.update()
                self.show_snack("Ошибка! Цена должна быть числом.", ft.Colors.RED_900)
        elif field == "stock":
            try:
                p["stock"] = int(value) if value else 0
                control.border = ft.InputBorder.NONE
                control.border_color = None
                control.update()
            except ValueError:
                control.border = ft.InputBorder.OUTLINE
                control.border_color = ft.Colors.RED_700
                control.update()
                self.show_snack(
                    "Ошибка! Остаток должен быть целым числом.", ft.Colors.RED_900
                )
        else:
            p[field] = value

        if p.get("id"):
            if p not in self.pending_changes["products"]["update"]:
                self.pending_changes["products"]["update"].append(p)

    def create_product_row(self, p):
        cat_name = CATEGORIES.get(str(p.get("category_id", "")), {}).get(
            "name", str(p.get("category_id", ""))
        )

        name_field = ft.TextField(
            value=str(p.get("name", "")),
            border=ft.InputBorder.NONE,
            text_size=13,
            height=30,
            width=220,
            on_change=lambda e: self.on_product_field_change(
                p, "name", name_field.value, name_field
            ),
        )
        price_field = ft.TextField(
            value=str(p.get("retail_price", "")),
            border=ft.InputBorder.NONE,
            text_size=13,
            height=30,
            width=80,
            on_change=lambda e: self.on_product_field_change(
                p, "retail_price", price_field.value, price_field
            ),
        )
        stock_field = ft.TextField(
            value=str(p.get("stock", "")),
            border=ft.InputBorder.NONE,
            text_size=13,
            height=30,
            width=60,
            on_change=lambda e: self.on_product_field_change(
                p, "stock", stock_field.value, stock_field
            ),
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(str(p.get("sku", "")), size=13)),
                ft.DataCell(name_field),
                ft.DataCell(ft.Text(cat_name, size=13)),
                ft.DataCell(price_field),
                ft.DataCell(stock_field),
                ft.DataCell(
                    ft.IconButton(
                        ft.Icons.DELETE,
                        icon_color=ft.Colors.GREY_600,
                        on_click=lambda e: self.mark_product_deleted(p),
                    )
                ),
            ]
        )

    def add_product_click(self, e):
        if not self.p_name_field.value or not self.p_category_dropdown.value:
            self.show_snack("Заполните название и категорию товара!", ft.Colors.RED_700)
            return
        try:
            retail_price = (
                float(self.p_price_field.value.replace(",", "."))
                if self.p_price_field.value
                else 0.0
            )
            stock = int(self.p_stock_field.value) if self.p_stock_field.value else 0
        except ValueError:
            self.show_snack("Неверный формат цены или остатка!", ft.Colors.RED_700)
            return

        new_p = {
            "id": None,
            "sku": self.p_sku_field.value,
            "name": self.p_name_field.value,
            "category_id": int(self.p_category_dropdown.value),
            "brand": "Brand",
            "model": "Model",
            "purchase_price": retail_price * 0.7,
            "retail_price": retail_price,
            "stock": stock,
        }

        self.local_products.append(new_p)
        self.pending_changes["products"]["add"].append(new_p)

        new_row = self.create_product_row(new_p)
        new_row.data = new_p
        self.products_rows.append(new_row)

        self.clear_empty_product_inputs()
        self.refresh_tables()

    def create_sale_row(self, s):
        def go_to_product(e):
            self.tabs.selected_index = 0
            self.products_search.value = str(s.get("product_id", ""))
            self.main_page.update()

        product_id_btn = ft.TextButton(
            content=ft.Text(
                str(s.get("product_id", "")),
                size=13,
                weight=ft.FontWeight.NORMAL,
                color=ft.Colors.GREY_300,
            ),
            on_click=go_to_product,
        )

        return ft.DataRow(
            cells=[
                ft.DataCell(ft.Text(str(s.get("order_number", "")), size=13)),
                ft.DataCell(product_id_btn),
                ft.DataCell(ft.Text(str(s.get("quantity", "")), size=13)),
                ft.DataCell(ft.Text(str(s.get("total_amount", "")), size=13)),
                ft.DataCell(ft.Text(str(s.get("order_status", "")), size=13)),
            ]
        )

    def add_sale_click(self, e):
        if not self.s_product_field.value:
            self.show_snack("Заполните ID товара!", ft.Colors.RED_700)
            return
        try:
            prod_id = int(self.s_product_field.value)
            qty = int(self.s_qty_field.value) if self.s_qty_field.value else 1
            amount = (
                float(self.s_amount_field.value.replace(",", "."))
                if self.s_amount_field.value
                else 0.0
            )
        except ValueError:
            self.show_snack(
                "Неверный формат ID, количества или суммы!", ft.Colors.RED_700
            )
            return

        new_s = {
            "id": None,
            "order_number": self.s_order_field.value,
            "product_id": prod_id,
            "quantity": qty,
            "price_per_unit": amount / qty if qty > 0 else amount,
            "total_amount": amount,
            "seller_name": "System",
            "payment_type": "Cash",
            "order_status": self.s_status_field.value or "выполнен",
        }

        self.local_sales.append(new_s)
        self.pending_changes["sales"]["add"].append(new_s)

        new_row = self.create_sale_row(new_s)
        new_row.data = new_s
        self.sales_rows.append(new_row)

        self.clear_empty_sale_inputs()
        self.refresh_tables()

    def mark_product_deleted(self, p):
        if p.get("id"):
            self.pending_changes["products"]["delete"].append(p)
        if p in self.local_products:
            self.local_products.remove(p)

        self.products_rows = [row for row in self.products_rows if row.data != p]
        self.refresh_tables()

    def on_product_search(self, e):
        query = self.products_search.value
        filtered_products = search_products(query)

        self.products_rows = []
        for p in filtered_products:
            row = self.create_product_row(p)
            row.data = p
            self.products_rows.append(row)

        self.refresh_tables()

    def save_all_changes(self, e):
        current_db_ts = get_last_update()
        if current_db_ts > self.last_timestamp:
            self.show_snack(
                "Исходные данные были изменены на сервере другим пользователем. Обновите страницу.",
                ft.Colors.RED_700,
            )
            return

        for p in self.pending_changes["products"]["add"]:
            create_product(p)
        for p in self.pending_changes["products"]["update"]:
            update_product(p["id"], p)
        for p in self.pending_changes["products"]["delete"]:
            delete_product(p["id"])

        for s in self.pending_changes["sales"]["add"]:
            create_sale(s)

        self.show_snack("Изменения успешно сохранены", ft.Colors.GREY_700)
        self.load_data()

    def show_snack(self, text, color):
        snack = ft.SnackBar(ft.Text(text, color=ft.Colors.WHITE), bgcolor=color)
        try:
            self.main_page.show_dialog(snack)
        except AttributeError:
            try:
                self.main_page.open(snack)
            except AttributeError:
                self.main_page.snack_bar = snack
                snack.open = True
                self.main_page.update()


def get_table_view(page: ft.Page):
    return TableView(page)
