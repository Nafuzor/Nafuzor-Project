import random
import string
import qrcode
import io

def generate_card_data():
    # Генерация псевдо-номера карты (Luhn алгоритм не используем для простоты, просто рандом)
    card_num = "4" + "".join([str(random.randint(0, 9)) for _ in range(15)])
    cvv = "".join([str(random.randint(0, 9)) for _ in range(3)])
    return card_num, cvv

def generate_qr(data):
    qr = qrcode.QRCode(version=1, box_size=10, border=5)
    qr.add_data(data)
    qr.make(fit=True)
    img = qr.make_image(fill='black', back_color='white')
    bio = io.BytesIO()
    img.save(bio)
    bio.seek(0)
    return bio

def format_number(num):
    # Простое форматирование для красоты
    return f"{num}"