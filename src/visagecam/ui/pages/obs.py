# Copyright (c) 2026 Skaiiner. Todos los derechos reservados.

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
)

from visagecam.obs import ObsClient
from visagecam.ui.components import Card, SwitchRow, button, muted, pill, set_tone
from visagecam.ui.context import Context
from visagecam.ui.pages.base import Page, header


class ObsPage(Page):
    def __init__(self, ctx: Context) -> None:
        super().__init__(ctx)
        self.obs = ObsClient(ctx.settings.obs_host, ctx.settings.obs_port, ctx.settings.obs_password)
        self._scene_items: list = []
        self._updating = False
        status_row = pill("Desconectado")
        self.status = status_row
        self.column.addLayout(header("OBS Studio", status_row))

        conn = Card("Conexion", "En OBS: Herramientas > Ajustes del servidor WebSocket.")
        host_row = QHBoxLayout()
        self.host = QLineEdit(ctx.settings.obs_host)
        self.host.setPlaceholderText("Servidor")
        self.port = QSpinBox()
        self.port.setRange(1, 65535)
        self.port.setValue(ctx.settings.obs_port)
        self.port.setFixedWidth(90)
        self.port.setButtonSymbols(QSpinBox.NoButtons)
        host_row.addWidget(self.host, 1)
        host_row.addWidget(self.port)
        conn.add(layout=host_row)
        self.password = QLineEdit(ctx.settings.obs_password)
        self.password.setEchoMode(QLineEdit.Password)
        self.password.setPlaceholderText("Contrasena")
        conn.add(self.password)
        self.connect_button = button("Conectar", "primary", "plug", "#0b0d12")
        self.connect_button.clicked.connect(self._toggle)
        conn.add(self.connect_button)
        self.message = muted("")
        conn.add(self.message)
        self.column.addWidget(conn)

        self.scenes_card = Card("Escenas", "Doble clic en una escena para cambiar a ella.")
        self.scenes = QListWidget()
        self.scenes.setObjectName("plain")
        self.scenes.setFixedHeight(130)
        self.scenes.currentItemChanged.connect(lambda *_: self._load_items())
        self.scenes.itemDoubleClicked.connect(lambda _i: self._switch())
        self.scenes_card.add(self.scenes)
        switch = button("Cambiar a la escena seleccionada", "ghost", "play")
        switch.clicked.connect(self._switch)
        self.scenes_card.add(switch)
        self.column.addWidget(self.scenes_card)

        self.items_card = Card("Fuentes de la escena", "Activa o desactiva fuentes al instante.")
        self.items_box = QVBoxLayout()
        self.items_box.setSpacing(10)
        self.items_card.add(layout=self.items_box)
        add = button("Anadir camara VisageCam a la escena", "ghost", "camera")
        add.clicked.connect(self._add_camera)
        self.items_card.add(add)
        self.column.addWidget(self.items_card)
        self.finish()
        self._set_connected(False)

    def shutdown(self) -> None:
        self.obs.disconnect()

    def _set_connected(self, connected: bool) -> None:
        self.scenes_card.setEnabled(connected)
        self.items_card.setEnabled(connected)
        self.status.setText("Conectado" if connected else "Desconectado")
        set_tone(self.status, "ok" if connected else "")
        self.connect_button.setText("Desconectar" if connected else "Conectar")

    def _toggle(self) -> None:
        if self.obs.connected:
            self.obs.disconnect()
            self._set_connected(False)
            self.message.setText("")
            return
        s = self.ctx.settings
        self.obs.host = self.host.text().strip() or "localhost"
        self.obs.port = self.port.value()
        self.obs.password = self.password.text()
        s.obs_host, s.obs_port, s.obs_password = self.obs.host, self.obs.port, self.obs.password
        self.ctx.save()
        self.connect_button.setEnabled(False)
        self.message.setText("Conectando...")

        def work():
            self.obs.connect()
            return self.obs.list_scenes()

        self.ctx.runner.run(work, self._connected, self._failed)

    def _connected(self, result) -> None:
        scenes, current = result
        self.connect_button.setEnabled(True)
        self._set_connected(True)
        self.message.setText(f"OBS {self.obs.obs_version}. Escena activa: {current}")
        self._updating = True
        self.scenes.clear()
        for name in scenes:
            entry = QListWidgetItem(name)
            self.scenes.addItem(entry)
            if name == current:
                self.scenes.setCurrentItem(entry)
        self._updating = False
        self._load_items()

    def _failed(self, message: str) -> None:
        self.connect_button.setEnabled(True)
        self._set_connected(False)
        self.message.setText(message)
        set_tone(self.status, "danger")
        self.status.setText("Error")
        self.ctx.notify(message, "error")

    def _scene(self) -> str:
        item = self.scenes.currentItem()
        return item.text() if item else ""

    def _load_items(self) -> None:
        scene = self._scene()
        if not scene or self._updating or not self.obs.connected:
            return
        self.ctx.runner.run(lambda: self.obs.list_items(scene), self._show_items, self._failed)

    def _show_items(self, items) -> None:
        while self.items_box.count():
            entry = self.items_box.takeAt(0)
            if entry.widget() is not None:
                entry.widget().deleteLater()
        if not items:
            self.items_box.addWidget(muted("Esta escena no tiene fuentes."))
        for item in items:
            row = SwitchRow(item.name)
            row.setChecked(item.enabled)
            row.toggled.connect(lambda state, i=item.item_id: self._toggle_item(i, state))
            self.items_box.addWidget(row)

    def _toggle_item(self, item_id: int, state: bool) -> None:
        scene = self._scene()
        self.ctx.runner.run(
            lambda: self.obs.set_item_enabled(scene, item_id, state),
            None,
            lambda message: (self.ctx.notify(message, "error"), self._load_items()),
        )

    def _switch(self) -> None:
        scene = self._scene()
        if not scene:
            return
        self.ctx.runner.run(
            lambda: self.obs.set_scene(scene),
            lambda _r: (
                self.message.setText(f"Escena activa: {scene}"),
                self.ctx.notify(f"Escena: {scene}", "ok"),
            ),
            self._failed,
        )

    def _add_camera(self) -> None:
        scene = self._scene()
        if not scene:
            return
        url = self.ctx.engine.stream.url
        self.ctx.runner.run(
            lambda: self.obs.add_camera_source(scene, stream_url=url),
            lambda label: (self.ctx.notify(f"Camara anadida a {scene} ({label})", "ok"), self._load_items()),
            lambda message: self.ctx.notify(message, "error"),
        )
