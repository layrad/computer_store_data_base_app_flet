import flet as ft
from views import get_table_view, get_reports_view, get_about_view


def main(page: ft.Page):
    page.title = "DNS 2"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.window_min_width = 400
    page.window_min_height = 600

    content_area = ft.Container(
        expand=True, padding=ft.Padding(left=15, top=60, right=15, bottom=15)
    )

    def change_route(e):
        index = e.control.selected_index
        content_area.content = None

        if index == 0:
            content_area.content = get_table_view(page)
        elif index == 1:
            content_area.content = get_reports_view(page)
        elif index == 2:
            content_area.content = get_about_view(page)

        menu_container.visible = False
        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        bgcolor="#121212",
        extended=False,
        min_width=100,
        label_type=ft.NavigationRailLabelType.ALL,
        leading=ft.Container(height=50),
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.STORAGE, label="База"),
            ft.NavigationRailDestination(icon=ft.Icons.ANALYTICS, label="Отчеты"),
            ft.NavigationRailDestination(icon=ft.Icons.INFO, label="О нас"),
        ],
        on_change=change_route,
    )

    menu_container = ft.Container(
        content=rail,
        left=0,
        top=0,
        bottom=0,
        width=100,
        visible=False,
        shadow=ft.BoxShadow(blur_radius=15, color="#66000000", offset=ft.Offset(3, 0)),
    )

    def toggle_menu(e):
        menu_container.visible = not menu_container.visible
        page.update()

    menu_button = ft.IconButton(
        icon=ft.Icons.MENU,
        icon_color=ft.Colors.WHITE,
        icon_size=28,
        on_click=toggle_menu,
        left=10,
        top=10,
    )

    page.add(
        ft.Stack(
            [
                content_area,
                menu_container,
                menu_button,
            ],
            expand=True,
        )
    )

    content_area.content = get_table_view(page)
    page.update()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
