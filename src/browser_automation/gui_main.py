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
    QProgressDialog,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from browser_automation.camoufox_launcher import CamoufoxLauncher
from browser_automation.profile_repository import ProfileRepository
from browser_automation.value_objects import PROFILE_VERSION, CamoufoxSettings, Profile, ProxyConfig


DEFAULT_PROFILES_PATH = Path.home() / ".config" / "browser-automation" / "profiles.json"

STATUS_RUNNING = "запущен"
STATUS_STOPPED = "не запущен"


class StopWorker(QThread):
    """Завершение браузера в отдельном потоке — browser.close() не блокирует UI."""

    finished = Signal()

    def __init__(self, launcher: CamoufoxLauncher) -> None:
        super().__init__()
        self._launcher = launcher

    def run(self) -> None:
        try:
            self._launcher.stop()
        except Exception:
            pass
        self.finished.emit()


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
            version=getattr(self._profile, "version", PROFILE_VERSION) if self._profile else PROFILE_VERSION,
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
        self._stop_workers: list[StopWorker] = []

        # Таймер: проверка, не закрыл ли пользователь браузер вручную
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._check_browsers_closed)
        self._status_timer.start(2000)  # каждые 2 сек
        # Периодическое сохранение куков (при ручном закрытии браузера)
        self._cookies_timer = QTimer(self)
        self._cookies_timer.timeout.connect(self._save_running_cookies)
        self._cookies_timer.start(15_000)  # каждые 15 сек — куки в профиль JSON

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
                QMessageBox.information(self, "Готово", f"Скопировано как «{new_p.name}».")
        self._refresh_table()

    def _export_profile_data(self, pid: str) -> dict | None:
        """Экспорт профиля: если запущен — куки берём из браузера."""
        p = self._repo.get(pid)
        if not p:
            return None
        d = p.to_dict()
        if pid in self._launchers:
            cookies = self._launchers[pid].get_all_browser_cookies()
            if cookies:
                d["cookies"] = cookies
        return d

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

    def _save_running_cookies(self) -> None:
        """Сохраняет куки всех запущенных профилей (на случай ручного закрытия браузера)."""
        for pid, launcher in self._launchers.items():
            if not launcher.is_running():
                continue
            cookies = launcher.get_all_browser_cookies()
            p = self._repo.get(pid)
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
            progress = QProgressDialog("Запуск браузера...", None, 0, 0, self)
            progress.setWindowModality(Qt.WindowModality.WindowModal)
            progress.setMinimumDuration(0)
            progress.show()
            QApplication.processEvents()
            try:
                launcher = CamoufoxLauncher(profile=p)
                launcher.start()
                self._launchers[pid] = launcher
                self._refresh_table()
                QMessageBox.information(self, "Запуск", f"Браузер запущен для «{p.name}».")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка запуска", f"{p.name}: {e}")
            finally:
                progress.close()

    def _stop_selected(self) -> None:
        ids = self._selected_ids()
        if not ids:
            return
        stopped = []
        for pid in ids:
            launcher = self._launchers.pop(pid, None)
            if launcher:
                cookies = launcher.get_all_browser_cookies()
                p = self._repo.get(pid)
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
                worker = StopWorker(launcher)
                worker.finished.connect(self._on_stop_worker_finished)
                self._stop_workers.append(worker)
                worker.start()
                if p:
                    stopped.append(p.name)
        self._refresh_table()
        if stopped:
            QMessageBox.information(self, "Завершение", f"Завершение: {', '.join(stopped)}")

    def _on_stop_worker_finished(self) -> None:
        # Удаляем завершённые воркеры
        self._stop_workers[:] = [w for w in self._stop_workers if w.isRunning()]

    def closeEvent(self, event) -> None:
        self._status_timer.stop()
        self._cookies_timer.stop()
        for pid, launcher in list(self._launchers.items()):
            try:
                cookies = launcher.get_all_browser_cookies()
                p = self._repo.get(pid)
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
                launcher.stop()
            except Exception:
                pass
        self._launchers.clear()
        event.accept()


def main() -> None:
    app = QApplication([])
    win = MainWindow()
    win.show()
    app.exec()
