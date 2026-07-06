"""
queue_manager.py
----------------
Çoklu indirme kuyruğu yöneticisi.
Thread-safe, maksimum N paralel indirme yönetir.
"""

from __future__ import annotations

import threading
from collections import deque
from typing import Callable, Optional

from PyQt6.QtCore import QObject, pyqtSignal

from backend.downloader import DownloadTask, DownloadWorker, DownloadStatus


class QueueManager(QObject):
    """
    İndirme kuyruğunu yöneten sınıf.

    Sinyaller:
        task_started(str)     - task_id: indirme başladı
        task_finished(str)    - task_id: indirme tamamlandı
        task_error(str, str)  - task_id, mesaj: hata
        task_cancelled(str)   - task_id: iptal edildi
        queue_empty()         - Kuyruk boşaldı
    """

    task_started = pyqtSignal(str)
    task_finished = pyqtSignal(str, str)   # task_id, output_path
    task_error = pyqtSignal(str, str)      # task_id, error_msg
    task_cancelled = pyqtSignal(str)
    queue_changed = pyqtSignal()
    queue_empty = pyqtSignal()

    def __init__(self, max_concurrent: int = 3, parent=None):
        super().__init__(parent)
        self._max_concurrent = max_concurrent
        self._lock = threading.Lock()

        # Bekleyen görevler kuyruğu
        self._pending: deque[DownloadTask] = deque()

        # Aktif worker'lar: task_id -> DownloadWorker
        self._active: dict[str, DownloadWorker] = {}

        # Tüm görev durumları: task_id -> DownloadStatus
        self._statuses: dict[str, DownloadStatus] = {}

    @property
    def max_concurrent(self) -> int:
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int):
        self._max_concurrent = max(1, value)
        self._start_pending()

    def add_task(self, task: DownloadTask) -> str:
        """Kuyruğa yeni indirme görevi ekler. task_id döndürür."""
        with self._lock:
            self._statuses[task.task_id] = DownloadStatus.PENDING
            self._pending.append(task)

        self.queue_changed.emit()
        self._start_pending()
        return task.task_id

    def cancel_task(self, task_id: str):
        """Görevi iptal eder (aktif veya bekleyen)."""
        with self._lock:
            # Aktif ise worker'ı durdur
            if task_id in self._active:
                worker = self._active[task_id]
                worker.cancel()
                self._statuses[task_id] = DownloadStatus.CANCELLED
                return

            # Bekleyen kuyruktaysa kaldır
            self._pending = deque(
                t for t in self._pending if t.task_id != task_id
            )
            if task_id in self._statuses:
                self._statuses[task_id] = DownloadStatus.CANCELLED

        self.task_cancelled.emit(task_id)
        self.queue_changed.emit()

    def cancel_all(self):
        """Tüm aktif ve bekleyen görevleri iptal eder."""
        with self._lock:
            task_ids = list(self._active.keys()) + [t.task_id for t in self._pending]
        for tid in task_ids:
            self.cancel_task(tid)

    def get_status(self, task_id: str) -> DownloadStatus:
        return self._statuses.get(task_id, DownloadStatus.PENDING)

    def pending_count(self) -> int:
        return len(self._pending)

    def active_count(self) -> int:
        return len(self._active)

    def total_count(self) -> int:
        return len(self._statuses)

    def _start_pending(self):
        """Yer varsa bekleyen görevleri başlatır."""
        with self._lock:
            while (
                self._pending
                and len(self._active) < self._max_concurrent
            ):
                task = self._pending.popleft()
                self._launch_worker(task)

    def _launch_worker(self, task: DownloadTask):
        """Worker thread'i oluşturur ve başlatır (lock içinde çağrılır)."""
        worker = DownloadWorker(task)
        self._active[task.task_id] = worker
        self._statuses[task.task_id] = DownloadStatus.DOWNLOADING

        # Sinyaller bağla
        worker.finished.connect(
            lambda path, tid=task.task_id: self._on_finished(tid, path)
        )
        worker.error.connect(
            lambda msg, tid=task.task_id: self._on_error(tid, msg)
        )

        worker.start()
        self.task_started.emit(task.task_id)
        self.queue_changed.emit()

    def _on_finished(self, task_id: str, output_path: str):
        """Worker tamamlandığında çağrılır."""
        with self._lock:
            self._active.pop(task_id, None)
            self._statuses[task_id] = DownloadStatus.FINISHED

        self.task_finished.emit(task_id, output_path)
        self.queue_changed.emit()

        if not self._active and not self._pending:
            self.queue_empty.emit()

        # Sıradakini başlat
        self._start_pending()

    def _on_error(self, task_id: str, error_msg: str):
        """Worker hata verdiğinde çağrılır."""
        with self._lock:
            self._active.pop(task_id, None)
            self._statuses[task_id] = DownloadStatus.ERROR

        self.task_error.emit(task_id, error_msg)
        self.queue_changed.emit()
        self._start_pending()

    def get_worker(self, task_id: str) -> DownloadWorker | None:
        """Aktif worker'a erişim sağlar (sinyal bağlama için)."""
        return self._active.get(task_id)
