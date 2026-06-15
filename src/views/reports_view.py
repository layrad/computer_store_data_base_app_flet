import flet as ft


def get_reports_view(page: ft.Page):
    options = [
        "Отчет по продажам за месяц",
        "Остатки на складе",
        "Топ продаваемых товаров",
        "Товары с низким запасом",
        "Выручка по категориям",
        "Свой вариант...",
    ]

    dropdown = ft.Dropdown(
        options=[ft.dropdown.Option(text=opt) for opt in options],
        width=400,
        hint_text="Выберите тип отчета",
        border_color="#333333",
        color=ft.Colors.WHITE,
    )

    custom_input = ft.TextField(
        visible=False,
        width=400,
        hint_text="Введите свой запрос...",
        border_color="#333333",
    )

    report_output = ft.TextField(
        multiline=True,
        expand=True,
        read_only=True,
        border_color="#222222",
        color=ft.Colors.GREY_300,
        text_size=14,
    )

    def on_dropdown_change(e):
        custom_input.visible = dropdown.value == "Свой вариант..."
        custom_input.update()

    dropdown.on_select = on_dropdown_change

    def on_generate(e):
        pass

    return ft.Container(
        expand=True,
        padding=20,
        content=ft.Column(
            controls=[
                ft.Text("Генерация отчетов", size=24, weight=ft.FontWeight.BOLD),
                dropdown,
                custom_input,
                ft.ElevatedButton(
                    "Составить отчет",
                    icon=ft.Icons.ANALYTICS,
                    bgcolor="#2E2E2E",
                    color=ft.Colors.WHITE,
                    on_click=on_generate,
                ),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                report_output,
            ]
        ),
    )
