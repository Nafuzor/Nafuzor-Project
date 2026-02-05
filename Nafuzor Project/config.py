import os

BOT_TOKEN = "8153271966:AAEraO3RpPJbx5BXRVnmrEsvjM2X6euHZ88"
ADMIN_ID = 7063766212

CHANNELS = [-1002428932473, -1003670923992]

# --- ПЛАТЕЖНЫЕ ТОКЕНЫ ---
# CryptoBot (Testnet или Mainnet)
CRYPTO_BOT_TOKEN = "453850:AAIjyzZLq2vyCNgX5Pkqr4iTQrti48bQChX" 

# YooMoney
YOOMONEY_TOKEN = "4100118416658587.EF2DDFB4DA69C592497047D803114707FC7E6B3C3B309AC53F911DAD69574DD8F9BF771C160C8EAB9177A214DAE4FC5898AA91120AC95FD80D9F229B5D46137CECD4366CA60F949BF2882EC15F7C7199887DED23383160D32EA6A46B225F1E1A21B237C8811681CC7F8B932E9C576258F2FEC612F873CEEA43CE52EF0CE7B87D" 
YOOMONEY_WALLET = "4100118416658587" # Номер кошелька

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