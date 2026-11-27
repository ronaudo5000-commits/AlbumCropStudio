
class UndoHistory:
    """操作の実行順序とUndo・Redo履歴を管理する。"""

    def __init__(self, max_entries=30):
        self.max_entries = max_entries
        self.undo_stack = []
        self.redo_stack = []

    def record(self, entry):
        """新しい操作を記録する。"""
        self.undo_stack.append(entry)

        if len(self.undo_stack) > self.max_entries:
            self.undo_stack.pop(0)

        self.redo_stack.clear()

    def peek_undo(self):
        """次に取り消す操作を取得する（取り出さない）。"""
        if not self.undo_stack:
            return None

        return self.undo_stack[-1]

    def peek_redo(self):
        """次にやり直す操作を取得する（取り出さない）。"""
        if not self.redo_stack:
            return None

        return self.redo_stack[-1]

    def commit_undo(self):
        """取り消しが成功した操作をRedo履歴へ移す。"""
        if not self.undo_stack:
            return None

        entry = self.undo_stack.pop()
        self.redo_stack.append(entry)
        return entry

    def commit_redo(self):
        """やり直しが成功した操作をUndo履歴へ戻す。"""
        if not self.redo_stack:
            return None

        entry = self.redo_stack.pop()
        self.undo_stack.append(entry)
        return entry

    def clear(self):
        """すべての操作履歴を消去する。"""
        self.undo_stack.clear()
        self.redo_stack.clear()
