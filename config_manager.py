import json
import os
import sys

def _get_base_dir():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


CONFIG_FILE = os.path.join(_get_base_dir(), "config.json")

DEFAULTS = {
    "windowSize": 200,
    "fps": 15,
    "speed": 4,
    "scaleFactor": 4,
    "petPosition": {"x": 100, "y": 100},
    "bubbleDuration": 3,
    "idleInterval": 30,
    "walkFrequency": 5,       # 走动频率：每隔几秒有概率触发走动（秒）
    "walkChance": 0.6,        # 每次触发时走动的概率（0-1）
    "walkDuration": 6,        # 单次走动持续时间（秒）
    "assets": [],
    "bindings": {"idle": "待机.gif", "walk": "右边走路.gif", "walk_left": "左边走路.gif", "walk_right": "右边走路.gif", "drag": "抓起.gif", "pet": "摸摸头.gif", "feed": "", "play": ""},
    "interactionStates": [
        {"key": "pet", "label": "摸摸", "emoji": "🤚"},
        {"key": "feed", "label": "喂食", "emoji": "🍖"},
        {"key": "play", "label": "玩耍", "emoji": "⚽"},
    ],
    "responses": {
        "pet": ["摸摸我干嘛~", "好舒服~", "别闹~", "嘻嘻~"],
        "feed": ["好吃~", "谢谢主人~", "还要~", "吃饱了~"],
        "play": ["好好玩~", "再来一次~", "哈哈~", "累死了~"],
        "drag": ["放开我~", "别拽我~", "头晕了~", "救命啊~"],
    },
    "idleMessages": ["好喜欢你", "想宝宝了", "好喜欢冰冰呀", "饿饿的...", "什么时候吃饭呢..?", "想被宝宝摸摸..", "kisskiss~", "mua~", "宝宝！"],
}


class ConfigManager:
    def __init__(self):
        self.config = {}
        self.load()

    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                self.config = {**DEFAULTS, **loaded}
                self.config["responses"] = {**DEFAULTS["responses"], **(loaded.get("responses") or {})}
                self.config["bindings"] = {**DEFAULTS["bindings"], **(loaded.get("bindings") or {})}
                if loaded.get("interactionStates"):
                    self.config["interactionStates"] = loaded["interactionStates"]
            else:
                self.config = DEFAULTS.copy()
        except Exception:
            self.config = DEFAULTS.copy()

    def save(self):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, key, default=None):
        return self.config.get(key, default)

    def set(self, key, value):
        self.config[key] = value

    def get_bindings(self):
        return self.config.get("bindings", DEFAULTS["bindings"])

    def get_responses(self, state):
        return self.config.get("responses", {}).get(state, [])

    def get_idle_messages(self):
        return self.config.get("idleMessages", DEFAULTS["idleMessages"])

    def get_interaction_states(self):
        return self.config.get("interactionStates", DEFAULTS["interactionStates"])

    def update_binding(self, state, filename):
        self.config.setdefault("bindings", {})[state] = filename

    def update_response(self, state, responses):
        self.config.setdefault("responses", {})[state] = responses

    def set_interaction_states(self, states):
        self.config["interactionStates"] = states
