import flet as ft
from views import get_table_view, get_reports_view, get_about_view


def main(page: ft.Page):
    page.title = "DNS 2"
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#121212"
    page.window_min_width = 400
    page.window_min_height = 600

    content_area = ft.Container(expand=True)

    def change_route(e):
        index = e.control.selected_index
        content_area.content = None

        if index == 0:
            content_area.content = get_table_view(page)
        elif index == 1:
            content_area.content = get_reports_view(page)
        elif index == 2:
            content_area.content = get_about_view(page)

        page.update()

    rail = ft.NavigationRail(
        selected_index=0,
        bgcolor="#121212",
        destinations=[
            ft.NavigationRailDestination(icon=ft.Icons.STORAGE, label="База"),
            ft.NavigationRailDestination(icon=ft.Icons.ANALYTICS, label="Отчеты"),
            ft.NavigationRailDestination(icon=ft.Icons.INFO, label="О нас"),
        ],
        on_change=change_route,
    )

    def adjust_sidebar():
        if page.width < 600:
            rail.min_width = 56
            rail.extended = False
            rail.label_type = ft.NavigationRailLabelType.NONE
        else:
            rail.min_width = 100
            rail.extended = False
            rail.label_type = ft.NavigationRailLabelType.ALL

    def on_resize(e):
        adjust_sidebar()
        page.update()

    page.on_resize = on_resize
    adjust_sidebar()

    page.add(
        ft.Row(
            [
                rail,
                ft.VerticalDivider(width=1, color="#222222"),
                content_area,
            ],
            expand=True,
        )
    )

    content_area.content = get_table_view(page)
    page.update()


if __name__ == "__main__":
    ft.run(main, assets_dir="assets")
