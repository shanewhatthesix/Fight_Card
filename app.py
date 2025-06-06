from flask import Flask, render_template, request, redirect, url_for, jsonify, send_from_directory, session
import os
from werkzeug.utils import secure_filename
import json
import random # 导入 random 模块
import battle # 导入 battle 模块
import uuid # 用于生成唯一的战斗ID

app = Flask(__name__)
app.secret_key = os.urandom(24) # 设置一个随机的密钥，用于session
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
        for char in characters:
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
                'hp': int(request.form['hp']) if request.form['hp'] else 0
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
            # 处理技能音效文件上传
            if f'skill_audio_{i}' in request.files:
                skill_audio_file = request.files[f'skill_audio_{i}']
                if skill_audio_file.filename != '' and allowed_file(skill_audio_file.filename):
                    # 新的文件名格式：skill_索引.mp3
                    audio_filename = secure_filename(f"skill_{i}.mp3")
                    skill_audio_file.save(os.path.join(UPLOAD_FOLDER, audio_filename))
                    new_skills[-1]['audio'] = audio_filename # 将文件名保存到当前技能的audio字段
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
        
        # 处理音频上传 (角色整体音频，非技能音频)
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
            'hp': 100
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

@app.route('/pokemon_battle')
def pokemon_battle_page():
    """Renders the Pokemon-style battle page."""
    return render_template('pokemon_battle.html')

@app.route('/api/pokemon_battle/init', methods=['POST'])
def init_pokemon_battle():
    data = request.get_json()
    player1_id = data.get('player1_id')
    player2_id = data.get('player2_id')

    if not player1_id or not player2_id:
        return jsonify({"success": False, "message": "缺少玩家角色ID。"}), 400

    characters = load_characters()
    
    # 查找玩家选择的角色
    player1_char = next((c for c in characters if c['id'] == int(player1_id)), None)
    player2_char = next((c for c in characters if c['id'] == int(player2_id)), None)

    if not player1_char or not player2_char:
        return jsonify({"success": False, "message": "未找到指定角色。"}), 404

    # 初始化战斗状态
    battle_id = str(uuid.uuid4())
    
    # 深拷贝角色数据，避免修改原始数据
    p1_char_copy = json.loads(json.dumps(player1_char))
    p2_char_copy = json.loads(json.dumps(player2_char))

    # 初始化当前HP和战斗统计
    p1_char_copy['current_hp'] = p1_char_copy['stats']['hp']
    p1_char_copy['damage_dealt'] = 0
    p1_char_copy['damage_taken'] = 0
    p1_char_copy['healing_done'] = 0

    p2_char_copy['current_hp'] = p2_char_copy['stats']['hp']
    p2_char_copy['damage_dealt'] = 0
    p2_char_copy['damage_taken'] = 0
    p2_char_copy['healing_done'] = 0

    # 随机决定哪个角色先行动
    first_attacker_id = random.choice([p1_char_copy['id'], p2_char_copy['id']])

    initial_log = [
        {"event": "start", "message": f"宝可梦式对战开始: 「{p1_char_copy['name']}」 vs 「{p2_char_copy['name']}」"}
    ]

    battle_state = {
        'battle_id': battle_id,
        'team1_ids': [p1_char_copy['id']],
        'team2_ids': [p2_char_copy['id']],
        'characters': [p1_char_copy, p2_char_copy],
        'current_turn': 1,
        'active_character_id': first_attacker_id,
        'battle_log': initial_log,
        'battle_ended': False,
        'final_result_message': ''
    }
    session[battle_id] = battle_state # 将战斗状态存储在session中

    return jsonify({"success": True, "state": battle_state})

@app.route('/api/pokemon_battle/action', methods=['POST'])
def pokemon_battle_action():
    data = request.get_json()
    battle_id = data.get('battle_id')
    character_id = data.get('character_id')
    skill_name = data.get('skill_name')

    if not battle_id or not character_id or not skill_name:
        return jsonify({"success": False, "message": "缺少战斗ID、角色ID或技能名称。"}), 400

    battle_state = session.get(battle_id)
    if not battle_state:
        return jsonify({"success": False, "message": "未找到战斗状态，请重新开始战斗。"}), 404
    
    if battle_state['battle_ended']:
        return jsonify({"success": False, "message": "战斗已结束，无法执行行动。"}), 400

    # 确保是当前行动角色
    if battle_state['active_character_id'] != character_id:
        return jsonify({"success": False, "message": "现在不是该角色行动。"}), 400

    attacker = next((c for c in battle_state['characters'] if c['id'] == character_id), None)
    if not attacker or attacker['current_hp'] <= 0:
        return jsonify({"success": False, "message": "行动角色无效或已阵亡。"}), 400

    skill = next((s for s in attacker['skills'] if s['name'] == skill_name), None)
    if not skill:
        return jsonify({"success": False, "message": "未找到指定技能。"}), 400

    # 确定对手队伍
    opponent_team_ids = battle_state['team2_ids'] if character_id in battle_state['team1_ids'] else battle_state['team1_ids']
    active_opponents = [c for c in battle_state['characters'] if c['id'] in opponent_team_ids and c['current_hp'] > 0]

    if not active_opponents:
        # 对手队伍已全部阵亡，战斗结束
        battle_state['battle_ended'] = True
        battle_state['final_result_message'] = f"恭喜「{attacker['name']}」的队伍获得了胜利！"
        battle_state['battle_log'].append({"event": "end", "message": battle_state['final_result_message']})
        session[battle_id] = battle_state
        return jsonify({"success": True, "state": battle_state})

    # 随机选择一个活跃的对手作为防御者
    defender = random.choice(active_opponents)

    battle_state['battle_log'].append({
        "event": "use_skill",
        "character": attacker['name'],
        "defender": defender['name'],
        "skill": skill['name'],
        "effect": skill['effect'],
        "audio": skill.get('audio', ''), # 添加audio字段
        "message": f"「{attacker['name']}」对「{defender['name']}」使用了「{skill['name']}」！"
    })

    # 计算伤害 (复用 battle.py 中的伤害计算逻辑)
    total_damage = 0
    for damage_type, base_damage in skill['damage'].items():
        defender_resistance = 0
        if 'attributes' in defender and defender['attributes']:
            for attr in defender['attributes']:
                if 'resistance' in attr and damage_type in attr['resistance']:
                    defender_resistance = attr['resistance'][damage_type]
                    break
        actual_damage_for_type = max(0, base_damage - defender_resistance)
        total_damage += actual_damage_for_type
        
    fluctuation_percentage = random.uniform(-0.15, 0.15)
    damage_dealt = total_damage * (1 + fluctuation_percentage)
    damage_dealt = max(0, round(damage_dealt))

    defender_hp_before = defender['current_hp']
    defender['current_hp'] -= damage_dealt
    defender_hp_after = max(0, defender['current_hp'])

    # 更新统计数据
    attacker['damage_dealt'] += damage_dealt
    defender['damage_taken'] += damage_dealt

    battle_state['battle_log'].append({
        "event": "deal_damage",
        "attacker": attacker['name'],
        "defender": defender['name'],
        "skill": skill['name'],
        "damage_dealt": damage_dealt,
        "defender_hp_before": defender_hp_before,
        "defender_hp_after": defender_hp_after,
        "message": f"「{defender['name']}」受到了 {damage_dealt} 点伤害。"
    })
    battle_state['battle_log'].append({"event": "hp_update", "character": defender['name'], "hp": defender_hp_after, "message": f"「{defender['name']}」剩余生命值: {defender_hp_after:.2f}"})

    if defender['current_hp'] <= 0:
        battle_state['battle_log'].append({"event": "defeated", "character": defender['name'], "message": f"「{defender['name']}」已被击败！"})
        
        # 检查对手队伍是否全部阵亡
        if not any(c['current_hp'] > 0 for c in active_opponents):
            battle_state['battle_ended'] = True
            winner_char_name = attacker['name']
            battle_state['final_result_message'] = f"恭喜「{winner_char_name}」的队伍获得了胜利！"
            battle_state['battle_log'].append({"event": "end", "message": battle_state['final_result_message']})
            
            # 更新胜率 (简化处理，只更新获胜方)
            win_rates = battle.load_win_rates()
            winner_char_id = str(attacker['id'])
            win_rates.setdefault(winner_char_id, {"total_battles": 0, "wins": 0})
            win_rates[winner_char_id]["total_battles"] += 1
            win_rates[winner_char_id]["wins"] += 1
            battle.save_win_rates(win_rates)

            # 更新所有参战角色的总战斗次数
            for char in battle_state['characters']:
                if str(char['id']) not in win_rates: # 如果是输家且之前没有记录
                    win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
                if str(char['id']) != winner_char_id: # 输家只增加总战斗次数
                    win_rates[str(char['id'])]["total_battles"] += 1
            battle.save_win_rates(win_rates)

            session[battle_id] = battle_state
            return jsonify({"success": True, "state": battle_state})

    # 切换到下一个行动角色
    all_active_characters = [c for c in battle_state['characters'] if c['current_hp'] > 0]
    if len(all_active_characters) > 0:
        # 找到当前行动角色的索引
        current_attacker_index = -1
        for i, char in enumerate(all_active_characters):
            if char['id'] == battle_state['active_character_id']:
                current_attacker_index = i
                break
        
        # 切换到下一个角色，如果到达列表末尾则回到开头
        next_attacker_index = (current_attacker_index + 1) % len(all_active_characters)
        battle_state['active_character_id'] = all_active_characters[next_attacker_index]['id']

        # 如果回到了第一个行动角色，则回合数增加
        if next_attacker_index == 0: # 简单判断，如果所有活跃角色都行动过一轮，则进入下一回合
            battle_state['current_turn'] += 1
            battle_state['battle_log'].append({"event": "turn_start", "turn": battle_state['current_turn'], "message": f"--- 第 {battle_state['current_turn']} 回合 ---"})
            
            # 检查最大回合数
            MAX_TURNS = 200 # 与 battle.py 保持一致
            if battle_state['current_turn'] > MAX_TURNS:
                battle_state['battle_ended'] = True
                battle_state['final_result_message'] = "战斗结束: 平局！(达到最大回合数)"
                battle_state['battle_log'].append({"event": "end", "message": battle_state['final_result_message']})
                
                # 更新所有参战角色的总战斗次数 (平局)
                win_rates = battle.load_win_rates()
                for char in battle_state['characters']:
                    win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
                    win_rates[str(char['id'])]["total_battles"] += 1
                battle.save_win_rates(win_rates)

                session[battle_id] = battle_state
                return jsonify({"success": True, "state": battle_state})
    else:
        # 所有角色都阵亡，平局
        battle_state['battle_ended'] = True
        battle_state['final_result_message'] = "战斗结束: 所有角色都被击败，平局！"
        battle_state['battle_log'].append({"event": "end", "message": battle_state['final_result_message']})
        
        # 更新所有参战角色的总战斗次数 (平局)
        win_rates = battle.load_win_rates()
        for char in battle_state['characters']:
            win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
            win_rates[str(char['id'])]["total_battles"] += 1
        battle.save_win_rates(win_rates)

    session[battle_id] = battle_state # 保存更新后的状态
    return jsonify({"success": True, "state": battle_state})

if __name__ == '__main__':
    app.run(debug=True)