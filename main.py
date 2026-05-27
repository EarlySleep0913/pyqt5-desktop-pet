#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

if __name__ == "__main__":
    QApplication.setAttribute(Qt.AA_DisableHighDpiScaling)
    QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.Floor)

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    from pet import PetWidget
    pet = PetWidget()
    pet.show()

    sys.exit(app.exec_())
