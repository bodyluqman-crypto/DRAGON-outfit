from flask import Flask, request, jsonify, send_file
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import os
import logging
import urllib3
import random
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
main_key = "DRAGON-TEAM"
executor = ThreadPoolExecutor(max_workers=10)

# الرابط السري لصور Free Fire
INFO_URL = "https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG"

def fetch_player_info(uid):
    """جلب بيانات اللاعب"""
    url = f'https://otman-info.vercel.app/player-info?uid={uid}'
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching player info: {e}")
    return None

def fetch_image(image_url, size=None):
    """جلب الصورة من الرابط"""
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, timeout=10, verify=False, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            return img
    except Exception as e:
        logger.error(f"Error fetching image: {e}")
    return None

def make_circle_with_border(image, size, border_color):
    """صورة دائرية مع إطار ملون وتأثير توهج"""
    if image is None:
        return None
    
    img = image.resize((size, size), Image.Resampling.LANCZOS)
    
    # قناع دائري
    mask = Image.new('L', (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size, size), fill=255)
    
    # الصورة الدائرية
    circular = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    circular.paste(img, (0, 0), mask)
    
    # إضافة إطار ملون مع توهج
    border = Image.new('RGBA', (size + 20, size + 20), (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border)
    
    # توهج خارجي
    for i in range(8, 0, -1):
        alpha = 60 - i * 5
        draw_border.ellipse((10 - i, 10 - i, size + 10 + i, size + 10 + i),
                           outline=(border_color[0], border_color[1], border_color[2], alpha), width=2)
    
    # الإطار الرئيسي
    draw_border.ellipse((10, 10, size + 10, size + 10), outline=border_color, width=4)
    draw_border.ellipse((14, 14, size + 6, size + 6), outline=(255, 255, 255, 150), width=1)
    
    border.paste(circular, (10, 10), circular)
    return border

def create_fancy_background():
    """خلفية فخمة متدرجة الألوان مع تأثيرات"""
    width, height = 1200, 1200
    img = Image.new('RGBA', (width, height), (0, 0, 0, 255))
    draw = ImageDraw.Draw(img)
    
    # تدرج لوني فخم (بنفسجي إلى أزرق سماوي)
    for y in range(height):
        ratio = y / height
        r = int(40 + ratio * 80)
        g = int(10 + ratio * 100)
        b = int(70 + ratio * 150)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255), width=1)
    
    # دوائر زخرفية متعددة الألوان
    colors = [
        (255, 100, 100, 40), (100, 255, 100, 40), (100, 100, 255, 40),
        (255, 255, 100, 40), (255, 100, 255, 40), (100, 255, 255, 40),
        (255, 200, 100, 40), (200, 100, 255, 40)
    ]
    
    for i, color in enumerate(colors):
        r = 150 + i * 70
        draw.ellipse((width//2 - r, height//2 - r, width//2 + r, height//2 + r),
                    outline=color, width=3)
    
    # خطوط زخرفية (شبكة)
    for i in range(0, width, 50):
        draw.line([(i, 0), (i, height)], fill=(255, 255, 255, 15), width=1)
        draw.line([(0, i), (width, i)], fill=(255, 255, 255, 15), width=1)
    
    # نجوم متلألئة
    for _ in range(200):
        x = random.randint(0, width)
        y = random.randint(0, height)
        intensity = random.randint(100, 255)
        draw.point((x, y), fill=(intensity, intensity, intensity, 255))
    
    # خطوط مضيئة متقاطعة
    draw.line([(0, height//2), (width, height//2)], fill=(0, 255, 255, 30), width=2)
    draw.line([(width//2, 0), (width//2, height)], fill=(255, 0, 255, 30), width=2)
    
    return img

@app.route('/outfit-image', methods=['GET'])
def outfit_image():
    uid = request.args.get('uid')
    key = request.args.get('key')

    if not uid:
        return jsonify({'error': 'Missing uid parameter'}), 400
    if key != main_key:
        return jsonify({'error': 'Invalid or missing API key'}), 403

    # جلب بيانات اللاعب
    data = fetch_player_info(uid)
    if not data:
        return jsonify({'error': 'Failed to fetch player info'}), 500

    # استخراج البيانات
    profile_info = data.get("profileInfo", {})
    clothes_ids = profile_info.get("clothes", [])
    equipped_skills = profile_info.get("equipedSkills", [])
    pet_id = data.get("petInfo", {}).get("id")
    weapon_id = data.get("basicInfo", {}).get("weaponSkinShows", [None])[0]
    player_name = data.get("basicInfo", {}).get("nickname", "WARRIOR")

    logger.info(f"Player: {player_name}, Clothes: {len(clothes_ids)} items")

    # ترتيب الملابس حسب النوع
    required_codes = ["211", "214", "203", "204", "205", "208"]
    fallback_ids = ["211000000", "214000000", "203000077", "204000345", "205000070", "208000000"]
    
    used_ids = set()
    futures = []

    def fetch_outfit(idx, code):
        matched = None
        for oid in clothes_ids:
            if str(oid).startswith(code) and oid not in used_ids:
                matched = oid
                used_ids.add(oid)
                break
        if matched is None:
            matched = fallback_ids[idx]
        url = f'{INFO_URL}/{matched}.png'
        return fetch_image(url, size=(130, 130))

    for idx, code in enumerate(required_codes):
        futures.append(executor.submit(fetch_outfit, idx, code))

    # إنشاء الخلفية
    background = create_fancy_background()
    W, H = 1200, 1200
    draw = ImageDraw.Draw(background)

    # محاولة تحميل الخطوط
    try:
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 55)
        big_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 38)
        name_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 32)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 20)
        watermark_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 28)
    except:
        title_font = ImageFont.load_default()
        big_font = ImageFont.load_default()
        name_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
        watermark_font = ImageFont.load_default()

    # ===== DRAGONX1M@ في أعلى الصورة =====
    watermark = "⚡ DRAGONX1M@ ⚡"
    # ظل للخط
    for offset in range(4, 0, -1):
        draw.text((W//2 - 140 + offset, 20 + offset), watermark,
                 fill=(50, 50, 100, 120), font=watermark_font)
    draw.text((W//2 - 140, 20), watermark,
             fill=(255, 215, 0, 255), font=watermark_font)  # لون ذهبي
    
    # خط زخرفي تحت الـ watermark
    draw.line([(W//2 - 200, 65), (W//2 + 200, 65)], fill=(255, 215, 0, 200), width=3)

    # عنوان رئيسي
    title = "⚡ ELITE OUTFIT ⚡"
    for offset in range(3, 0, -1):
        draw.text((W//2 - 160 + offset, 85 + offset), title,
                 fill=(100, 100, 200, 100), font=title_font)
    draw.text((W//2 - 160, 85), title, fill=(0, 255, 255, 255), font=title_font)

    # إحداثيات الدوائر (مركز كل دائرة)
    circles = [
        (250, 280, (0, 255, 255), "HELMET"),   # قبعة
        (250, 500, (255, 0, 255), "VISOR"),    # وجه
        (250, 720, (255, 255, 0), "ARMOR"),    # قميص
        (950, 280, (0, 255, 0), "LEG"),        # بنطلون
        (950, 500, (255, 100, 0), "BOOTS"),    # حذاء
        (950, 720, (255, 0, 255), "PET"),      # حيوان
    ]

    # لصق صور الملابس في دوائرها
    for idx, future in enumerate(futures):
        if idx >= len(circles):
            break
        x, y, color, name = circles[idx]
        img = future.result()
        if img:
            circular = make_circle_with_border(img, 130, color)
            background.paste(circular, (x - 75, y - 75), circular)
        
        # اسم القطعة تحت الدائرة
        try:
            bbox = draw.textbbox((0, 0), name, font=small_font)
            text_w = bbox[2] - bbox[0]
        except:
            text_w = len(name) * 10
        draw.text((x - text_w//2, y + 90), name, fill=color, font=small_font)

    # السلاح (دائرة في أسفل المنتصف)
    weapon_x, weapon_y = W//2, 950
    weapon_color = (255, 50, 100)
    
    if weapon_id:
        weapon_url = f'{INFO_URL}/weapon_{weapon_id}.png'
        weapon_img = fetch_image(weapon_url, size=(180, 100))
        if not weapon_img:
            weapon_url = f'{INFO_URL}/{weapon_id}.png'
            weapon_img = fetch_image(weapon_url, size=(180, 100))
        if weapon_img:
            # إطار للسلاح
            weapon_border = Image.new('RGBA', (200, 130), (0, 0, 0, 0))
            wb_draw = ImageDraw.Draw(weapon_border)
            wb_draw.rectangle([(10, 10), (190, 120)], outline=weapon_color, width=4)
            wb_draw.rectangle([(15, 15), (185, 115)], outline=(255, 255, 255, 100), width=1)
            weapon_border.paste(weapon_img, (20, 15), weapon_img)
            background.paste(weapon_border, (weapon_x - 100, weapon_y - 65), weapon_border)
    
    draw.text((weapon_x - 35, weapon_y + 50), "WEAPON", fill=weapon_color, font=small_font)

    # الحيوان الأليف (إذا لم يتم لصقه)
    if pet_id and pet_id not in used_ids:
        pet_url = f'{INFO_URL}/{pet_id}.png'
        pet_img = fetch_image(pet_url, size=(120, 120))
        if pet_img:
            pet_circle = make_circle_with_border(pet_img, 120, (255, 100, 200))
            background.paste(pet_circle, (950 - 70, 720 - 70), pet_circle)

    # صورة الـ Avatar الرئيسية
    avatar_id = "406"
    for skill in equipped_skills:
        if str(skill).endswith("06"):
            avatar_id = str(skill)
            break
    
    avatar_url = f'https://characteriroxmar.vercel.app/chars?id={avatar_id}'
    avatar_img = fetch_image(avatar_url, size=(380, 450))
    if avatar_img:
        ax = (W - avatar_img.width) // 2
        ay = 360
        background.paste(avatar_img, (ax, ay), avatar_img)
        
        # إطار فخم حول الـ Avatar
        draw.rectangle([ax - 12, ay - 12, ax + avatar_img.width + 12, ay + avatar_img.height + 12],
                      outline=(0, 255, 255, 200), width=4)
        for i in range(3):
            draw.rectangle([ax - 12 + i, ay - 12 + i, ax + avatar_img.width + 12 - i, ay + avatar_img.height + 12 - i],
                          outline=(255, 255, 255, 60), width=1)

    # اسم اللاعب بتأثير فخم
    name_text = f"🏆 {player_name.upper()} 🏆"
    for offset in range(3, 0, -1):
        draw.text((W//2 - len(name_text)*10 + offset, H - 85 + offset),
                 name_text, fill=(100, 100, 200, 120), font=name_font)
    draw.text((W//2 - len(name_text)*10, H - 85),
             name_text, fill=(255, 215, 0, 255), font=name_font)
    
    # خطوط زخرفية تحت الاسم
    draw.line([(W//2 - 250, H - 45), (W//2 + 250, H - 45)], fill=(0, 255, 255, 200), width=3)
    draw.line([(W//2 - 240, H - 42), (W//2 + 240, H - 42)], fill=(255, 255, 255, 100), width=1)

    # تذييل في أسفل اليمين
    footer = "@DRAGONX1M"
    draw.text((W - 180, H - 35), footer, fill=(255, 255, 255, 150), font=small_font)

    # حفظ الصورة
    img_io = BytesIO()
    background.save(img_io, 'PNG')
    img_io.seek(0)
    
    logger.info("✅ Fancy Outfit Image Created Successfully!")
    return send_file(img_io, mimetype='image/png')

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': '✅ DRAGONX1M@ ELITE OUTFIT API',
        'creator': 'DRAGONX1M@',
        'version': '3.0',
        'style': 'Fancy Cyber Design',
        'endpoints': {
            '/outfit-image': 'GET - Generate outfit image'
        },
        'parameters': {
            'uid': 'Required - Player UID',
            'key': 'Required - API key (DRAGON-TEAM)'
        },
        'example': 'https://your-domain.com/outfit-image?uid=2129828082&key=DRAGON-TEAM',
        'features': [
            '🔥 تصميم فخم جداً',
            '🎨 ألوان نيون متعددة',
            '💫 تأثيرات توهج 3D',
            '👑 اسم اللاعب بتأثير ذهبي',
            '⚡ شعار DRAGONX1M@',
            '🎭 7 دوائر ملونة للملابس والسلاح'
        ]
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False, threaded=True)
