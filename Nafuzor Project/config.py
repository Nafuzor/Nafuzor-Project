import os

BOT_TOKEN = "бот токен"
ADMIN_ID = 7063766212

CHANNELS = [-1002428932473, -1003670923992]

# --- ПЛАТЕЖНЫЕ ТОКЕНЫ ---
# CryptoBot (Testnet или Mainnet)
CRYPTO_BOT_TOKEN = "крипто токен" 

# YooMoney
YOOMONEY_TOKEN = "юмани токен" 
YOOMONEY_WALLET = "номер кошелька" # Номер кошелька

# Настройки подписок
SUBSCRIPTIONS = {
    "none": {
        "price": 0, 
        "rank": 0, 
        "name": "Стандарт", 
        "display_rate": "5$/2.4$",
        "rates": {"base": 5, "extra": 2.4},
        "link": ""
    },
    "alpha": {
        "price": 300, 
        "rank": 1, 
        "name": "Alpha", 
        "display_rate": "6$/3$",
        "link": "https://nafuzor.github.io/nafuzor-site/#sys_modal_tier_1_alpha_access_grant",
        "rates": {"base": 6, "extra": 3}
    },
    "nucleus": {
        "price": 600, 
        "rank": 2, 
        "name": "Nucleus", 
        "display_rate": "9$/4.5$",
        "link": "https://nafuzor.github.io/nafuzor-site/#sys_modal_tier_2_nucleus_access_grant",
        "rates": {"base": 9, "extra": 4.5}
    },
    "zero_limits": {
        "price": 1100, 
        "rank": 3, 
        "name": "Zero Limits", 
        "display_rate": "15$/7.5$",
        "link": "https://nafuzor.github.io/nafuzor-site/#sys_modal_tier_3_zero_access_grant",
        "rates": {"base": 15, "extra": 7.5}
    }
}
