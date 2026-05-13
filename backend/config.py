import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/settings.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_active_broker():
    config = load_config()
    broker_name = config["active_broker"]
    broker = config["brokers"][broker_name]
    return broker_name, broker

def get_trading_config():
    return load_config()["trading"]

def get_risk_config():
    return load_config()["risk"]

def get_portfolio_config():
    return load_config()["portfolio"]

def get_notification_config():
    return load_config()["notification"]

def get_export_config():
    return load_config()["export"]

def switch_broker(broker_name):
    config = load_config()
    if broker_name not in config["brokers"]:
        print(f"找不到券商：{broker_name}")
        return False
    config["active_broker"] = broker_name
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    print(f"已切換至：{config['brokers'][broker_name]['name']}")
    return True

if __name__ == "__main__":
    broker_name, broker = get_active_broker()
    print(f"目前券商：{broker['name']}")
    print(f"交易市場：{broker['market']}")
    risk = get_risk_config()
    print(f"每日虧損上限：{risk['daily_loss_limit_pct']}%")
    print(f"最大回撤：{risk['max_drawdown_pct']}%")
