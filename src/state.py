state = "lobby"
lives = 3
score = 0
player_hp = 100
player_max_hp = 100
player_xp = 0
player_level = 1
has_double_dash = False
has_regen = False
has_cd_reduction = False
has_extended_reach = False
has_executioner = False
has_spiked_armor = False
selected_character = "GraveRobber"
equipped_skills = []

def is_equipped(skill_key):
    return skill_key in equipped_skills
