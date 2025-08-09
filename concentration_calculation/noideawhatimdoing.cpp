#include <QApplication>
#include <QInputDialog>
#include <QDialog>
#include <QVBoxLayout>
#include <QHBoxLayout>
#include <QLabel>
#include <QLineEdit>
#include <QPushButton>
#include <QMessageBox>
#include<bits/stdc++.h>

using namespace std;

class CatNamesDialog : public QDialog {
public:
    CatNamesDialog(int numCats, QWidget* parent = nullptr) : QDialog(parent) {
        setWindowTitle("Enter Cat Names");
        QVBoxLayout* mainLayout = new QVBoxLayout(this);

        for (int i = 0; i < numCats; ++i) {
            QHBoxLayout* row = new QHBoxLayout();
            QLabel* label = new QLabel(QString("Cat %1:").arg(i+1), this);
            QLineEdit* edit = new QLineEdit(this);
            edits.push_back(edit);
            row->addWidget(label);
            row->addWidget(edit);
            mainLayout->addLayout(row);
        }

        QHBoxLayout* buttons = new QHBoxLayout();
        QPushButton* ok = new QPushButton("OK", this);
        QPushButton* cancel = new QPushButton("Cancel", this);
        connect(ok, &QPushButton::clicked, this, &QDialog::accept);
        connect(cancel, &QPushButton::clicked, this, &QDialog::reject);
        buttons->addWidget(ok);
        buttons->addWidget(cancel);
        mainLayout->addLayout(buttons);
    }

    vector<string> getNames() const {
        vector<string> names;
        for (auto e : edits) {
            names.push_back(e->text().toStdString());
        }
        return names;
    }

private:
    vector<QLineEdit*> edits;
};

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);


    
    // Step 1: Ask for number of cats
    bool ok;
    int numCats = QInputDialog::getInt(nullptr, "Number of Cats",
                                       "Enter number of cats:",
                                       1, 1, 100, 1, &ok);
    if (!ok) return 0;
    cout << "you have " << numCats << " cats" << endl;
    // Step 2: Ask for cat names
    // CatNamesDialog dialog(numCats);
    // if (dialog.exec() == QDialog::Accepted) {
    //     auto names = dialog.getNames();
    //     QString msg = "Your cats are:\n";
    //     for (const auto& name : names) {
    //         msg += QString::fromStdString(name) + "\n";
    //     }
    //     QMessageBox::information(nullptr, "Cat List", msg);
    // }

    return 0;
}
