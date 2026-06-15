import flet as ft


def get_about_view(page: ft.Page):
    return ft.Container(
        expand=True,
        padding=30,
        content=ft.Column(
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "DNS 2", size=40, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE
                ),
                ft.Text(
                    "Если DNS такой крутой, почему нет DNS 2?",
                    size=16,
                    color=ft.Colors.GREY_400,
                ),
                ft.Divider(height=40, color=ft.Colors.TRANSPARENT),
                ft.Text("Автор: Мещанюк В.С.", size=20, color=ft.Colors.WHITE),
                ft.Divider(height=20, color=ft.Colors.TRANSPARENT),
                ft.TextButton(
                    "GitHub проекта",
                    icon=ft.Icons.CODE,
                    on_click=lambda _: page.launch_url("https://github.com"),
                ),
                ft.TextButton(
                    "Сайт приложения",
                    icon=ft.Icons.WEB,
                    on_click=lambda _: page.launch_url("http://localhost"),
                ),
            ],
        ),
    )
