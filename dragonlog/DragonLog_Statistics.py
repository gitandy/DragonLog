# DragonLog (c) 2025 by Andreas Schawo is licensed under CC BY-SA 4.0.
# To view a copy of this license, visit http://creativecommons.org/licenses/by-sa/4.0/

from PyQt6 import QtWidgets, QtSql, QtGui
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure


# noinspection PyPep8Naming
class StatisticsWidget(QtWidgets.QDialog):
    def __init__(self, parent, title: str, db_con: QtSql.QSqlDatabase, bands: tuple):
        super().__init__(parent)

        self.__db_con__ = db_con
        self.__bands__ = bands

        self.initTemporary()

        self.setWindowTitle(title)
        self.setModal(True)
        self.setWhatsThis(self.tr('Press Ctrl+C to copy the data to the clipboard'))
        verticalLayout = QtWidgets.QVBoxLayout()
        self.setLayout(verticalLayout)
        self.tabWidget = QtWidgets.QTabWidget()
        verticalLayout.addWidget(self.tabWidget)

        self.buildTableStat('QSO', (self.tr('QSOs'), self.tr('Modes'), self.tr('Bands'),
                                    self.tr('Gridsquares'), self.tr('Contest QSOs')))
        self.buildQSLStat('QSL', (self.tr('QSOs'),
                                  self.tr('QSL sent'), self.tr('QSL rcvd'),
                                  self.tr('eQSL sent'), self.tr('eQSL rcvd'),
                                  self.tr('LotW sent'), self.tr('LotW rcvd')))
        self.buildGraphStat(self.tr('Modes'), 'mode')
        self.buildGraphStat(self.tr('Bands'), 'band')

        self.show()

    def initTemporary(self):
        # QSO stat
        self.__db_con__.exec('''CREATE TEMP VIEW IF NOT EXISTS t_qso_stat AS
            SELECT strftime('%Y', date_time) as year, COUNT(id) as qsos, COUNT(DISTINCT mode) as modes, 
                COUNT(DISTINCT band) as bands, COUNT(DISTINCT upper(substr(locator, 0, 4))) as gridsquares, 
                COUNT(nullif(contest_id = '', 1)) as contest_qsos
            FROM qsos GROUP BY year
            UNION SELECT 'total', COUNT(id), COUNT(DISTINCT mode), COUNT(DISTINCT band), 
                COUNT(DISTINCT upper(substr(locator, 0, 4))), COUNT(nullif(contest_id = '', 1)) 
            FROM qsos;''')
        # QSL stat
        self.__db_con__.exec('''CREATE TEMP VIEW IF NOT EXISTS t_qsl_stat AS 
            SELECT
                strftime('%Y', date_time) as year, COUNT(id) as qsos, 
                COUNT(nullif(qsl_sent != 'Y', 1)) as qsl_sent, COUNT(nullif(qsl_rcvd != 'Y', 1)) as qsl_rcvd,
                COUNT(nullif(eqsl_sent != 'Y', 1)) as eqsl_sent, COUNT(nullif(eqsl_rcvd != 'Y', 1)) as eqsl_rcvd,
                COUNT(nullif(lotw_sent != 'Y', 1)) as lotw_sent, COUNT(nullif(lotw_rcvd != 'Y', 1)) as lotw_rcvd
            FROM qsos GROUP BY year
            UNION SELECT 'total', COUNT(id) as qsos, 
                COUNT(nullif(qsl_sent != 'Y', 1)), COUNT(nullif(qsl_rcvd != 'Y', 1)),
                COUNT(nullif(eqsl_sent != 'Y', 1)), COUNT(nullif(eqsl_rcvd != 'Y', 1)),
                COUNT(nullif(lotw_sent != 'Y', 1)), COUNT(nullif(lotw_rcvd != 'Y', 1)) 
            FROM qsos;''')

        # Bands table for proper sorting
        query = self.__db_con__.exec('''SELECT count(*) FROM sqlite_master WHERE type='table' AND name='t_bands';''')
        if query.next() and query.value(0) == 0:
            self.__db_con__.exec('''CREATE TEMP TABLE IF NOT EXISTS t_bands (
                    "id"    INTEGER NOT NULL,
                    "band"  TEXT,
                    PRIMARY KEY("id" AUTOINCREMENT)
                );''')
            for b in self.__bands__:
                self.__db_con__.exec(f"INSERT INTO t_bands (band) VALUES ('{b}')")

        # Bands summary
        self.__db_con__.exec('''CREATE TEMP VIEW IF NOT EXISTS t_band_stat AS 
            SELECT band, COUNT(*) as qsos FROM qsos GROUP BY band;''')
        # Modes summary
        self.__db_con__.exec('''CREATE TEMP VIEW IF NOT EXISTS t_mode_stat AS 
            SELECT mode, COUNT(*) as qsos FROM qsos GROUP BY mode;''')
        # Bands per year
        self.__db_con__.exec('''CREATE TEMP VIEW IF NOT EXISTS t_bands_per_year AS 
            WITH 
                years AS (SELECT DISTINCT strftime('%Y', date_time) as year FROM qsos),
                dist_bands AS (SELECT DISTINCT band FROM qsos),
                year_band AS (SELECT year, band FROM years CROSS JOIN dist_bands)
            SELECT 
                yb.year,
                yb.band,
                COALESCE(COUNT(q.id), 0) AS qso_count
            FROM 
                year_band yb
            LEFT JOIN 
                qsos q ON strftime('%Y', q.date_time) = yb.year AND q.band = yb.band
            LEFT JOIN 
                t_bands b ON b.band = yb.band 
            GROUP BY 
                yb.year, yb.band
            ORDER BY 
                yb.year, b.id;
            ''')
        # Modes per year
        self.__db_con__.exec('''CREATE TEMP VIEW IF NOT EXISTS t_modes_per_year AS 
            WITH 
                years AS (SELECT DISTINCT strftime('%Y', date_time) as year FROM qsos),
                modes AS (SELECT DISTINCT mode FROM qsos),
                year_mode AS (SELECT year, mode FROM years CROSS JOIN modes)
            SELECT 
                ym.year,
                ym.mode,
                COALESCE(COUNT(q.id), 0) AS qso_count
            FROM 
                year_mode ym
            LEFT JOIN 
                qsos q ON strftime('%Y', q.date_time) = ym.year AND q.mode = ym.mode
            GROUP BY 
                ym.year, ym.mode
            ORDER BY 
                ym.year, ym.mode;
            ''')
        self.__db_con__.commit()

    def fetchStat(self, name='qso') -> list[list]:
        stat = []
        if self.__db_con__ and name in ('qso', 'qsl', 'band', 'mode'):
            query = self.__db_con__.exec(f'SELECT * FROM t_{name}_stat')
            if query.lastError().text():
                raise Exception(query.lastError().text())

            rec = query.record()
            col_count = rec.count()
            stat.append([rec.fieldName(i) for i in range(col_count)])
            while query.next():
                stat.append([query.value(i) for i in range(col_count)])
        return stat

    def fetchPerYearStat(self, name) -> dict[str, list]:
        stat: dict[str, list] = {
            'categories': [],
        }
        if self.__db_con__ and name in ('band', 'mode'):
            query = self.__db_con__.exec(f'SELECT * FROM t_{name}s_per_year')
            if query.lastError().text():
                raise Exception(query.lastError().text())
            while query.next():
                if query.value(1) not in stat['categories']:
                    stat['categories'].append(query.value(1))
                if query.value(0) not in stat:
                    stat[query.value(0)] = [query.value(2)]
                else:
                    stat[query.value(0)].append(query.value(2))
        return stat

    def buildTableStat(self, title: str, header: tuple = ()):
        stat = self.fetchStat(title.lower())
        if not stat:
            return

        tableWidget = StatTableWidget(len(stat) - 1, len(stat[0]) - 1, stat_summary=stat.copy())
        tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        tableWidget.setVerticalHeaderLabels([str(r[0]).capitalize() for r in stat[1:]])

        if header:
            tableWidget.setHorizontalHeaderLabels(header)
        else:
            tableWidget.setHorizontalHeaderLabels([hl.capitalize() for hl in stat[0][1:]])

        self.tabWidget.addTab(tableWidget, f'{title}-{self.tr("Statistic")}')

        for r, row in enumerate(stat[1:]):
            for c, cell in enumerate(row[1:]):
                item = QtWidgets.QTableWidgetItem(str(cell))
                tableWidget.setItem(r, c, item)

        tableWidget.resizeColumnsToContents()

    def buildQSLStat(self, title: str, header: tuple = ()):
        stat = self.fetchStat(title.lower())
        if not stat:
            return

        widget = StatWidget(self, stat_summary=stat)

        # Table
        tableWidget = StatTableWidget(len(stat) - 1, len(stat[0]) - 1, stat_summary=stat.copy())
        tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        tableWidget.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.NoSelection)
        tableWidget.setVerticalHeaderLabels([str(r[0]).capitalize() for r in stat[1:]])

        if header:
            tableWidget.setHorizontalHeaderLabels(header)
        else:
            tableWidget.setHorizontalHeaderLabels([hl.capitalize() for hl in stat[0][1:]])

        for r, row in enumerate(stat[1:]):
            for c, cell in enumerate(row[1:]):
                item = QtWidgets.QTableWidgetItem(str(cell))
                tableWidget.setItem(r, c, item)
        tableWidget.resizeColumnsToContents()

        # Graph
        stat_widget = FigureCanvasQTAgg(Figure())
        ax = stat_widget.figure.subplots()
        ax.tick_params(axis='x', rotation=90)
        cat = header
        width = .8
        bottom = np.zeros(len(header))

        for d in stat[1:-1]:
            val = [int(v) for v in d[1:]]
            p = ax.bar(cat, val, width, label=d[0], bottom=bottom)
            bottom += val
        stat_widget.figure.tight_layout()

        # Layout
        layout = QtWidgets.QVBoxLayout(widget)
        layout.addWidget(tableWidget)
        layout.addWidget(stat_widget)
        layout.addWidget(NavigationToolbar(stat_widget, self.parent()))
        self.tabWidget.addTab(widget, f'{title}-{self.tr("Statistic")}')

    def buildGraphStat(self, title: str, stat_name: str):
        stat_sum = self.fetchStat(stat_name)
        if not stat_sum:
            return

        stat_detail = self.fetchPerYearStat(stat_name)
        if not stat_detail:
            return

        # Init
        widget = StatWidget(self, stat_summary=stat_sum.copy(), stat_details=stat_detail.copy())
        stat_widget = FigureCanvasQTAgg(Figure())
        ax = stat_widget.figure.subplots(1, 2)

        # per year
        stat_cat = stat_detail.pop('categories')
        x = np.arange(len(stat_cat))
        width = 1 / (len(stat_detail) + 1)  # the width of the bars

        try:
            for i, (cat, count) in enumerate(stat_detail.items()):
                offset = width * i
                rects = ax[0].bar(x + offset, count, width, label=cat)
                # ax[0].bar_label(rects, padding=3)
                ax[0].tick_params(axis='x', rotation=90)

            ax[0].set_ylabel('QSOs')
            ax[0].set_title(f'{title} ' + self.tr('per year'))
            ax[0].set_xticks(x + width, stat_cat)
            ax[0].legend(fontsize='small')

            # summary
            stat_sum = np.array(stat_sum[1:]).transpose()
            ax[1].pie([int(c) for c in stat_sum[1]], labels=stat_sum[0])
            ax[1].set_title(f'{title} ' + self.tr('summary'))

            # display
            stat_widget.figure.tight_layout()
            layout = QtWidgets.QVBoxLayout(widget)
            layout.addWidget(stat_widget)
            layout.addWidget(NavigationToolbar(stat_widget, self.parent()))
            self.tabWidget.addTab(widget, f'{title}-{self.tr("Statistic")}')
        except IndexError:
            pass

    def keyPressEvent(self, event: QtGui.QKeyEvent):
        if type(event) is QtGui.QKeyEvent:
            if event.matches(QtGui.QKeySequence.StandardKey.Copy):
                # noinspection PyTypeChecker
                widget: StatWidget = self.tabWidget.currentWidget()
                table = []
                if widget.stat_details:
                    for r, d in widget.stat_details.items():
                        d.insert(0, r)
                        table.append('\t'.join([str(c) for c in d]))
                else:
                    for r in widget.stat_summary:
                        table.append('\t'.join([str(c) for c in r]))

                clip = QtWidgets.QApplication.clipboard()
                clip.setText('\r\n'.join(table))


class NavigationToolbar(NavigationToolbar2QT):
    toolitems = [t for t in NavigationToolbar2QT.toolitems if
                 t[0] in ('Home', 'Pan', 'Zoom', 'Save')]


class StatWidget(QtWidgets.QWidget):
    def __init__(self, *args, stat_summary: list[list], stat_details: dict[str, list] = None, **kwargs):
        super().__init__(*args, **kwargs)
        self.__stat_summary__: list[list] = stat_summary
        self.__stat_details__: dict[str, list] = stat_details

    @property
    def stat_summary(self) -> list[list]:
        return self.__stat_summary__

    @property
    def stat_details(self) -> dict[str, list]:
        return self.__stat_details__


class StatTableWidget(QtWidgets.QTableWidget, StatWidget):
    def __init__(self, *args, stat_summary: list[list], stat_details: dict[str, list] = None, **kwargs):
        super().__init__(*args, stat_summary=stat_summary, stat_details=stat_details, **kwargs)
        self.__stat_summary__: list[list] = stat_summary
        self.__stat_details__: dict[str, list] = stat_details
