# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file '/home/cnc/Work/teachinlathe/src/teachinlathe/widgets/lathe_fixtures/lathe_fixture.ui'
#
# Created by: PyQt5 UI code generator 5.15.10
#
# WARNING: Any manual changes made to this file will be lost when pyuic5 is
# run again.  Do not edit this file unless you know what you are doing.


from PyQt5 import QtCore, QtGui, QtWidgets


class Ui_Form(object):
    def setupUi(self, Form):
        Form.setObjectName("Form")
        Form.resize(190, 220)
        sizePolicy = QtWidgets.QSizePolicy(QtWidgets.QSizePolicy.Fixed, QtWidgets.QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Form.sizePolicy().hasHeightForWidth())
        Form.setSizePolicy(sizePolicy)
        Form.setStyleSheet("")
        self.frame = QtWidgets.QFrame(Form)
        self.frame.setGeometry(QtCore.QRect(0, 0, 190, 220))
        self.frame.setFrameShape(QtWidgets.QFrame.StyledPanel)
        self.frame.setFrameShadow(QtWidgets.QFrame.Raised)
        self.frame.setObjectName("frame")
        self.label_6 = QtWidgets.QLabel(self.frame)
        self.label_6.setGeometry(QtCore.QRect(10, 115, 81, 21))
        self.label_6.setStyleSheet("font: 10pt \"Noto Sans\";")
        self.label_6.setObjectName("label_6")
        self.description = QtWidgets.QLabel(self.frame)
        self.description.setGeometry(QtCore.QRect(10, 10, 171, 61))
        font = QtGui.QFont()
        font.setFamily("Noto Sans")
        font.setPointSize(12)
        font.setBold(False)
        font.setItalic(False)
        font.setWeight(50)
        self.description.setFont(font)
        self.description.setStyleSheet("font: 12pt \"Noto Sans\";")
        self.description.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.description.setAlignment(QtCore.Qt.AlignCenter)
        self.description.setWordWrap(True)
        self.description.setObjectName("description")
        self.label_2 = QtWidgets.QLabel(self.frame)
        self.label_2.setGeometry(QtCore.QRect(10, 90, 81, 21))
        self.label_2.setStyleSheet("font: 10pt \"Noto Sans\";")
        self.label_2.setObjectName("label_2")
        self.maxRpm = QtWidgets.QLabel(self.frame)
        self.maxRpm.setGeometry(QtCore.QRect(90, 115, 46, 21))
        self.maxRpm.setStyleSheet("font: 10pt \"Noto Sans\";")
        self.maxRpm.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.maxRpm.setObjectName("maxRpm")
        self.units = QtWidgets.QLabel(self.frame)
        self.units.setGeometry(QtCore.QRect(140, 90, 36, 21))
        self.units.setStyleSheet("font: 10pt \"Noto Sans\";")
        self.units.setAlignment(QtCore.Qt.AlignCenter)
        self.units.setObjectName("units")
        self.diameter = QtWidgets.QLabel(self.frame)
        self.diameter.setGeometry(QtCore.QRect(100, 90, 36, 21))
        self.diameter.setStyleSheet("font: 10pt \"Noto Sans\";")
        self.diameter.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.diameter.setObjectName("diameter")
        self.groupBox = QtWidgets.QGroupBox(self.frame)
        self.groupBox.setGeometry(QtCore.QRect(10, 140, 171, 71))
        font = QtGui.QFont()
        font.setPointSize(10)
        self.groupBox.setFont(font)
        self.groupBox.setObjectName("groupBox")
        self.teachZMinus = QtWidgets.QPushButton(self.groupBox)
        self.teachZMinus.setGeometry(QtCore.QRect(90, 30, 71, 31))
        self.teachZMinus.setObjectName("teachZMinus")
        self.zMinusLimit = TeachInLineEdit(self.groupBox)
        self.zMinusLimit.setEnabled(False)
        self.zMinusLimit.setGeometry(QtCore.QRect(10, 30, 71, 31))
        self.zMinusLimit.setAlignment(QtCore.Qt.AlignRight|QtCore.Qt.AlignTrailing|QtCore.Qt.AlignVCenter)
        self.zMinusLimit.setProperty("referenceType", 0)
        self.zMinusLimit.setProperty("axisNumber", 2)
        self.zMinusLimit.setProperty("latheMode", 0)
        self.zMinusLimit.setObjectName("zMinusLimit")
        self.line = QtWidgets.QFrame(self.frame)
        self.line.setGeometry(QtCore.QRect(0, 70, 191, 20))
        self.line.setFrameShape(QtWidgets.QFrame.HLine)
        self.line.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.line.setObjectName("line")

        self.retranslateUi(Form)
        QtCore.QMetaObject.connectSlotsByName(Form)

    def retranslateUi(self, Form):
        _translate = QtCore.QCoreApplication.translate
        Form.setWindowTitle(_translate("Form", "Form"))
        self.label_6.setText(_translate("Form", "Max RPM:"))
        self.description.setText(_translate("Form", "Rohm 3 Jaws chuck with a long long text that might wrap"))
        self.label_2.setText(_translate("Form", "Diameter:"))
        self.maxRpm.setText(_translate("Form", "2000"))
        self.units.setText(_translate("Form", "mm"))
        self.diameter.setText(_translate("Form", "000"))
        self.groupBox.setTitle(_translate("Form", "Z-  G53 limit"))
        self.teachZMinus.setText(_translate("Form", "TeachIn"))
        self.zMinusLimit.setText(_translate("Form", "000.000"))
        self.zMinusLimit.setProperty("inchFormat", _translate("Form", "%9.4f"))
        self.zMinusLimit.setProperty("millimeterFormat", _translate("Form", "%10.3f"))
        self.zMinusLimit.setProperty("degreeFormat", _translate("Form", "%10.2f"))
from qtpyvcp.widgets.input_widgets.teachin_line_edit import TeachInLineEdit
