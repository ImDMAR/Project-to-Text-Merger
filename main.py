import os
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# --- КОНФИГУРАЦИЯ ---
IGNORE_DIRS = {
    'venv', '.venv', 'env', '.git', '.idea', '__pycache__',
    'node_modules', '.vscode', 'build', 'dist', 'target',
    'logs', 'temp', 'tmp', 'assets', 'media', 'obj', 'bin'
}

ALLOWED_EXTENSIONS = {
    '.py', '.js', '.ts', '.html', '.css', '.scss',
    '.json', '.yaml', '.yml', '.xml', '.txt', '.md',
    '.sql', '.sh', '.bat', '.env', '.dockerfile', '.c', '.cpp', '.h', '.cs'
}


class ProjectScannerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Project to Text Merger")
        self.root.geometry("700x900")  # Исправлено: формат "ШиринаxВысота"

        self.project_path = tk.StringVar(value=os.getcwd())

        self.setup_ui()
        self.refresh_tree()

    def setup_ui(self):
        # Верхняя панель управления
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text="Путь:").pack(side=tk.LEFT)
        ttk.Entry(top_frame, textvariable=self.project_path, width=50).pack(side=tk.LEFT, padx=5)
        ttk.Button(top_frame, text="Обзор", command=self.browse_folder).pack(side=tk.LEFT)
        ttk.Button(top_frame, text="Обновить", command=self.refresh_tree).pack(side=tk.LEFT, padx=5)

        # Панель массового выбора
        select_frame = ttk.Frame(self.root, padding="5")
        select_frame.pack(fill=tk.X)
        ttk.Button(select_frame, text="☑ Выбрать всё", command=lambda: self.set_all_checks("☑")).pack(side=tk.LEFT,
                                                                                                      padx=10)
        ttk.Button(select_frame, text="☐ Снять всё", command=lambda: self.set_all_checks("☐")).pack(side=tk.LEFT)

        # Дерево файлов
        tree_frame = ttk.Frame(self.root, padding="10")
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=("full_path"), displaycolumns=())
        self.tree.heading("#0", text="Структура проекта (Двойной клик или Пробел для выбора)", anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # События
        self.tree.bind("<Double-1>", self.toggle_node)
        self.tree.bind("<space>", self.toggle_node)

        # Нижняя кнопка
        btn_frame = ttk.Frame(self.root, padding="10")
        btn_frame.pack(fill=tk.X)

        style = ttk.Style()
        style.configure("Action.TButton", font=('Helvetica', 10, 'bold'))

        ttk.Button(btn_frame, text="СГЕНЕРИРОВАТЬ КОНТЕКСТ ДЛЯ ИИ",
                   style="Action.TButton", command=self.generate_context).pack(fill=tk.X, ipady=10)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.project_path.set(path)
            self.refresh_tree()

    def refresh_tree(self):
        self.tree.delete(*self.tree.get_children())
        root_path = self.project_path.get()
        if not os.path.exists(root_path):
            return
        self.insert_node("", root_path)

    def insert_node(self, parent, path):
        name = os.path.basename(path)
        if not name: name = path

        if name in IGNORE_DIRS:
            return

        # По умолчанию ставим галочку ☑
        node = self.tree.insert(parent, "end", text=f"☑ {name}", open=True, values=(path,))

        if os.path.isdir(path):
            try:
                items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
                for item in items:
                    self.insert_node(node, os.path.join(path, item))
            except PermissionError:
                pass
        else:
            ext = os.path.splitext(path)[1].lower()
            if ext not in ALLOWED_EXTENSIONS and name != 'Dockerfile':
                self.tree.delete(node)

    def toggle_node(self, event):
        selection = self.tree.selection()
        if not selection: return
        item = selection[0]
        text = self.tree.item(item, "text")

        if text.startswith("☑"):
            new_char = "☐"
        else:
            new_char = "☑"

        self.update_node_recursive(item, new_char)

    def update_node_recursive(self, item, char):
        text = self.tree.item(item, "text")
        self.tree.item(item, text=f"{char} {text[2:]}")
        for child in self.tree.get_children(item):
            self.update_node_recursive(child, char)

    def set_all_checks(self, char):
        for item in self.tree.get_children():
            self.update_node_recursive(item, char)

    def generate_context(self):
        root_path = self.project_path.get()
        output_file = os.path.join(root_path, "ai_project_context.md")

        selected_files = []

        def collect_selected(item):
            text = self.tree.item(item, "text")
            path = self.tree.item(item, "values")[0]
            if text.startswith("☑") and os.path.isfile(path):
                selected_files.append(path)
            for child in self.tree.get_children(item):
                collect_selected(child)

        for root_item in self.tree.get_children():
            collect_selected(root_item)

        if not selected_files:
            messagebox.showwarning("Внимание", "Выберите хотя бы один файл!")
            return

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write("# PROJECT CONTEXT FOR AI\n\n")

                # 1. Mermaid Diagram
                f.write("## Project Structure\n")
                f.write("```mermaid\ngraph TD\n")
                f.write(f"    Root[\"{os.path.basename(root_path)}\"]\n")
                for file in selected_files:
                    rel = os.path.relpath(file, root_path)
                    # Упрощенная визуализация для Mermaid
                    f.write(f"    Root --> {rel.replace(os.sep, '/')}\n")
                f.write("```\n\n")

                # 2. File Contents
                f.write("## File Contents\n\n")
                for file_path in selected_files:
                    rel_path = os.path.relpath(file_path, root_path)
                    ext = os.path.splitext(file_path)[1][1:] or "txt"

                    f.write(f"<file path=\"{rel_path}\">\n")
                    f.write(f"```{ext}\n")
                    try:
                        with open(file_path, 'r', encoding='utf-8') as content:
                            f.write(content.read())
                    except Exception as e:
                        f.write(f"Error reading file: {e}")
                    f.write(f"\n```\n</file>\n\n")

            messagebox.showinfo("Успех", f"Контекст сохранен в:\n{output_file}")
            # Открываем файл после создания
            if os.name == 'nt': os.startfile(output_file)
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    root = tk.Tk()
    app = ProjectScannerApp(root)
    root.mainloop()
