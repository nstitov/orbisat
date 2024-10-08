# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'choose_ground_station_dialog.ui'
#
# Created by: PyQt5 UI code generator 5.15.9
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Dialog(object):
    def setupUi(self, Dialog):
        Dialog.setObjectName("Dialog")
        Dialog.resize(320, 260)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Dialog.sizePolicy().hasHeightForWidth())
        Dialog.setSizePolicy(sizePolicy)
        Dialog.setMinimumSize(QtCore.QSize(320, 260))
        Dialog.setMaximumSize(QtCore.QSize(320, 260))
        self.verticalLayoutWidget = QtWidgets.QWidget(Dialog)
        self.verticalLayoutWidget.setGeometry(QtCore.QRect(10, 0, 302, 259))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.verticalLayoutWidget.setFont(font)
        self.verticalLayoutWidget.setObjectName("verticalLayoutWidget")
        self.main_layout = QtWidgets.QVBoxLayout(self.verticalLayoutWidget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        self.main_layout.setSpacing(5)
        self.main_layout.setObjectName("main_layout")
        self.choose_station_text_label = QtWidgets.QLabel(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.choose_station_text_label.sizePolicy().hasHeightForWidth())
        self.choose_station_text_label.setSizePolicy(sizePolicy)
        self.choose_station_text_label.setMinimumSize(QtCore.QSize(300, 15))
        self.choose_station_text_label.setMaximumSize(QtCore.QSize(300, 15))
        font = QtGui.QFont()
        font.setFamily("Geneva")
        font.setPointSize(12)
        font.setItalic(False)
        self.choose_station_text_label.setFont(font)
        self.choose_station_text_label.setObjectName("choose_station_text_label")
        self.main_layout.addWidget(self.choose_station_text_label)
        self.available_stations_scroll_area = QtWidgets.QScrollArea(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.available_stations_scroll_area.sizePolicy().hasHeightForWidth())
        self.available_stations_scroll_area.setSizePolicy(sizePolicy)
        self.available_stations_scroll_area.setMinimumSize(QtCore.QSize(300, 200))
        self.available_stations_scroll_area.setMaximumSize(QtCore.QSize(300, 200))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.available_stations_scroll_area.setFont(font)
        self.available_stations_scroll_area.setWidgetResizable(True)
        self.available_stations_scroll_area.setObjectName("available_stations_scroll_area")
        self.scrollAreaWidgetContents = QtWidgets.QWidget()
        self.scrollAreaWidgetContents.setGeometry(QtCore.QRect(0, 0, 298, 198))
        self.scrollAreaWidgetContents.setObjectName("scrollAreaWidgetContents")
        self.available_stations_scroll_area.setWidget(self.scrollAreaWidgetContents)
        self.main_layout.addWidget(self.available_stations_scroll_area)
        self.buttons_layout = QtWidgets.QHBoxLayout()
        self.buttons_layout.setObjectName("buttons_layout")
        self.choose_selected_station_button = QtWidgets.QPushButton(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.choose_selected_station_button.sizePolicy().hasHeightForWidth())
        self.choose_selected_station_button.setSizePolicy(sizePolicy)
        self.choose_selected_station_button.setMinimumSize(QtCore.QSize(145, 30))
        self.choose_selected_station_button.setMaximumSize(QtCore.QSize(145, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.choose_selected_station_button.setFont(font)
        self.choose_selected_station_button.setObjectName("choose_selected_station_button")
        self.buttons_layout.addWidget(self.choose_selected_station_button)
        self.add_new_station_button = QtWidgets.QPushButton(self.verticalLayoutWidget)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(self.add_new_station_button.sizePolicy().hasHeightForWidth())
        self.add_new_station_button.setSizePolicy(sizePolicy)
        self.add_new_station_button.setMinimumSize(QtCore.QSize(145, 30))
        self.add_new_station_button.setMaximumSize(QtCore.QSize(145, 30))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.add_new_station_button.setFont(font)
        self.add_new_station_button.setObjectName("add_new_station_button")
        self.buttons_layout.addWidget(self.add_new_station_button)
        self.main_layout.addLayout(self.buttons_layout)

        self.retranslateUi(Dialog)
        QtCore.QMetaObject.connectSlotsByName(Dialog)

    def retranslateUi(self, Dialog):
        _translate = QtCore.QCoreApplication.translate
        Dialog.setWindowTitle(_translate("Dialog", "Dialog"))
        self.choose_station_text_label.setText(_translate("Dialog", "Choose available station or add new:"))
        self.choose_selected_station_button.setText(_translate("Dialog", "Choose selected station"))
        self.add_new_station_button.setText(_translate("Dialog", "Add new station"))
