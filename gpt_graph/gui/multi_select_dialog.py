import sys
from PyQt5.QtWidgets import QApplication, QDialog, QListWidget, QVBoxLayout, QPushButton, QHBoxLayout

class MultiSelectDialog(QDialog):
    def __init__(self, options):
        super().__init__()
        self.options = options
        self.selectedIndices = []
        self.initUI()

    def initUI(self):
        # Layout
        layout = QVBoxLayout()

        # List widget for multi selection
        self.listWidget = QListWidget(self)
        self.listWidget.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.listWidget)

        # Populate the list widget with provided options
        for index, option in enumerate(self.options):
            self.listWidget.addItem(f"{index}: {option}")

        # Button layout
        buttonLayout = QHBoxLayout()

        # Confirm selection button
        self.confirmButton = QPushButton("Confirm", self)
        self.confirmButton.clicked.connect(self.confirmSelections)
        buttonLayout.addWidget(self.confirmButton)

        # Add button layout to main layout
        layout.addLayout(buttonLayout)

        # Set the layout on the dialog
        self.setLayout(layout)

    def confirmSelections(self):
        self.selectedIndices = [self.listWidget.row(item) for item in self.listWidget.selectedItems()]
        self.accept()  # Close the dialog and set return value to QDialog.Accepted

def multi_select_dialog(options):
    app = QApplication(sys.argv)
    dialog = MultiSelectDialog(options)
    if dialog.exec() == QDialog.Accepted:
        print("Selected indices:", dialog.selectedIndices)
        return dialog.selectedIndices
    else:
        print("No selection made or dialog cancelled.")
    return []

# Example usage
if __name__ == '__main__':
    options = ["Option 1", "Option 2", "Option 3", "Option 4", "Option 5"]
    selected_indices = multi_select(options)
    print("Final selected indices:", selected_indices)