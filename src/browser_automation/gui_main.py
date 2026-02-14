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
    QHBoxLayout,
    QHeaderView,
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
from browser_automation.value_objects import (
    PROFILE_VERSION,
    CamoufoxSettings,
    Profile,
    ProxyConfig,
)

DEFAULT_PROFILES_PATH = Path.home() / ".config" / "browser-automation" / "profiles.json"

class LaunchWorker(QThread):
    """Запуск Camoufox в отдельном потоке — избегает 'Sync API inside asyncio loop'."""

    finished = Signal(str, object)  # profile_id, launcher
    error = Signal(str, str)
    cookies_ready = Signal(str, list)  # profile_id, cookies
    browser_closed = Signal(str)  # profile_id — браузер закрыт вручную
    fetch_requested = Signal()  # запрос куков из главного потока
    stop_requested = Signal()  # запрос остановки

    def __init__(self, profile_id: str, profile: Profile) -> None:
        super().__init__()
        self.profile_id = profile_id
        self.profile = profile
        self._launcher: CamoufoxLauncher | None = None
        self._check_timer: QTimer | None = None

    def run(self) -> None:
        try:
            self._launcher = CamoufoxLauncher(profile=self.profile)
            self._launcher.start()
            self.finished.emit(self.profile_id, self._launcher)
            self.fetch_requested.connect(self.fetch_cookies, Qt.ConnectionType.QueuedConnection)
            self.stop_requested.connect(self.fetch_and_stop, Qt.ConnectionType.QueuedConnection)
            self._check_timer = QTimer()
            self._check_timer.timeout.connect(self._check_browser_closed)
            self._check_timer.start(2000)
        except Exception as e:
            self.error.emit(self.profile.name, str(e))
            return
        self.exec()

    def _check_browser_closed(self) -> None:
        """В потоке воркера — Playwright требует тот же поток."""
        if self._launcher and not self._launcher.is_running():
            if self._check_timer:
                self._check_timer.stop()
            cookies = self._launcher.get_all_browser_cookies()
            if cookies:
                self.cookies_ready.emit(self.profile_id, cookies)
            self.browser_closed.emit(self.profile_id)

    def fetch_cookies(self) -> None:
        """Вызывается по таймеру — в потоке воркера."""
        if self._launcher:
            cookies = self._launcher.get_all_browser_cookies()
            if cookies:
                self.cookies_ready.emit(self.profile_id, cookies)

    def fetch_and_stop(self) -> None:
        """Вызвать перед остановкой — куки + stop в потоке воркера."""
        if self._check_timer:
            self._check_timer.stop()
        if self._launcher:
            cookies = self._launcher.get_all_browser_cookies()
            self.cookies_ready.emit(self.profile_id, cookies)
            self._launcher.stop()
        self.quit()




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
            "Оставьте пустым — без прокси. Если указать VLESS — прокси 127.0.0.1, порт подберётся свободный (10808, 10809, …)."
        )
        self.vless_edit.setMaximumHeight(80)
        form.addRow("VLESS:", self.vless_edit)

        self.proxy_host = QLineEdit()
        self.proxy_host.setPlaceholderText(
            "Только без VLESS: укажите host. С VLESS — оставьте пустым (будет 127.0.0.1)."
        )
        form.addRow("Прокси host:", self.proxy_host)
        self.proxy_port = QLineEdit()
        self.proxy_port.setPlaceholderText(
            "Без VLESS: укажите port. С VLESS: пусто — с 10808; или стартовый порт для поиска свободного."
        )
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
        host = self.proxy_host.text().strip()
        port_str = self.proxy_port.text().strip()
        if vless:
            # VLESS задан: port пусто → 10808; иначе стартовый порт для поиска свободного
            if port_str:
                try:
                    proxy = ProxyConfig(host="127.0.0.1", port=int(port_str))
                except ValueError:
                    proxy = ProxyConfig(host="127.0.0.1", port=10808)
            # port пусто → proxy=None, лаунчер возьмёт 10808 по умолчанию
        else:
            # VLESS пустой: host/port пусто → без прокси; иначе ручной прокси
            if host or port_str:
                try:
                    proxy = ProxyConfig(
                        host=host or "127.0.0.1",
                        port=int(port_str) if port_str else 10808,
                    )
                except ValueError:
                    pass
        return Profile(
            id=self._profile.id if self._profile else "",
            name=name,
            vless_raw=vless,
            proxy_config=proxy,
            camoufox_settings=CamoufoxSettings(),
            cookies=self._profile.cookies if self._profile else None,
            version=getattr(self._profile, "version", PROFILE_VERSION)
            if self._profile
            else PROFILE_VERSION,
        )


class MainWindow(QMainWindow):
    """Главное окно: таблица профилей, панель действий."""

    def __init__(self, profiles_path: Path | str = DEFAULT_PROFILES_PATH) -> None:
        super().__init__()
        self.setWindowTitle("Browser Automation — Профили")
        self.setMinimumSize(600, 450)
        self.resize(800, 550)
        self._profiles_path = Path(profiles_path)
        self._repo = ProfileRepository(self._profiles_path)
        self._launchers: dict[str, CamoufoxLauncher] = {}
        self._workers: dict[str, LaunchWorker] = {}
        self._launch_workers: list[LaunchWorker] = []

        # Периодическое сохранение куков (при ручном закрытии браузера)
        self._cookies_timer = QTimer(self)
        self._cookies_timer.timeout.connect(self._save_running_cookies)
        self._cookies_timer.start(15_000)  # каждые 15 сек — куки в профиль JSON

        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)

        # Таблица
        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Название", "ID"])
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Stretch
        )
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
        launch_btn.setStyleSheet(
            "background: #2e7d32; color: white; font-weight: bold;"
        )
        self._launch_btn = launch_btn
        panel.addWidget(launch_btn)

        layout.addLayout(panel)
        self._refresh_table()
        self._on_selection_changed()

    def _refresh_table(self) -> None:
        self.table.setRowCount(0)
        for p in self._repo.list_all():
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(p.name))
            id_item = QTableWidgetItem(p.id[:12] + "…")
            id_item.setData(Qt.ItemDataRole.UserRole, p.id)
            self.table.setItem(row, 1, id_item)
            self.table.setRowHeight(row, 28)

    def _selected_ids(self) -> list[str]:
        ids = []
        for item in self.table.selectedItems():
            row = item.row()
            id_cell = self.table.item(row, 1)
            if id_cell:
                pid = id_cell.data(Qt.ItemDataRole.UserRole)
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

    def _on_cell_double_clicked(self, row: int, _col: int) -> None:
        id_cell = self.table.item(row, 1)
        if id_cell:
            pid = id_cell.data(Qt.ItemDataRole.UserRole)
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
                cookies=p.cookies,
                version=p.version,
            )
            self._repo.update(new_p)
            self._refresh_table()
            QMessageBox.information(self, "Готово", f"Профиль «{new_p.name}» обновлён.")

    def _duplicate_selected(self) -> None:
        for pid in self._selected_ids():
            new_p = self._repo.copy(pid)
            if new_p:
                QMessageBox.information(
                    self, "Готово", f"Скопировано как «{new_p.name}»."
                )
        self._refresh_table()

    def _export_profile_data(self, pid: str) -> dict | None:
        """Экспорт профиля (куки из repo — периодически сохраняются)."""
        p = self._repo.get(pid)
        if not p:
            return None
        return p.to_dict()

    def _export_to_clipboard(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        data = [self._export_profile_data(pid) for pid in ids]
        data = [d for d in data if d]
        if not data:
            return
        text = json.dumps(data, ensure_ascii=False, indent=2)
        QApplication.clipboard().setText(text)
        QMessageBox.information(
            self, "Готово", f"В буфер скопировано {len(data)} профиль(ей)."
        )

    def _export_to_file(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        data = [self._export_profile_data(pid) for pid in ids]
        data = [d for d in data if d]
        if not data:
            return
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
        names = [self._repo.get(pid).name for pid in ids if self._repo.get(pid)]
        if (
            QMessageBox.question(
                self,
                "Удалить?",
                f"Удалить {len(ids)} профиль(ей)? Браузеры будут закрыты.\n"
                + ", ".join(names[:5])
                + (" …" if len(names) > 5 else ""),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        workers_to_wait = []
        for pid in ids:
            launcher = self._launchers.pop(pid, None)
            worker = self._workers.pop(pid, None)
            if worker and launcher:
                worker.cookies_ready.connect(self._on_cookies_ready)
                worker.stop_requested.emit()
                workers_to_wait.append(worker)
            elif launcher:
                launcher.stop()
        for w in workers_to_wait:
            w.wait(5000)
        for pid in ids:
            self._repo.delete(pid)
        self._refresh_table()
        QMessageBox.information(self, "Готово", "Профили удалены.")

    def _save_running_cookies(self) -> None:
        """Сохраняет куки — сигнал воркеру (выполнится в его потоке)."""
        for worker in self._workers.values():
            worker.fetch_requested.emit()

    def _on_cookies_ready(self, profile_id: str, cookies: list) -> None:
        """Получены куки от воркера — сохраняем в профиль."""
        p = self._repo.get(profile_id)
        if p and cookies:
            updated = Profile(
                id=p.id,
                name=p.name,
                cookies=cookies,
                proxy_config=p.proxy_config,
                vless_raw=p.vless_raw,
                camoufox_settings=p.camoufox_settings,
                version=p.version,
            )
            self._repo.update(updated)

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
            worker.cookies_ready.connect(self._on_cookies_ready)
            worker.browser_closed.connect(self._on_browser_closed)
            self._launch_workers.append(worker)
            worker.start()

    def _on_launch_finished(self, profile_id: str, launcher: CamoufoxLauncher) -> None:
        self._launchers[profile_id] = launcher
        worker = self.sender()
        if isinstance(worker, LaunchWorker):
            self._workers[profile_id] = worker
            if worker in self._launch_workers:
                self._launch_workers.remove(worker)
        self._refresh_table()
        p = self._repo.get(profile_id)
        name = p.name if p else profile_id
        self.statusBar().showMessage(f"Браузер запущен: {name}", 3000)

    def _on_browser_closed(self, profile_id: str) -> None:
        """Браузер закрыт вручную."""
        self._launchers.pop(profile_id, None)
        self._workers.pop(profile_id, None)

    def _on_launch_error(self, profile_name: str, error_msg: str) -> None:
        worker = self.sender()
        if isinstance(worker, LaunchWorker) and worker in self._launch_workers:
            self._launch_workers.remove(worker)
        QMessageBox.critical(self, "Ошибка запуска", f"{profile_name}: {error_msg}")

    def closeEvent(self, event) -> None:
        self._cookies_timer.stop()
        workers_to_wait = []
        for pid in list(self._launchers.keys()):
            launcher = self._launchers.get(pid)
            worker = self._workers.get(pid)
            if worker and launcher:
                worker.cookies_ready.connect(self._on_cookies_ready)
                worker.stop_requested.emit()
                workers_to_wait.append(worker)
        for w in workers_to_wait:
            w.wait(5000)
        self._launchers.clear()
        self._workers.clear()
        event.accept()


def main() -> None:
    import signal
    from pathlib import Path

    DEFAULT_PROFILES_PATH = (
        Path.home() / ".config" / "browser-automation" / "profiles.json"
    )

    app = QApplication([])
    win = MainWindow(DEFAULT_PROFILES_PATH)
    win.show()

    def signal_handler(sig, frame):
        print("\nПолучен сигнал завершения. Закрываем GUI...")
        app.quit()

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    app.exec()
