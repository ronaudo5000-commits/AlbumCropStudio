from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class UndoCommand:
    """取り消し可能な操作を表すクラス。"""

    undo_callback: Callable[[], None]
    description: str = ""

    def undo(self) -> None:
        """登録された取り消し処理を実行する。"""
        self.undo_callback()


class UndoManager:
    """アプリケーション内のUndo履歴を管理するクラス。"""

    def __init__(self, max_history: int = 100) -> None:
        self._undo_stack: list[UndoCommand] = []
        self._max_history = max_history

    def push(
        self,
        undo_callback: Callable[[], None],
        description: str = "",
    ) -> None:
        """取り消し可能な操作を履歴へ追加する。"""

        command = UndoCommand(
            undo_callback=undo_callback,
            description=description,
        )

        self._undo_stack.append(command)

        if len(self._undo_stack) > self._max_history:
            self._undo_stack.pop(0)

    def undo(self) -> bool:
        """直前の操作を取り消す。成功した場合はTrueを返す。"""

        if not self.can_undo():
            return False

        command = self._undo_stack.pop()
        command.undo()

        return True

    def can_undo(self) -> bool:
        """取り消せる操作が存在するか確認する。"""
        return bool(self._undo_stack)

    def clear(self) -> None:
        """すべてのUndo履歴を削除する。"""
        self._undo_stack.clear()

    def undo_description(self) -> str:
        """次に取り消される操作の説明を返す。"""

        if not self.can_undo():
            return ""

        return self._undo_stack[-1].description