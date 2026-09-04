EDITION_FREE = "free"
EDITION_INTERNAL = "internal"


# ---------------------------------
# 現在のエディション
# ---------------------------------
#
# 公開Free版を作るとき:
# CURRENT_EDITION = EDITION_FREE
#
# 仲間内/Internal版を作るとき:
# CURRENT_EDITION = EDITION_INTERNAL
#
CURRENT_EDITION = EDITION_FREE


# ---------------------------------
# エディション別機能
# ---------------------------------
FREE_MAX_PAGES = 5


def is_free_edition():
    return CURRENT_EDITION == EDITION_FREE


def is_internal_edition():
    return CURRENT_EDITION == EDITION_INTERNAL


def get_max_pages():
    if is_free_edition():
        return FREE_MAX_PAGES

    return None


def is_multi_page_export_enabled():
    return is_internal_edition()
