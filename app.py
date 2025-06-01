from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory
import os
from werkzeug.utils import secure_filename
import json
import battle # 导入 battle 模块

app = Flask(__name__)
DATA_FILE = 'data/characters.json'
UPLOAD_FOLDER = 'static/assets'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp3', 'wav'}

ELEMENTS = ['金', '木', '水', '火', '土', '风', '雷', '毒', '法', '圣', '精神']

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 确保数据目录存在
os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)

def load_characters():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, 'r', encoding='utf-8') as f:
        characters = json.load(f).get('characters', [])
        # 确保atk字段是字典格式
        for char in characters:
            if isinstance(char['stats']['atk'], int):
                original_atk_value = char['stats']['atk']
                char['stats']['atk'] = {element: 0 for element in ELEMENTS}
                char['stats']['atk']['金'] = original_atk_value
            elif not isinstance(char['stats']['atk'], dict):
                char['stats']['atk'] = {element: 0 for element in ELEMENTS}
            # 确保所有元素键都存在于atk字典中
            for element in ELEMENTS:
                if element not in char['stats']['atk']:
                    char['stats']['atk'][element] = 0
            # 确保skills中的damage字段是字典
            for i, skill_item in enumerate(char.get('skills', [])):
                if isinstance(skill_item, str):
                    # 如果技能是字符串，转换为字典格式
                    char['skills'][i] = {
                        'name': skill_item,
                        'effect': '', # Add default effect
                        'damage': {element: 0 for element in ELEMENTS}
                    }
                    skill_item = char['skills'][i] # 更新skill_item为新创建的字典
                # 确保skills中的effect字段存在
                if 'effect' not in skill_item:
                    skill_item['effect'] = ''
                # 确保skills中的damage字段是字典
                if 'damage' not in skill_item or not isinstance(skill_item['damage'], dict):
                    skill_item['damage'] = {element: 0 for element in ELEMENTS}
                else:
                    # 确保所有元素键都存在于damage字典中
                    for element in ELEMENTS:
                        if element not in skill_item['damage']:
                            skill_item['damage'][element] = 0
            
            # Heuristic fix for '精神' damage transfer issue
            # If character's '精神' atk is > 0 and a skill's '精神' damage is 0,
            # assume the '精神' atk was mistakenly transferred from a skill.
            # This is a specific fix based on observed data pattern.
            if char['stats']['atk'].get('精神', 0) > 0:
                for skill_item in char.get('skills', []):
                    if skill_item['damage'].get('精神', 0) == 0:
                        # Transfer the '精神' atk to the skill's '精神' damage
                        skill_item['damage']['精神'] = char['stats']['atk']['精神']
                        char['stats']['atk']['精神'] = 0 # Reset character's '精神' atk
                        break # Only fix the first skill found with 0 '精神' damage
            
            # 确保attributes中的resistance字段是字典
            for i, attr_item in enumerate(char.get('attributes', [])):
                if isinstance(attr_item, str):
                    # 如果属性是字符串，转换为字典格式
                    char['attributes'][i] = {
                        'name': attr_item,
                        'resistance': {element: 0 for element in ELEMENTS}
                    }
                    attr_item = char['attributes'][i] # 更新attr_item为新创建的字典
                # 确保attributes中的resistance字段是字典
                if 'resistance' not in attr_item or not isinstance(attr_item['resistance'], dict):
                    attr_item['resistance'] = {element: 0 for element in ELEMENTS}
                else:
                    # 确保所有元素键都存在于resistance字典中
                    for element in ELEMENTS:
                        if element not in attr_item['resistance']:
                            attr_item['resistance'][element] = 0

        return characters

def save_characters(characters):
    with open(DATA_FILE, 'w') as f:
        json.dump({'characters': characters}, f, indent=2)

@app.route('/')
def index():
    characters = load_characters()
    win_rates = battle.load_win_rates() # Load win rates
    return render_template('index.html', characters=characters, win_rates=win_rates) # Pass win_rates to template

@app.route('/edit/<int:char_id>', methods=['GET', 'POST'])
def edit_character(char_id):
    characters = load_characters()
    character = next((c for c in characters if c['id'] == char_id), None)

    if character is None:
        # 如果角色不存在，重定向到主页或显示错误
        return redirect(url_for('index'))
    
    if request.method == 'POST':
        # 更新角色数据逻辑
        character.update({
            'name': request.form['name'],
            'stats': {
                'hp': int(request.form['hp']) if request.form['hp'] else 0,
                'atk': {
                    **{element: int(request.form.get(f'atk_{element}') or 0) for element in ELEMENTS}
                }
            },
            'element': request.form.get('element', '') # Use .get with default for element
        })

        # Process skills
        new_skills = []
        skill_indices = sorted(list(set([int(key.split('_')[2]) for key in request.form.keys() if key.startswith('skill_name_')])))
        
        for i in skill_indices:
            name = request.form.get(f'skill_name_{i}', '').strip()
            effect = request.form.get(f'skill_effect_{i}', '').strip()
            
            skill_damage = {}
            for element in ELEMENTS:
                damage_value = request.form.get(f'skill_damage_{i}_{element}')
                skill_damage[element] = int(damage_value or 0)

            if name or effect or any(skill_damage.values()):
                new_skills.append({
                    "name": name,
                    "effect": effect,
                    "damage": skill_damage
                })
        character['skills'] = new_skills

        # Process attributes
        new_attributes = []
        attribute_indices = sorted(list(set([int(key.split('_')[2]) for key in request.form.keys() if key.startswith('attribute_name_')])))

        for i in attribute_indices:
            name = request.form.get(f'attribute_name_{i}', '').strip()
            
            attr_resistance = {}
            for element in ELEMENTS:
                resistance_value = request.form.get(f'attr_resistance_{i}_{element}')
                attr_resistance[element] = int(resistance_value or 0)

            if name or any(attr_resistance.values()):
                new_attributes.append({
                    "name": name,
                    "resistance": attr_resistance
                })
        character['attributes'] = new_attributes
        
        # 处理图片上传
        if 'image' in request.files:
            image = request.files['image']
            if image.filename != '' and allowed_file(image.filename):
                filename = secure_filename(f"{char_id}_image.{image.filename.rsplit('.', 1)[1].lower()}")
                image.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                character['image'] = filename
        
        # 处理音频上传
        if 'audio' in request.files:
            audio = request.files['audio']
            if audio.filename != '' and allowed_file(audio.filename):
                filename = secure_filename(f"{char_id}_audio.{audio.filename.rsplit('.', 1)[1].lower()}")
                audio.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                character['audio'] = filename
        
        save_characters(characters)
        return redirect(url_for('index'))
    
    return render_template('edit.html', character=character)

@app.route('/assets/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/create', methods=['POST'])
def create_character():
    characters = load_characters()
    new_id = max(c['id'] for c in characters) + 1 if characters else 1
    characters.append({
        'id': new_id,
        'name': '新角色',
        'stats': {
            'hp': 100,
            'atk': {element: 0 for element in ELEMENTS}
        },
        'skills': [],  # 格式: [{"name": "火球术", "effect": "造成100点伤害", "damage": {"火": 100, ...}}, ...]
        'image': '',
        'audio': '',
        'attributes': [], # 格式: [{"name": "火焰抗性", "resistance": {"火": 50, ...}}, ...]
        'element': '' # Default element
    })
    save_characters(characters)
    return redirect(url_for('edit_character', char_id=new_id))

@app.route('/delete/<int:char_id>', methods=['POST'])
def delete_character(char_id):
    characters = load_characters()
    character = next((c for c in characters if c['id'] == char_id), None)
    
    # 删除关联的文件
    if character:
        if character.get('image'):
            image_path = os.path.join(app.config['UPLOAD_FOLDER'], character['image'])
            if os.path.exists(image_path):
                os.remove(image_path)
        if character.get('audio'):
            audio_path = os.path.join(app.config['UPLOAD_FOLDER'], character['audio'])
            if os.path.exists(audio_path):
                os.remove(audio_path)
    
    characters = [c for c in characters if c['id'] != char_id]
    save_characters(characters)
    return redirect(url_for('index'))

@app.route('/api/characters', methods=['GET'])
def get_all_characters():
    """Returns all characters as JSON."""
    characters = load_characters()
    return jsonify({"characters": characters})

@app.route('/battle', methods=['GET'])
def battle_characters():
    """Handles character battle requests and returns detailed steps."""
    characters = load_characters() # Use app's load_characters to ensure consistent data
    
    battle_mode = request.args.get('mode', '2v2') # Get battle mode, default to 2v2

    if battle_mode == '1v1':
        char1_id = request.args.get('char1_id', type=int)
        char2_id = request.args.get('char2_id', type=int)

        if not char1_id or not char2_id:
            return jsonify({"error": "Missing character IDs for 1v1 battle."}), 400

        team1, team2 = battle.select_characters(characters, [char1_id], [char2_id], battle_mode='1v1')

        if not team1 or not team2:
            return jsonify({"error": "Could not select characters for 1v1 battle."}), 400
        
        battle_steps, final_result = battle.simulate_battle(team1, team2, battle_mode='1v1')

    elif battle_mode == '2v2':
        team1_char1_id = request.args.get('team1_char1_id', type=int)
        team1_char2_id = request.args.get('team1_char2_id', type=int)
        team2_char1_id = request.args.get('team2_char1_id', type=int)
        team2_char2_id = request.args.get('team2_char2_id', type=int)

        if not all([team1_char1_id, team1_char2_id, team2_char1_id, team2_char2_id]):
            return jsonify({"error": "Missing character IDs for 2v2 battle."}), 400

        team1_ids = [team1_char1_id, team1_char2_id]
        team2_ids = [team2_char1_id, team2_char2_id]
        
        team1, team2 = battle.select_characters(characters, team1_ids, team2_ids, battle_mode='2v2')

        if not team1 or not team2:
            return jsonify({"error": "Could not select characters for 2v2 battle."}), 400

        battle_steps, final_result = battle.simulate_battle(team1, team2, battle_mode='2v2')
    elif battle_mode == 'free_for_all':
        # 大乱斗模式：所有角色参战
        battle_steps, final_result = battle.simulate_battle_free_for_all(characters) # 新增函数
    else:
        return jsonify({"error": "Invalid battle mode specified."}), 400

    return jsonify({
        "steps": battle_steps,
        "result": final_result
    })

@app.route('/battle_result', methods=['GET'])
def battle_result_page():
    """Renders the battle result page with battle steps and final result."""
    final_result = request.args.get('result', '未知结果')
    battle_steps_json = request.args.get('steps', '[]')
    try:
        battle_steps = json.loads(battle_steps_json)
    except json.JSONDecodeError:
        battle_steps = [] # Fallback to empty list if JSON is invalid
    return render_template('battle_result.html', final_result=final_result, battle_steps=battle_steps)

@app.route('/douququ')
def douququ_mode():
    """Renders the douququ mode page."""
    return render_template('douququ.html')

if __name__ == '__main__':
    app.run(debug=True)