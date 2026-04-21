import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, filedialog


IGNORE_DIRS = {
    'venv', '.venv', 'env', '.git', '.idea', '__pycache__',
    'node_modules', '.vscode', 'build', 'dist', 'target',
    'logs', 'temp', 'tmp', 'obj', 'bin'
}

ALLOWED_EXTENSIONS = {
    '.py', '.js', '.ts', '.html', '.css', '.scss',
    '.json', '.yaml', '.yml', '.xml', '.txt', '.md',
    '.sql', '.sh', '.bat', '.env', '.dockerfile', '.c', '.cpp', '.h', '.cs',
    '.go', '.rs', '.php', '.rb', '.java', '.kt'
}


def resource_path(relative_path: str):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath('.')
    return os.path.join(base_path, relative_path)


class ProjectScannerApp:
    def __init__(self, root):
        self.root = root
        try:
            self.root.iconbitmap(resource_path('Merger.ico'))
        except:
            pass
        self.root.title('Project to Text Merger')
        self.root.geometry('700x900')

        self.project_path = tk.StringVar(value=os.getcwd())
        self.is_processing = False

        self.setup_ui()
        self.refresh_tree()

    def setup_ui(self):
        # Верхняя панель управления
        top_frame = ttk.Frame(self.root, padding="10")
        top_frame.pack(fill=tk.X)

        ttk.Label(top_frame, text='Путь:').pack(side=tk.LEFT)
        self.path_entry = ttk.Entry(top_frame, textvariable=self.project_path, width=50)
        self.path_entry.pack(side=tk.LEFT, padx=5)

        self.browse_btn = ttk.Button(top_frame, text='Обзор', command=self.browse_folder)
        self.browse_btn.pack(side=tk.LEFT)

        self.refresh_btn = ttk.Button(top_frame, text='Обновить', command=self.refresh_tree)
        self.refresh_btn.pack(side=tk.LEFT, padx=5)

        # Панель массового выбора
        select_frame = ttk.Frame(self.root, padding='5')
        select_frame.pack(fill=tk.X)
        ttk.Button(select_frame, text='☑ Выбрать всё', command=lambda: self.set_all_checks('☑')).pack(side=tk.LEFT,
                                                                                                      padx=10)
        ttk.Button(select_frame, text='☐ Снять всё', command=lambda: self.set_all_checks('☐')).pack(side=tk.LEFT)

        # Дерево файлов
        tree_frame = ttk.Frame(self.root, padding='10')
        tree_frame.pack(fill=tk.BOTH, expand=True)

        self.tree = ttk.Treeview(tree_frame, columns=('full_path'), displaycolumns=())
        self.tree.heading('#0', text='Структура проекта (Двойной клик или Пробел для выбора)', anchor=tk.W)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.status_var = tk.StringVar(value="Готов")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.tree.bind('<Double-1>', self.toggle_node)
        self.tree.bind('<space>', self.toggle_node)

        btn_frame = ttk.Frame(self.root, padding='10')
        btn_frame.pack(fill=tk.X)

        style = ttk.Style()
        style.configure('Action.TButton', font=('Helvetica', 10, 'bold'))

        self.generate_btn = ttk.Button(
            btn_frame, text='СОБРАТЬ КОНТЕКСТ',
            style='Action.TButton', command=self.start_generate_context
        )
        self.generate_btn.pack(fill=tk.X, ipady=10)

    def set_ui_state(self, state):
        """Включает или выключает кнопки управления"""
        self.is_processing = (state == tk.DISABLED)
        self.refresh_btn.config(state=state)
        self.browse_btn.config(state=state)
        self.generate_btn.config(state=state)
        self.path_entry.config(state=state)

    def browse_folder(self):
        path = filedialog.askdirectory()
        if path:
            self.project_path.set(path)
            self.refresh_tree()

    def refresh_tree(self):
        if self.is_processing: return
        self.tree.delete(*self.tree.get_children())
        root_path = self.project_path.get()
        if not os.path.exists(root_path):
            return

        self.set_ui_state(tk.DISABLED)
        self.status_var.set('Сканирование директорий...')

        thread = threading.Thread(target=self._scan_worker, args=(root_path,), daemon=True)
        thread.start()

    def _scan_worker(self, root_path):
        """Воркер для сканирования файлов в потоке"""
        try:
            self.root.after(0, self._insert_node_async, '', root_path)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('Ошибка', str(e)))
        finally:
            self.root.after(100, lambda: self.status_var.set('Готов'))
            self.root.after(100, lambda: self.set_ui_state(tk.NORMAL))

    def _insert_node_async(self, parent, path):
        name = os.path.basename(path)
        if not name:
            name = path

        if name in IGNORE_DIRS:
            return

        if os.path.isfile(path):
            ext = os.path.splitext(path)[1].lower()
            if ext not in ALLOWED_EXTENSIONS and name.lower() != 'dockerfile':
                return

        node = self.tree.insert(parent, 'end', text=f'☑ {name}', open=True, values=(path,))

        if os.path.isdir(path):
            try:
                items = sorted(os.listdir(path), key=lambda x: (not os.path.isdir(os.path.join(path, x)), x.lower()))
                for item in items:
                    self._insert_node_async(node, os.path.join(path, item))
            except PermissionError:
                pass


    def toggle_node(self, event):
        selection = self.tree.selection()
        if not selection: return
        item = selection[0]
        text = self.tree.item(item, 'text')

        new_char = '☐' if text.startswith('☑') else '☑'
        self.update_node_recursive(item, new_char)

    def update_node_recursive(self, item, char):
        text = self.tree.item(item, 'text')
        self.tree.item(item, text=f'{char} {text[2:]}')
        for child in self.tree.get_children(item):
            self.update_node_recursive(child, char)

    def set_all_checks(self, char):
        for item in self.tree.get_children():
            self.update_node_recursive(item, char)

    def start_generate_context(self):
        if self.is_processing: return

        selected_files = []

        def collect_selected(item):
            text = self.tree.item(item, 'text')
            path = self.tree.item(item, 'values')[0]
            if text.startswith('☑') and os.path.isfile(path):
                selected_files.append(path)
            for child in self.tree.get_children(item):
                collect_selected(child)

        for root_item in self.tree.get_children():
            collect_selected(root_item)

        if not selected_files:
            messagebox.showwarning('Внимание', 'Выберите хотя бы один файл!')
            return

        self.set_ui_state(tk.DISABLED)
        self.status_var.set(f'Сборка контекста ({len(selected_files)} файлов)...')

        thread = threading.Thread(target=self._generate_worker, args=(selected_files,), daemon=True)
        thread.start()

    def _generate_worker(self, selected_files):
        root_path = self.project_path.get()
        output_file = os.path.join(root_path, 'project_context.md')

        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('# PROJECT CONTEXT FOR AI\n\n')

                f.write('## Project Structure\n')
                f.write('```mermaid\ngraph TD\n')
                f.write(f'    Root[\"{os.path.basename(root_path)}\"]\n')
                for file in selected_files:
                    rel = os.path.relpath(file, root_path)
                    f.write(f'    Root --> {rel}\n')
                f.write('```\n\n')

                f.write('## File Contents\n\n')
                for file_path in selected_files:
                    rel_path = os.path.relpath(file_path, root_path)
                    ext = os.path.splitext(file_path)[1][1:] or 'txt'

                    f.write(f'<file path=\"{rel_path}\">\n')
                    f.write(f'```{ext}\n')
                    try:
                        with open(file_path, 'r', encoding='utf-8', errors='replace') as content:
                            f.write(content.read())
                    except Exception as e:
                        f.write(f'Error reading file: {e}')
                    f.write(f'\n```\n</file>\n\n')

            self.root.after(0, lambda: messagebox.showinfo('Успех', f'Контекст сохранен в:\n{output_file}'))
            if os.name == 'nt': os.startfile(output_file)
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror('Ошибка', str(e)))
        finally:
            self.root.after(0, lambda: self.status_var.set('Готов'))
            self.root.after(0, lambda: self.set_ui_state(tk.NORMAL))


if __name__ == '__main__':
    root = tk.Tk()
    app = ProjectScannerApp(root)
    root.mainloop()
