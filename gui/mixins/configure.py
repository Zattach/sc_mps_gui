from json import dumps
from qtpy.QtCore import (Qt, Slot, QModelIndex, QItemSelection,
                         QSortFilterProxyModel)
from qtpy.QtWidgets import (QHeaderView, QApplication)
from mps_database.models import Device
from enums import ConfFiles
from models_pkg.configure_model import (ConfigureTableModel)


class ConfigureMixin:
    def configure_init(self):
        """Initializer for everything in Configure tab: ListViews and
        PyDMEmbeddedDisplay."""
        self.ui.configure_spltr.setSizes([50, 50])
        self.ui.devs_spltr.setStretchFactor(0, 2)
        self.ui.devs_spltr.setStretchFactor(1, 1)

        devs = self.model.config.session.query(Device).all()

        # Set model, filter, and header for the All Devices table
        self.all_devs_model = ConfigureTableModel(self, devs)
        self.all_devs_filter = QSortFilterProxyModel(self)
        self.all_devs_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.all_devs_filter.setSourceModel(self.all_devs_model)
        self.ui.all_devs_tbl.setModel(self.all_devs_filter)
        self.ui.all_devs_tbl.sortByColumn(1, Qt.AscendingOrder)
        hdr = self.ui.all_devs_tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)

        # Set model, filter, and header for the Selected Devices table
        self.sel_devs_model = ConfigureTableModel(self, [])
        self.sel_devs_filter = QSortFilterProxyModel(self)
        self.sel_devs_filter.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.sel_devs_filter.setSourceModel(self.sel_devs_model)
        self.ui.sel_devs_tbl.setModel(self.sel_devs_filter)
        self.ui.sel_devs_tbl.sortByColumn(1, Qt.AscendingOrder)
        hdr = self.ui.sel_devs_tbl.horizontalHeader()
        hdr.setSectionResizeMode(0, QHeaderView.Stretch)
        hdr.setSectionResizeMode(1, QHeaderView.ResizeToContents)

    def configure_connections(self):
        """Establish PV and slot connections for the devices model and
        configure tab."""
        # All Devices table and LineEdit
        self.ui.all_devs_edt.textChanged.connect(self.all_devs_filter.setFilterFixedString)
        self.ui.all_devs_tbl.selectionModel().selectionChanged.connect(self.dev_selected)

        # Selected Devices table and LineEdit
        self.ui.sel_devs_edt.textChanged.connect(self.sel_devs_filter.setFilterFixedString)
        self.ui.sel_clear_btn.clicked.connect(self.sel_devs_model.clear_data)
        self.ui.sel_devs_tbl.clicked.connect(self.dev_deselect)
        self.sel_devs_model.table_changed.connect(self.reload_embed)

    @Slot(QItemSelection, QItemSelection)
    def dev_selected(self, selected: QItemSelection, **kw):
        indexes = [i for i in selected.indexes() if i.column() == 0]

        for ind in indexes:
            dev_id = self.all_devs_filter.mapToSource(ind).row()
            dev = self.all_devs_model.get_device(dev_id)
            self.sel_devs_model.add_datum(dev)

    @Slot(QModelIndex)
    def dev_deselect(self, index: QModelIndex):
        if not index.isValid():
            return

        dev_id = self.sel_devs_filter.mapToSource(index).row()
        self.sel_devs_model.remove_datum(dev_id)

    @Slot(ConfFiles)
    def reload_embed(self, dev_type: ConfFiles):
        if dev_type == ConfFiles.BPMS:
            if self.sel_devs_model.rowCount() == 1:
                dev = self.sel_devs_model.get_device(0)
                mac = {'MULTI': False,
                       'LN': dev.card.link_node.lcls1_id,
                       'CL': dev.card.crate.location,
                       'AC': f"Slot {dev.card.number}" if dev.card.number != 1 else "RTM"}
                if dev.is_analog():
                    mac['CH'] = dev.channel.number
                else:
                    mac['CH'] = ", ".join([i.channel.number for i in dev.inputs])
                mac['DEVICE'] = self.model.name.getDeviceName(dev)
            else:
                mac = {'MULTI': True}
                for i in range(self.sel_devs_model.rowCount()):
                    dev = self.sel_devs_model.get_device(i)
                    mac[f'LN{i+1}'] = dev.card.link_node.lcls1_id
                    mac[f'CL{i+1}'] = dev.card.crate.location
                    mac[f'AC{i+1}'] = f"Slot {dev.card.number}" if dev.card.number != 1 else "RTM"
                    if dev.is_analog():
                        mac[f'CH{i+1}'] = dev.channel.number
                    else:
                        mac[f'CH{i+1}'] = ", ".join([i.channel.number for i in dev.inputs])
                    mac[f'DEV{i+1}'] = self.model.name.getDeviceName(dev)
        else:
            mac = {}

        self.ui.configure_embed.macros = dumps(mac)
        self.ui.configure_embed.filename = dev_type.value
        QApplication.instance().processEvents()
