import json
import random
import os

WIN_RATES_FILE = 'data/win_rates.json'

def load_characters(filepath="data/characters.json"):
    """Loads character data from a JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get("characters", [])
    except FileNotFoundError:
        print(f"Error: Character file not found at {filepath}")
        return []
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {filepath}")
        return []

def load_win_rates():
    """Loads win rates data from a JSON file."""
    if not os.path.exists(WIN_RATES_FILE):
        return {}
    try:
        with open(WIN_RATES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        print(f"Error: Could not decode JSON from {WIN_RATES_FILE}")
        return {}

def save_win_rates(win_rates):
    """Saves win rates data to a JSON file."""
    with open(WIN_RATES_FILE, 'w', encoding='utf-8') as f:
        json.dump(win_rates, f, indent=2)

def select_characters(characters, team1_ids=None, team2_ids=None, battle_mode='2v2'):
    """Selects characters for battle, either by ID or randomly, based on battle_mode."""
    if not characters:
        return [], []

    num_chars_per_team = 1 if battle_mode == '1v1' else 2
    required_total_chars = num_chars_per_team * 2

    if team1_ids is not None and team2_ids is not None:
        team1 = [next((c for c in characters if c["id"] == char_id), None) for char_id in team1_ids]
        team2 = [next((c for c in characters if c["id"] == char_id), None) for char_id in team2_ids]
        
        if len(team1) != num_chars_per_team or len(team2) != num_chars_per_team or \
           any(c is None for c in team1) or any(c is None for c in team2):
            print(f"Error: Specified character ID(s) not found or incorrect number of characters for {battle_mode} battle.")
            return [], []
    else:
        if len(characters) < required_total_chars:
            print(f"Error: Not enough characters for a random {battle_mode} battle.")
            return [], []
        selected_chars = random.sample(characters, required_total_chars)
        team1 = selected_chars[:num_chars_per_team]
        team2 = selected_chars[num_chars_per_team:]

    return team1, team2

def simulate_battle(team1, team2, battle_mode='2v2'):
    """Simulates a turn-based battle between two teams and returns detailed steps."""
    num_chars_per_team = 1 if battle_mode == '1v1' else 2
    if not team1 or not team2 or len(team1) != num_chars_per_team or len(team2) != num_chars_per_team:
        return [], "Battle could not start due to invalid teams or incorrect number of characters for the selected mode."

    battle_steps = []
    
    # Initialize current HP and battle stats for all characters
    for char in team1 + team2:
        char['current_hp'] = char['stats']['hp']
        char['damage_dealt'] = 0
        char['damage_taken'] = 0
        char['healing_done'] = 0 # Placeholder for future healing mechanics

    team1_names = ", ".join([c['name'] for c in team1])
    team2_names = ", ".join([c['name'] for c in team2])
    
    if battle_mode == '1v1':
        battle_steps.append({"event": "start", "message": f"1V1 战斗开始: 「{team1_names}」 vs 「{team2_names}」"})
    else:
        battle_steps.append({"event": "start", "message": f"2V2 战斗开始: 队伍1 ({team1_names}) vs 队伍2 ({team2_names})"})
 
    MAX_TURNS = 200 # 设置最大回合数以防止无限战斗或内存错误
    turn = 1
    while any(c['current_hp'] > 0 for c in team1) and any(c['current_hp'] > 0 for c in team2) and turn <= MAX_TURNS:
        battle_steps.append({"event": "turn_start", "turn": turn, "message": f"--- 第 {turn} 回合 ---"})

        # 组合所有活跃的战斗者并随机化行动顺序
        active_fighters = [c for c in team1 + team2 if c['current_hp'] > 0]
        random.shuffle(active_fighters)

        for attacker in active_fighters:
            if attacker['current_hp'] <= 0:
                battle_steps.append({"event": "skip_turn", "character": attacker['name'], "message": f"「{attacker['name']}」已被击败，跳过回合。"})
                continue # 如果角色已被击败，则跳过回合

            battle_steps.append({"event": "character_turn", "character": attacker['name'], "message": f"「{attacker['name']}」的回合。"})

            # Determine opponent team
            opponent_team = team2 if attacker in team1 else team1
            
            # Select active opponents
            active_opponents = [c for c in opponent_team if c['current_hp'] > 0]

            if not active_opponents:
                # Opponent team is defeated, battle ends
                break

            # Randomly select a skill
            if not attacker['skills']:
                battle_steps.append({"event": "no_skill", "character": attacker['name'], "message": f"「{attacker['name']}」没有技能，跳过回合。"})
                continue
            skill = random.choice(attacker['skills'])
            
            # 随机选择一个活跃的对手作为防御者
            defender = random.choice(active_opponents)

            battle_steps.append({
                "event": "use_skill",
                "character": attacker['name'],
                "defender": defender['name'],
                "skill": skill['name'],
                "effect": skill['effect'],
                "message": f"「{attacker['name']}」对「{defender['name']}」使用了「{skill['name']}」！"
            })

            # 初始化总伤害
            total_damage = 0
            
            # 遍历技能的每种伤害类型
            for damage_type, base_damage in skill['damage'].items():
                # 获取防御者对应类型的抗性
                # 假设每个角色只有一个属性，且属性中包含resistance
                defender_resistance = 0
                if 'attributes' in defender and defender['attributes']:
                    for attr in defender['attributes']:
                        if 'resistance' in attr and damage_type in attr['resistance']:
                            defender_resistance = attr['resistance'][damage_type]
                            break # 找到抗性后跳出循环
                
                # 计算实际伤害：基础伤害减去抗性，确保不低于0
                # 这里可以根据需求调整抗性计算方式，例如百分比减免
                actual_damage_for_type = max(0, base_damage - defender_resistance)
                total_damage += actual_damage_for_type
                
            # 应用伤害波动
            fluctuation_percentage = random.uniform(-0.15, 0.15)
            damage_dealt = total_damage * (1 + fluctuation_percentage)
            damage_dealt = max(0, round(damage_dealt))

            defender_hp_before = defender['current_hp']
            defender['current_hp'] -= damage_dealt
            defender_hp_after = max(0, defender['current_hp'])

            # 更新统计数据
            attacker['damage_dealt'] += damage_dealt
            defender['damage_taken'] += damage_dealt

            battle_steps.append({
                "event": "deal_damage",
                "attacker": attacker['name'],
                "defender": defender['name'],
                "skill": skill['name'],
                "damage_dealt": damage_dealt,
                "defender_hp_before": defender_hp_before,
                "defender_hp_after": defender_hp_after,
                "message": f"「{defender['name']}」受到了 {damage_dealt} 点伤害。"
            })
            battle_steps.append({"event": "hp_update", "character": defender['name'], "hp": defender_hp_after, "message": f"「{defender['name']}」剩余生命值: {defender_hp_after:.2f}"})

            if defender['current_hp'] <= 0:
                battle_steps.append({"event": "defeated", "character": defender['name'], "message": f"「{defender['name']}」已被击败！"})
                # 检查整个队伍是否被击败
                if not any(c['current_hp'] > 0 for c in opponent_team):
                    # 一队被完全击败，立即结束战斗
                    winner_team_chars = team1 if opponent_team is team2 else team2
                    
                    # 计算MVP
                    mvp_char = None
                    max_damage = -1
                    for char in winner_team_chars:
                        if char['damage_dealt'] > max_damage:
                            max_damage = char['damage_dealt']
                            mvp_char = char
                    
                    final_result_message = ""
                    if mvp_char:
                        if battle_mode == '1v1':
                            final_result_message = f"恭喜「{mvp_char['name']}」获得了胜利！"
                        else:
                            other_winner_char = next((c for c in winner_team_chars if c is not mvp_char), None)
                            if other_winner_char:
                                final_result_message = f"恭喜「{mvp_char['name']}」获得了MVP，「{other_winner_char['name']}」是躺赢狗！"
                            else:
                                final_result_message = f"恭喜队伍 {'1' if opponent_team is team2 else '2'} 获得了胜利！"
                    else:
                        final_result_message = f"恭喜队伍 {'1' if opponent_team is team2 else '2'} 获得了胜利！"

                    # 收集所有角色的最终统计数据
                    character_stats = []
                    for char in team1 + team2:
                        character_stats.append({
                            "name": char['name'],
                            "team": "队伍1" if char in team1 else "队伍2",
                            "damage_dealt": char['damage_dealt'],
                            "damage_taken": char['damage_taken'],
                            "healing_done": char['healing_done']
                        })
                    
                    battle_steps.append({"event": "end", "result": final_result_message, "character_stats": character_stats, "message": final_result_message})
                    
                    # Update win rates
                    win_rates = load_win_rates()
                    winning_team_ids = [c['id'] for c in winner_team_chars]
                    losing_team_ids = [c['id'] for c in (team2 if opponent_team is team2 else team1)]

                    for char_id in winning_team_ids:
                        win_rates.setdefault(str(char_id), {"total_battles": 0, "wins": 0})
                        win_rates[str(char_id)]["total_battles"] += 1
                        win_rates[str(char_id)]["wins"] += 1
                    for char_id in losing_team_ids:
                        win_rates.setdefault(str(char_id), {"total_battles": 0, "wins": 0})
                        win_rates[str(char_id)]["total_battles"] += 1
                    save_win_rates(win_rates)

                    return battle_steps, final_result_message

        turn += 1
        # 检查所有活跃的战斗者行动结束后战斗是否应该结束
        if not any(c['current_hp'] > 0 for c in team1) or not any(c['current_hp'] > 0 for c in team2):
            break

    # 达到最大回合数或双方都阵亡
    final_result_message = ""
    team1_alive = any(c['current_hp'] > 0 for c in team1)
    team2_alive = any(c['current_hp'] > 0 for c in team2)

    if team1_alive and team2_alive:
        final_result_message = "战斗结束: 平局！(达到最大回合数)"
    elif team1_alive:
        # 计算MVP
        mvp_char = None
        max_damage = -1
        for char in team1:
            if char['damage_dealt'] > max_damage:
                max_damage = char['damage_dealt']
                mvp_char = char
        
        if mvp_char:
            if battle_mode == '1v1':
                final_result_message = f"恭喜「{mvp_char['name']}」获得了胜利！"
            else:
                other_winner_char = next((c for c in team1 if c is not mvp_char), None)
                if other_winner_char:
                    final_result_message = f"恭喜「{mvp_char['name']}」获得了MVP，「{other_winner_char['name']}」是躺赢狗！"
                else:
                    final_result_message = "恭喜队伍1获得了胜利！"
        else:
            final_result_message = "恭喜队伍1获得了胜利！"

    elif team2_alive:
        # 计算MVP
        mvp_char = None
        max_damage = -1
        for char in team2:
            if char['damage_dealt'] > max_damage:
                max_damage = char['damage_dealt']
                mvp_char = char
        
        if mvp_char:
            if battle_mode == '1v1':
                final_result_message = f"恭喜「{mvp_char['name']}」获得了胜利！"
            else:
                other_winner_char = next((c for c in team2 if c is not mvp_char), None)
                if other_winner_char:
                    final_result_message = f"恭喜「{mvp_char['name']}」获得了MVP，「{other_winner_char['name']}」是躺赢狗！"
                else:
                    final_result_message = "恭喜队伍2获得了胜利！"
        else:
            final_result_message = "恭喜队伍2获得了胜利！"
    else:
        final_result_message = "战斗结束: 平局！(双方队伍都被击败)"

    # 收集所有角色的最终统计数据
    character_stats = []
    for char in team1 + team2:
        character_stats.append({
            "name": char['name'],
            "team": "队伍1" if char in team1 else "队伍2",
            "damage_dealt": char['damage_dealt'],
            "damage_taken": char['damage_taken'],
            "healing_done": char['healing_done']
        })
    
    battle_steps.append({"event": "end", "result": final_result_message, "character_stats": character_stats, "message": final_result_message})
    
    # Update win rates for draw/max turns
    win_rates = load_win_rates()
    for char in team1 + team2:
        win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
        win_rates[str(char['id'])]["total_battles"] += 1
    save_win_rates(win_rates)

    return battle_steps, final_result_message

def simulate_battle_free_for_all(all_characters):
    """Simulates a free-for-all battle among all characters."""
    battle_steps = []
    
    if len(all_characters) < 2:
        return [], "大乱斗模式至少需要两个角色。"

    # Initialize current HP and battle stats for all characters
    for char in all_characters:
        char['current_hp'] = char['stats']['hp']
        char['damage_dealt'] = 0
        char['damage_taken'] = 0
        char['healing_done'] = 0

    character_names = ", ".join([c['name'] for c in all_characters])
    battle_steps.append({"event": "start", "message": f"大乱斗开始！参战角色: {character_names}", "characters": all_characters})

    MAX_TURNS = 200
    turn = 1
    while len([c for c in all_characters if c['current_hp'] > 0]) > 1 and turn <= MAX_TURNS:
        battle_steps.append({"event": "turn_start", "turn": turn, "message": f"--- 第 {turn} 回合 ---"})

        active_fighters = [c for c in all_characters if c['current_hp'] > 0]
        random.shuffle(active_fighters)

        for attacker in active_fighters:
            if attacker['current_hp'] <= 0:
                battle_steps.append({"event": "skip_turn", "character": attacker['name'], "message": f"「{attacker['name']}」已被击败，跳过回合。"})
                continue

            battle_steps.append({"event": "character_turn", "character": attacker['name'], "message": f"「{attacker['name']}」的回合。"})

            # Select active opponents (anyone not the attacker and still alive)
            active_opponents = [c for c in active_fighters if c is not attacker and c['current_hp'] > 0]

            if not active_opponents:
                # Only one character left, battle ends
                break

            if not attacker['skills']:
                battle_steps.append({"event": "no_skill", "character": attacker['name'], "message": f"「{attacker['name']}」没有技能，跳过回合。"})
                continue
            skill = random.choice(attacker['skills'])
            
            defender = random.choice(active_opponents)

            battle_steps.append({
                "event": "use_skill",
                "character": attacker['name'],
                "defender": defender['name'],
                "skill": skill['name'],
                "effect": skill['effect'],
                "message": f"「{attacker['name']}」对「{defender['name']}」使用了「{skill['name']}」！"
            })

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

            attacker['damage_dealt'] += damage_dealt
            defender['damage_taken'] += damage_dealt

            battle_steps.append({
                "event": "deal_damage",
                "attacker": attacker['name'],
                "defender": defender['name'],
                "skill": skill['name'],
                "damage_dealt": damage_dealt,
                "defender_hp_before": defender_hp_before,
                "defender_hp_after": defender_hp_after,
                "message": f"「{defender['name']}」受到了 {damage_dealt} 点伤害。"
            })
            battle_steps.append({"event": "hp_update", "character": defender['name'], "hp": defender_hp_after, "message": f"「{defender['name']}」剩余生命值: {defender_hp_after:.2f}"})

            if defender['current_hp'] <= 0:
                battle_steps.append({"event": "defeated", "character": defender['name'], "message": f"「{defender['name']}」已被击败！"})
                # Check if only one character remains after this defeat
                if len([c for c in all_characters if c['current_hp'] > 0]) <= 1:
                    break # End battle if only one or zero characters remain

        turn += 1
        # Check if battle should end after all active fighters have taken their turn
        if len([c for c in all_characters if c['current_hp'] > 0]) <= 1:
            break

    final_result_message = ""
    remaining_characters = [c for c in all_characters if c['current_hp'] > 0]

    if len(remaining_characters) == 1:
        winner_char = remaining_characters[0]
        final_result_message = f"大乱斗结束！恭喜「{winner_char['name']}」获得了最终胜利！"
        
        # Update win rates for the winner
        win_rates = load_win_rates()
        win_rates.setdefault(str(winner_char['id']), {"total_battles": 0, "wins": 0})
        win_rates[str(winner_char['id'])]["total_battles"] += 1
        win_rates[str(winner_char['id'])]["wins"] += 1
        save_win_rates(win_rates)

        # Update win rates for losers (all other characters)
        for char in all_characters:
            if char['id'] != winner_char['id']:
                win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
                win_rates[str(char['id'])]["total_battles"] += 1
        save_win_rates(win_rates)

    elif not remaining_characters:
        final_result_message = "大乱斗结束: 所有角色都被击败，平局！"
        # Update win rates for all characters (as a draw)
        win_rates = load_win_rates()
        for char in all_characters:
            win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
            win_rates[str(char['id'])]["total_battles"] += 1
        save_win_rates(win_rates)
    else:
        final_result_message = "大乱斗结束: 平局！(达到最大回合数)"
        # Update win rates for all characters (as a draw)
        win_rates = load_win_rates()
        for char in all_characters:
            win_rates.setdefault(str(char['id']), {"total_battles": 0, "wins": 0})
            win_rates[str(char['id'])]["total_battles"] += 1
        save_win_rates(win_rates)

    character_stats = []
    for char in all_characters:
        character_stats.append({
            "name": char['name'],
            "damage_dealt": char['damage_dealt'],
            "damage_taken": char['damage_taken'],
            "healing_done": char['healing_done']
        })

    battle_steps.append({"event": "end", "result": final_result_message, "character_stats": character_stats, "message": final_result_message})

    return battle_steps, final_result_message