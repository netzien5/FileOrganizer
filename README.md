# 📂 FileOrganizer Pro

![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=for-the-badge&logo=python)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)
![Status](https://img.shields.io/badge/Status-Stable-orange?style=for-the-badge)

A powerful, modern, and intelligent file organization tool built with **Python** and **CustomTkinter**.  
Stop wasting time manually sorting files—organize your Desktop, Downloads, and Documents with a single click.

## ✨ Key Features

* **🧠 Hybrid Smart Sorting:** Automatically categorizes known file types (Images, Docs, etc.) and creates dynamic folders for unknown extensions (e.g., `.xyz` -> `XYZ_Files`).
* **⚡ "Organize Everything" Mode:** Cleans up Desktop, Downloads, Documents, Pictures, Music, and Videos in one go.
* **↩️ Undo Functionality:** Made a mistake? Revert the last operation instantly with the Undo button.
* **⚙️ Settings & Custom Rules:** Define your own sorting rules via the Settings tab (e.g., move `.mp4` to `My_Movies`).
* **🛡️ Safe & Robust:**
    * **Skip Shortcuts:** Never moves `.lnk` (shortcuts) from the Desktop.
    * **Error Handling:** Skips open/locked files without crashing.
    * **Dry Run Mode:** Simulate the organization process before actually moving files.
* **🚀 High Performance:** Uses threading to prevent UI freezing during large file transfers.
* **🎨 Modern Dark UI:** Professional interface with real-time logs and progress bar.

## 🛠️ Installation

1.  **Clone the repository**
    ```bash
    git clone [https://github.com/netzien5/FileOrganizer.git](https://github.com/netzien5/FileOrganizer.git)
    cd FileOrganizer
    ```

2.  **Install Dependencies**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the Application**
    ```bash
    python main.py
    ```

## 📦 How to Build (.exe)

If you want to create a standalone executable file:

```bash
pip install pyinstaller
pyinstaller --noconsole --onefile --name=FileOrganizer main.py

