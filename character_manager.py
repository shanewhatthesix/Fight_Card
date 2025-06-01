# character_manager.py
import json
import os
import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext

DATA_FILE = 'data/characters.json'
ELEMENTS = ["金", "木", "水", "火", "土", "风", "雷", "毒", "法", "圣", "精神"]

def load_characters():
    """从JSON文件加载角色数据"""
    if not os.path.exists(DATA_FILE):
        return {"characters": []}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        messagebox.showerror("错误", "characters.json 文件格式错误，将创建新文件。")
        return {"characters": []}

def save_characters(data):
    """将角色数据保存到JSON文件"""
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        messagebox.showerror("保存错误", f"保存文件时发生错误: {e}")
        return False

class CharacterManagerGUI:
    def __init__(self, master):
        self.master = master
        master.title("角色管理工具")
        master.geometry("800x600")

        self.data = load_characters()

        self.create_widgets()
        self.refresh_character_list()

    def create_widgets(self):
        # 主框架
        self.main_frame = ttk.Frame(self.master, padding="10")
        self.main_frame.pack(fill=tk.BOTH, expand=True)

        # 角色列表区域
        self.list_frame = ttk.LabelFrame(self.main_frame, text="角色列表", padding="10")
        self.list_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.character_tree = ttk.Treeview(self.list_frame, columns=("ID", "姓名", "HP", "元素"), show="headings")
        self.character_tree.heading("ID", text="ID")
        self.character_tree.heading("姓名", text="姓名")
        self.character_tree.heading("HP", text="HP")
        self.character_tree.heading("元素", text="元素")
        self.character_tree.column("ID", width=50, anchor=tk.CENTER)
        self.character_tree.column("姓名", width=150)
        self.character_tree.column("HP", width=80, anchor=tk.CENTER)
        self.character_tree.column("元素", width=100)
        self.character_tree.pack(fill=tk.BOTH, expand=True)

        self.character_tree.bind("<Double-1>", self.on_character_select)

        # 按钮区域
        self.button_frame = ttk.Frame(self.main_frame, padding="10")
        self.button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=5, pady=5)

        ttk.Button(self.button_frame, text="刷新列表", command=self.refresh_character_list).pack(fill=tk.X, pady=5)
        ttk.Button(self.button_frame, text="添加角色", command=self.open_add_character_window).pack(fill=tk.X, pady=5)
        ttk.Button(self.button_frame, text="编辑角色", command=self.open_edit_character_window).pack(fill=tk.X, pady=5)
        ttk.Button(self.button_frame, text="删除角色", command=self.delete_character).pack(fill=tk.X, pady=5)
        ttk.Button(self.button_frame, text="查看详情", command=self.view_character_details).pack(fill=tk.X, pady=5)

    def refresh_character_list(self):
        """刷新角色列表显示"""
        for i in self.character_tree.get_children():
            self.character_tree.delete(i)
        
        self.data = load_characters() # 重新加载数据以确保最新
        for char in self.data['characters']:
            self.character_tree.insert("", tk.END, iid=char['id'], 
                                       values=(char['id'], char['name'], char['stats']['hp'], char['element']))

    def on_character_select(self, event):
        """双击列表项时打开编辑窗口"""
        selected_item = self.character_tree.selection()
        if selected_item:
            char_id = int(selected_item[0]) # 直接使用item_id作为char_id
            self.open_edit_character_window(char_id)

    def view_character_details(self):
        """查看选定角色的详细信息"""
        selected_item = self.character_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个角色。")
            return
        
        char_id = int(selected_item[0]) # 直接使用item_id作为char_id
        character = next((c for c in self.data['characters'] if c['id'] == char_id), None)

        if character:
            detail_window = tk.Toplevel(self.master)
            detail_window.title(f"角色详情: {character['name']}")
            detail_window.geometry("500x400")

            details_text = scrolledtext.ScrolledText(detail_window, wrap=tk.WORD, width=60, height=20)
            details_text.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            details_str = f"ID: {character['id']}\n"
            details_str += f"姓名: {character['name']}\n"
            details_str += f"HP: {character['stats']['hp']}\n"
            details_str += f"攻击: {character['stats']['atk']}\n"
            details_str += "技能:\n"
            for skill in character['skills']:
                details_str += f"  - 名称: {skill['name']}, 效果: {skill['effect']}, 伤害: {skill['damage']}\n"
            details_str += f"图片: {character['image']}\n"
            details_str += f"音频: {character['audio']}\n"
            details_str += "属性:\n"
            for attr in character['attributes']:
                details_str += f"  - 名称: {attr['name']}, 抗性: {attr['resistance']}\n"
            details_str += f"元素: {character['element']}\n"

            details_text.insert(tk.END, details_str)
            details_text.config(state=tk.DISABLED) # 禁止编辑

    def open_add_character_window(self):
        """打开添加角色窗口"""
        AddEditCharacterWindow(self.master, self.data, self.refresh_character_list)

    def open_edit_character_window(self, char_id=None):
        """打开编辑角色窗口"""
        if char_id is None:
            selected_item = self.character_tree.selection()
            if not selected_item:
                messagebox.showwarning("警告", "请先选择一个角色进行编辑。")
                return
            char_id = int(selected_item[0]) # 直接使用item_id作为char_id
        
        character = next((c for c in self.data['characters'] if c['id'] == char_id), None)
        if character:
            AddEditCharacterWindow(self.master, self.data, self.refresh_character_list, character)
        else:
            messagebox.showerror("错误", f"未找到ID为 {char_id} 的角色。")

    def delete_character(self):
        """删除选定角色"""
        selected_item = self.character_tree.selection()
        if not selected_item:
            messagebox.showwarning("警告", "请先选择一个角色进行删除。")
            return
        
        char_id = int(selected_item[0]) # 直接使用item_id作为char_id
        char_name = self.character_tree.item(selected_item[0], 'values')[1]

        if messagebox.askyesno("确认删除", f"确定要删除角色 '{char_name}' (ID: {char_id}) 吗？"):
            original_len = len(self.data['characters'])
            self.data['characters'] = [char for char in self.data['characters'] if char['id'] != char_id]
            if len(self.data['characters']) < original_len:
                if save_characters(self.data):
                    messagebox.showinfo("成功", f"角色 '{char_name}' (ID: {char_id}) 已删除。")
                    self.refresh_character_list()
            else:
                messagebox.showerror("错误", f"删除失败，未找到ID为 {char_id} 的角色。")

class AddEditCharacterWindow(tk.Toplevel):
    def __init__(self, master, data, refresh_callback, character=None):
        super().__init__(master)
        self.data = data
        self.refresh_callback = refresh_callback
        self.character = character # 如果是编辑模式，则为角色数据

        if self.character:
            self.title(f"编辑角色: {self.character['name']}")
        else:
            self.title("添加新角色")
        self.geometry("600x700")
        self.create_form_widgets()
        if self.character:
            self.load_character_data()

    def create_form_widgets(self):
        self.form_frame = ttk.Frame(self, padding="10")
        self.form_frame.pack(fill=tk.BOTH, expand=True)

        # 使用Canvas和Scrollbar来处理滚动
        self.canvas = tk.Canvas(self.form_frame)
        self.scrollbar = ttk.Scrollbar(self.form_frame, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = ttk.Frame(self.canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(
                scrollregion=self.canvas.bbox("all")
            )
        )

        self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # 角色基本信息
        ttk.Label(self.scrollable_frame, text="姓名:").grid(row=0, column=0, sticky=tk.W, pady=2)
        self.name_entry = ttk.Entry(self.scrollable_frame, width=40)
        self.name_entry.grid(row=0, column=1, sticky=tk.EW, pady=2)

        ttk.Label(self.scrollable_frame, text="HP:").grid(row=1, column=0, sticky=tk.W, pady=2)
        self.hp_entry = ttk.Entry(self.scrollable_frame, width=40)
        self.hp_entry.grid(row=1, column=1, sticky=tk.EW, pady=2)

        ttk.Label(self.scrollable_frame, text="图片文件名:").grid(row=2, column=0, sticky=tk.W, pady=2)
        self.image_entry = ttk.Entry(self.scrollable_frame, width=40)
        self.image_entry.grid(row=2, column=1, sticky=tk.EW, pady=2)

        ttk.Label(self.scrollable_frame, text="音频文件名:").grid(row=3, column=0, sticky=tk.W, pady=2)
        self.audio_entry = ttk.Entry(self.scrollable_frame, width=40)
        self.audio_entry.grid(row=3, column=1, sticky=tk.EW, pady=2)

        ttk.Label(self.scrollable_frame, text="元素:").grid(row=4, column=0, sticky=tk.W, pady=2)
        self.element_entry = ttk.Entry(self.scrollable_frame, width=40)
        self.element_entry.grid(row=4, column=1, sticky=tk.EW, pady=2)

        # 攻击属性
        ttk.Label(self.scrollable_frame, text="攻击属性:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.atk_entries = {}
        for i, elem in enumerate(ELEMENTS):
            ttk.Label(self.scrollable_frame, text=f"  {elem}:").grid(row=6+i, column=0, sticky=tk.W, padx=10)
            entry = ttk.Entry(self.scrollable_frame, width=10)
            entry.grid(row=6+i, column=1, sticky=tk.W)
            self.atk_entries[elem] = entry
        
        # 技能
        self.skill_frame = ttk.LabelFrame(self.scrollable_frame, text="技能", padding="5")
        self.skill_frame.grid(row=6+len(ELEMENTS), column=0, columnspan=2, sticky=tk.EW, pady=10)
        self.skills_data = [] # 存储技能数据
        self.skill_widgets = [] # 存储技能相关的Entry和Button
        self.add_skill_button = ttk.Button(self.skill_frame, text="添加技能", command=self.add_skill_field)
        self.add_skill_button.pack(pady=5)
        self.render_skills()

        # 属性
        self.attribute_frame = ttk.LabelFrame(self.scrollable_frame, text="属性", padding="5")
        self.attribute_frame.grid(row=6+len(ELEMENTS)+1, column=0, columnspan=2, sticky=tk.EW, pady=10)
        self.attributes_data = [] # 存储属性数据
        self.attribute_widgets = [] # 存储属性相关的Entry和Button
        self.add_attribute_button = ttk.Button(self.attribute_frame, text="添加属性", command=self.add_attribute_field)
        self.add_attribute_button.pack(pady=5)
        self.render_attributes()

        # 保存按钮
        ttk.Button(self.form_frame, text="保存角色", command=self.save_character).pack(pady=10)

    def load_character_data(self):
        """加载现有角色数据到表单"""
        self.name_entry.insert(0, self.character['name'])
        self.hp_entry.insert(0, self.character['stats']['hp'])
        self.image_entry.insert(0, self.character['image'])
        self.audio_entry.insert(0, self.character['audio'])
        self.element_entry.insert(0, self.character['element'])

        for elem, entry in self.atk_entries.items():
            entry.insert(0, self.character['stats']['atk'].get(elem, 0))
        
        self.skills_data = self.character['skills'][:] # 复制一份，避免直接修改
        self.render_skills()

        self.attributes_data = self.character['attributes'][:] # 复制一份
        self.render_attributes()

    def add_skill_field(self, skill_data=None):
        """动态添加技能输入字段"""
        skill_row_frame = ttk.Frame(self.skill_frame, borderwidth=1, relief="solid", padding="5")
        skill_row_frame.pack(fill=tk.X, pady=2)
        
        skill_name_label = ttk.Label(skill_row_frame, text="技能名称:")
        skill_name_label.grid(row=0, column=0, sticky=tk.W)
        skill_name_entry = ttk.Entry(skill_row_frame, width=30)
        skill_name_entry.grid(row=0, column=1, sticky=tk.EW)

        skill_effect_label = ttk.Label(skill_row_frame, text="技能效果:")
        skill_effect_label.grid(row=1, column=0, sticky=tk.W)
        skill_effect_entry = ttk.Entry(skill_row_frame, width=30)
        skill_effect_entry.grid(row=1, column=1, sticky=tk.EW)

        damage_entries = {}
        ttk.Label(skill_row_frame, text="伤害属性:").grid(row=2, column=0, sticky=tk.W)
        damage_frame = ttk.Frame(skill_row_frame)
        damage_frame.grid(row=2, column=1, sticky=tk.EW)
        for i, elem in enumerate(ELEMENTS):
            ttk.Label(damage_frame, text=f"{elem}:").grid(row=i//4, column=(i%4)*2, sticky=tk.W)
            entry = ttk.Entry(damage_frame, width=5)
            entry.grid(row=i//4, column=(i%4)*2+1, sticky=tk.W)
            damage_entries[elem] = entry

        remove_button = ttk.Button(skill_row_frame, text="移除技能", command=lambda: self.remove_skill_field(skill_row_frame))
        remove_button.grid(row=0, column=2, sticky=tk.E)

        self.skill_widgets.append({
            "frame": skill_row_frame,
            "name_entry": skill_name_entry,
            "effect_entry": skill_effect_entry,
            "damage_entries": damage_entries
        })

        if skill_data:
            skill_name_entry.insert(0, skill_data.get('name', ''))
            skill_effect_entry.insert(0, skill_data.get('effect', ''))
            for elem, val in skill_data.get('damage', {}).items():
                if elem in damage_entries:
                    damage_entries[elem].insert(0, val)
        
        # 重新打包添加技能按钮，确保它总是在最后
        self.add_skill_button.pack_forget()
        self.add_skill_button.pack(pady=5)
        self.update_scroll_region()

    def remove_skill_field(self, frame_to_remove):
        """移除技能输入字段"""
        for widget_set in self.skill_widgets:
            if widget_set["frame"] == frame_to_remove:
                self.skill_widgets.remove(widget_set)
                break
        frame_to_remove.destroy()
        self.update_scroll_region()

    def render_skills(self):
        """渲染所有技能字段"""
        for widget_set in self.skill_widgets:
            widget_set["frame"].destroy()
        self.skill_widgets = []
        for skill_data in self.skills_data:
            self.add_skill_field(skill_data)

    def add_attribute_field(self, attribute_data=None):
        """动态添加属性输入字段"""
        attribute_row_frame = ttk.Frame(self.attribute_frame, borderwidth=1, relief="solid", padding="5")
        attribute_row_frame.pack(fill=tk.X, pady=2)

        attr_name_label = ttk.Label(attribute_row_frame, text="属性名称:")
        attr_name_label.grid(row=0, column=0, sticky=tk.W)
        attr_name_entry = ttk.Entry(attribute_row_frame, width=30)
        attr_name_entry.grid(row=0, column=1, sticky=tk.EW)

        resistance_entries = {}
        ttk.Label(attribute_row_frame, text="抗性属性:").grid(row=1, column=0, sticky=tk.W)
        resistance_frame = ttk.Frame(attribute_row_frame)
        resistance_frame.grid(row=1, column=1, sticky=tk.EW)
        for i, elem in enumerate(ELEMENTS):
            ttk.Label(resistance_frame, text=f"{elem}:").grid(row=i//4, column=(i%4)*2, sticky=tk.W)
            entry = ttk.Entry(resistance_frame, width=5)
            entry.grid(row=i//4, column=(i%4)*2+1, sticky=tk.W)
            resistance_entries[elem] = entry

        remove_button = ttk.Button(attribute_row_frame, text="移除属性", command=lambda: self.remove_attribute_field(attribute_row_frame))
        remove_button.grid(row=0, column=2, sticky=tk.E)

        self.attribute_widgets.append({
            "frame": attribute_row_frame,
            "name_entry": attr_name_entry,
            "resistance_entries": resistance_entries
        })

        if attribute_data:
            attr_name_entry.insert(0, attribute_data.get('name', ''))
            for elem, val in attribute_data.get('resistance', {}).items():
                if elem in resistance_entries:
                    resistance_entries[elem].insert(0, val)
        
        # 重新打包添加属性按钮
        self.add_attribute_button.pack_forget()
        self.add_attribute_button.pack(pady=5)
        self.update_scroll_region()

    def remove_attribute_field(self, frame_to_remove):
        """移除属性输入字段"""
        for widget_set in self.attribute_widgets:
            if widget_set["frame"] == frame_to_remove:
                self.attribute_widgets.remove(widget_set)
                break
        frame_to_remove.destroy()
        self.update_scroll_region()

    def render_attributes(self):
        """渲染所有属性字段"""
        for widget_set in self.attribute_widgets:
            widget_set["frame"].destroy()
        self.attribute_widgets = []
        for attribute_data in self.attributes_data:
            self.add_attribute_field(attribute_data)

    def update_scroll_region(self):
        """更新Canvas的滚动区域"""
        self.canvas.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))

    def save_character(self):
        """保存角色数据"""
        try:
            name = self.name_entry.get()
            hp = int(self.hp_entry.get())
            image = self.image_entry.get()
            audio = self.audio_entry.get()
            element = self.element_entry.get()

            atk = {}
            for elem, entry in self.atk_entries.items():
                val = entry.get()
                atk[elem] = int(val) if val else 0

            skills = []
            for skill_widget in self.skill_widgets:
                skill_name = skill_widget["name_entry"].get()
                skill_effect = skill_widget["effect_entry"].get()
                skill_damage = {}
                for elem, entry in skill_widget["damage_entries"].items():
                    val = entry.get()
                    skill_damage[elem] = int(val) if val else 0
                skills.append({"name": skill_name, "effect": skill_effect, "damage": skill_damage})

            attributes = []
            for attr_widget in self.attribute_widgets:
                attr_name = attr_widget["name_entry"].get()
                attr_resistance = {}
                for elem, entry in attr_widget["resistance_entries"].items():
                    val = entry.get()
                    attr_resistance[elem] = int(val) if val else 0
                attributes.append({"name": attr_name, "resistance": attr_resistance})

            if self.character:
                # 编辑现有角色
                self.character.update({
                    "name": name,
                    "stats": {"hp": hp, "atk": atk},
                    "skills": skills,
                    "image": image,
                    "audio": audio,
                    "attributes": attributes,
                    "element": element
                })
                message = f"角色 '{name}' (ID: {self.character['id']}) 已更新。"
            else:
                # 添加新角色
                new_id = max([c['id'] for c in self.data['characters']]) + 1 if self.data['characters'] else 1
                new_character = {
                    "id": new_id,
                    "name": name,
                    "stats": {"hp": hp, "atk": atk},
                    "skills": skills,
                    "image": image,
                    "audio": audio,
                    "attributes": attributes,
                    "element": element
                }
                self.data['characters'].append(new_character)
                message = f"角色 '{name}' (ID: {new_id}) 已添加。"

            if save_characters(self.data):
                messagebox.showinfo("成功", message)
                self.refresh_callback()
                self.destroy() # 关闭窗口
            
        except ValueError:
            messagebox.showerror("输入错误", "HP、攻击和伤害属性必须是有效的数字。")
        except Exception as e:
            messagebox.showerror("错误", f"保存角色时发生错误: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = CharacterManagerGUI(root)
    root.mainloop()