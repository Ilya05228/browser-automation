"""PySide6 GUI: профили в таблице, CRUD, экспорт/импорт, статус запуска."""

import json
from pathlib import Path

from PySide6.QtCore import Qt, QThread, QTimer, Signal
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from browser_automation.camoufox_launcher import CamoufoxLauncher
from browser_automation.profile_repository import ProfileRepository
from browser_automation.value_objects import CamoufoxSettings, Profile, ProxyConfig


DEFAULT_PROFILES_PATH = Path.home() / ".config" / "browser-automation" / "profiles.json"

STATUS_RUNNING = "запущен"
STATUS_STOPPED = "не запущен"


class LaunchWorker(QThread):
    """Запуск Camoufox в отдельном потоке — избегает 'Sync API inside asyncio loop'."""

    finished = Signal(str, object)  # profile_id, launcher
    error = Signal(str, str)  # profile_name, error_msg

    def __init__(self, profile_id: str, profile: Profile) -> None:
        super().__init__()
        self.profile_id = profile_id
        self.profile = profile

    def run(self) -> None:
        try:
            launcher = CamoufoxLauncher(profile=self.profile)
            launcher.start()
            self.finished.emit(self.profile_id, launcher)
        except Exception as e:
            self.error.emit(self.profile.name, str(e))


class ProfileEditDialog(QDialog):
    """Диалог создания/редактирования профиля."""

    def __init__(
        self,
        parent: QWidget | None = None,
        profile: Profile | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Редактировать профиль" if profile else "Новый профиль")
        self._profile = profile
        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Название профиля")
        name_label = QLabel("Название <span style='color:red'>*</span>")
        name_label.setTextFormat(Qt.TextFormat.RichText)
        form.addRow(name_label, self.name_edit)

        self.vless_edit = QTextEdit()
        self.vless_edit.setPlaceholderText(
            "Оставьте пустым — прокси не будет. Если укажете VLESS, используется 127.0.0.1:10808 автоматически."
        )
        self.vless_edit.setMaximumHeight(80)
        form.addRow("VLESS:", self.vless_edit)

        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText("Оставьте пустым — при VLESS подставится 127.0.0.1")
        form.addRow("Прокси host:", self.proxy_host)
        self.proxy_port = QLineEdit()
        self.proxy_port.setPlaceholderText("Оставьте пустым — при VLESS подставится 10808")
        form.addRow("Прокси port:", self.proxy_port)

        layout.addLayout(form)

        if profile:
            self.name_edit.setText(profile.name)
            if profile.vless_raw:
                self.vless_edit.setPlainText(profile.vless_raw)
            if profile.proxy_config:
                self.proxy_host.setText(profile.proxy_config.host)
                self.proxy_port.setText(str(profile.proxy_config.port))

        bb = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        layout.addWidget(bb)

    def profile(self) -> Profile:
        name = self.name_edit.text().strip() or "Без имени"
        vless = self.vless_edit.toPlainText().strip() or None
        proxy = None
        if not vless:
            try:
                host = self.proxy_host.text().strip() or "127.0.0.1"
                port = int(self.proxy_port.text().strip() or "10808")
                proxy = ProxyConfig(host=host, port=port)
            except ValueError:
                pass
        return Profile(
            id=self._profile.id if self._profile else "",
            name=name,
            vless_raw=vless,
            proxy_config=proxy,
            camoufox_settings=CamoufoxSettings(),
        )


class MainWindow(QMainWindow):
    """Главное окно: таблица профилей, панель действий."""

    def __init__(self, profiles_path: Path | str = DEFAULT_PROFILES_PATH) -> None:
        super().__init__()
        self.setWindowTitle("Browser Automation — Профили")
        self.setMinimumSize(600, 450)
        self.resize(800, 550)
        self._repo = ProfileRepository(profiles_path)
        self._launchers: dict[str, CamoufoxLauncher] = {}
        self._launch_workers: list[LaunchWorker] = []

        # Таймер: проверка, не закрыл ли пользователь браузер вручную
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_browsers_closed)
        self._status_timer.start(2000)  # каждые 2 сек

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Название", "ID", "Статус"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.itemSelectionChanged.connect(self._on_selection_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        layout.addWidget(self.table)

        # Панель действий
        panel = QHBoxLayout()
        panel.addStretch()

        create_btn = QPushButton("➕ Создать")
        create_btn.clicked.connect(self._create_profile)
        panel.addWidget(create_btn)

        edit_btn = QPushButton("✏️ Изменить")
        edit_btn.clicked.connect(self._edit_selected)
        self._edit_btn = edit_btn
        panel.addWidget(edit_btn)

        dup_btn = QPushButton("📋 Дублировать")
        dup_btn.clicked.connect(self._duplicate_selected)
        self._dup_btn = dup_btn
        panel.addWidget(dup_btn)

        export_clip_btn = QPushButton("📤 Экспорт в буфер")
        export_clip_btn.clicked.connect(self._export_to_clipboard)
        self._export_clip_btn = export_clip_btn
        panel.addWidget(export_clip_btn)

        export_btn = QPushButton("📤 Экспорт в файл")
        export_btn.clicked.connect(self._export_to_file)
        self._export_btn = export_btn
        panel.addWidget(export_btn)

        import_btn = QPushButton("📥 Импорт из файла")
        import_btn.clicked.connect(self._import_from_file)
        panel.addWidget(import_btn)

        import_clip_btn = QPushButton("📥 Импорт из буфера")
        import_clip_btn.clicked.connect(self._import_from_clipboard)
        panel.addWidget(import_clip_btn)

        delete_btn = QPushButton("🗑️ Удалить")
        delete_btn.clicked.connect(self._delete_selected)
        self._delete_btn = delete_btn
        panel.addWidget(delete_btn)

        launch_btn = QPushButton("🚀 Запуск")
        launch_btn.clicked.connect(self._launch_selected)
        launch_btn.setStyleSheet("background: #2e7d32; color: white; font-weight: bold;")
        self._launch_btn = launch_btn
        panel.addWidget(launch_btn)

        stop_btn = QPushButton("⏹️ Завершить")
        stop_btn.clicked.connect(self._stop_selected)
        stop_btn.setStyleSheet("background: #c62828; color: white;")
        self._stop_btn = stop_btn
        panel.addWidget(stop_btn)

        layout.addLayout(panel)
        self._refresh_table()
        self._on_selection_changed()

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        for p in self._repo.list_all():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p.name))
            self.table.setItem(row, 1, QTableWidgetItem(p.id[:12] + "…"))
            status = STATUS_RUNNING if p.id in self._launchers else STATUS_STOPPED
            status_item = QTableWidgetItem(status)
            status_item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.table.setItem(row, 2, status_item)
            self.table.setRowHeight(row, 28)

    def _selected_ids(self) -> list[str]:
        ids = []
        for item in self.table.selectedItems():
            row = item.row()
            status_cell = self.table.item(row, 2)
            if status_cell:
                pid = status_cell.data(Qt.ItemDataRole.UserRole)
                if pid and pid not in ids:
                    ids.append(pid)
        return ids

    def _on_selection_changed(self) -> None:
        ids = self._selected_ids()
        has_sel = len(ids) > 0
        single_sel = len(ids) == 1
        self._edit_btn.setEnabled(single_sel)
        self._dup_btn.setEnabled(has_sel)
        self._export_clip_btn.setEnabled(has_sel)
        self._export_btn.setEnabled(has_sel)
        self._delete_btn.setEnabled(has_sel)
        self._launch_btn.setEnabled(has_sel)
        self._stop_btn.setEnabled(has_sel)

    def _on_cell_double_clicked(self, row: int, _col: int) -> None:
        status_cell = self.table.item(row, 2)
        if status_cell:
            pid = status_cell.data(Qt.ItemDataRole.UserRole)
            if pid:
                self._edit_profile(pid)

    def _edit_selected(self) -> None:
        ids = self._selected_ids()
        if len(ids) == 1:
            self._edit_profile(ids[0])

    def _create_profile(self) -> None:
        dlg = ProfileEditDialog(self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            p = dlg.profile()
            self._repo.create(p)
            self._refresh_table()
            QMessageBox.information(self, "Готово", f"Профиль «{p.name}» создан.")

    def _edit_profile(self, profile_id: str) -> None:
        p = self._repo.get(profile_id)
        if not p:
            return
        dlg = ProfileEditDialog(self, profile=p)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            new_p = dlg.profile()
            new_p = Profile(
                id=p.id,
                name=new_p.name,
                vless_raw=new_p.vless_raw,
                proxy_config=new_p.proxy_config,
                camoufox_settings=new_p.camoufox_settings,
            )
            self._repo.update(new_p)
            self._refresh_table()
            QMessageBox.information(self, "Готово", f"Профиль «{new_p.name}» обновлён.")

    def _duplicate_selected(self) -> None:
        for pid in self._selected_ids():
            new_p = self._repo.copy(pid)
            if new_p:
                QMessageBox.information(self, "Готово", f"Скопировано как «{new_p.name}».")
        self._refresh_table()

    def _export_to_clipboard(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        data = [self._repo.export_profile(pid) for pid in ids]
        text = json.dumps(data, ensure_ascii=False, indent=2)
        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self, "Готово", f"В буфер скопировано {len(data)} профиль(ей)."
        )

    def _export_to_file(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        data = [self._repo.export_profile(pid) for pid in ids]
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт", "", "JSON (*.json)")
        if not path:
            return
        try:
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2))
            QMessageBox.information(self, "Готово", f"Экспортировано в {path}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка", str(e))

    def _import_from_file(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Импорт", "", "JSON (*.json)")
        if not path:
            return
        try:
            raw = Path(path).read_text()
            data = json.loads(raw)
            if isinstance(data, list):
                for d in data:
                    self._repo.import_profile(d)
            else:
                self._repo.import_profile(data)
            self._refresh_table()
            QMessageBox.information(self, "Готово", "Импорт выполнен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def _import_from_clipboard(self) -> None:
        text = QApplication.clipboard().text()
        if not text.strip():
            QMessageBox.warning(self, "Ошибка", "Буфер обмена пуст.")
            return
        try:
            data = json.loads(text)
            if isinstance(data, list):
                for d in data:
                    self._repo.import_profile(d)
            else:
                self._repo.import_profile(data)
            self._refresh_table()
            QMessageBox.information(self, "Готово", "Импорт из буфера выполнен.")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка импорта", str(e))

    def _delete_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        running = [pid for pid in ids if pid in self._launchers]
        if running:
            QMessageBox.warning(
                self, "Удаление",
                "Сначала завершите запущенные профили.",
            )
            return
        names = [self._repo.get(pid).name for pid in ids if self._repo.get(pid)]
        if QMessageBox.question(
            self,
            "Удалить?",
            f"Удалить {len(ids)} профиль(ей)?\n" + ", ".join(names[:5]) + (" …" if len(names) > 5 else ""),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        ) != QMessageBox.StandardButton.Yes:
            return
        for pid in ids:
            self._repo.delete(pid)
        self._refresh_table()
        QMessageBox.information(self, "Готово", "Профили удалены.")

    def _check_browsers_closed(self) -> None:
        """Проверяет, не закрыл ли пользователь браузер вручную — обновляет статус в таблице."""
        to_remove = []
        for pid, launcher in self._launchers.items():
            if not launcher.is_running():
                to_remove.append(pid)
        for pid in to_remove:
            launcher = self._launchers.pop(pid, None)
            if launcher:
                try:
                    launcher.stop()
                except Exception:
                    pass
        if to_remove:
            self._refresh_table()

    def _launch_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        for pid in ids:
            if pid in self._launchers:
                continue
            p = self._repo.get(pid)
            if not p:
                continue
            worker = LaunchWorker(pid, p)
            worker.finished.connect(self._on_launch_finished)
            worker.error.connect(self._on_launch_error)
            worker.start()
            self._launch_workers.append(worker)

    def _on_launch_finished(self, profile_id: str, launcher: CamoufoxLauncher) -> None:
        self._launchers[profile_id] = launcher
        self._refresh_table()
        p = self._repo.get(profile_id)
        if p:
            QMessageBox.information(self, "Запуск", f"Браузер запущен для «{p.name}».")

    def _on_launch_error(self, profile_name: str, error_msg: str) -> None:
        QMessageBox.critical(self, "Ошибка запуска", f"{profile_name}: {error_msg}")

    def _stop_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        stopped = []
        for pid in ids:
            launcher = self._launchers.pop(pid, None)
            if launcher:
                launcher.stop()
                p = self._repo.get(pid)
                if p:
                    stopped.append(p.name)
        self._refresh_table()
        if stopped:
            QMessageBox.information(self, "Завершение", f"Завершено: {', '.join(stopped)}")

    def closeEvent(self, event) -> None:
        self._status_timer.stop()
        for launcher in self._launchers.values():
            try:
                launcher.stop()
            except Exception:
                pass
        self._launchers.clear()
        for w in self._launch_workers:
            if w.isRunning():
                w.terminate()
                w.wait(1000)
        event.accept()


def main() -> None:
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()
