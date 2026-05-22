from flask import Flask, request, jsonify, send_file
import requests
from PIL import Image, ImageDraw, ImageFont
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor
import os
import logging
import urllib3
import random

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
main_key = "DRAGON-TEAM"
executor = ThreadPoolExecutor(max_workers=5)

INFO_URL = "https://cdn.jsdelivr.net/gh/ShahGCreator/icon@main/PNG"

def fetch_player_info(uid):
    url = f'https://otman-info.vercel.app/player-info?uid={uid}'
    try:
        response = requests.get(url, timeout=10, verify=False)
        if response.status_code == 200:
            return response.json()
    except:
        pass
    return None

def fetch_image(image_url, size=None):
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(image_url, timeout=10, verify=False, headers=headers)
        if response.status_code == 200:
            img = Image.open(BytesIO(response.content)).convert("RGBA")
            if size:
                img = img.resize(size, Image.Resampling.LANCZOS)
            return img
    except Exception as e:
        logger.error(f"Error: {e}")
    return None

def make_circle_with_border(image, size, border_color):
    if image is None:
        return None
    img = image.resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new('L', (size, size), 0)
    draw_mask = ImageDraw.Draw(mask)
    draw_mask.ellipse((0, 0, size, size), fill=255)
    circular = Image.new('RGBA', (size, size), (0, 0, 0, 0))
    circular.paste(img, (0, 0), mask)
    border = Image.new('RGBA', (size + 16, size + 16), (0, 0, 0, 0))
    draw_border = ImageDraw.Draw(border)
    draw_border.ellipse((8, 8, size + 8, size + 8), outline=border_color, width=4)
    border.paste(circular, (8, 8), circular)
    return border

def create_background():
    width, height = 1200, 1200
    img = Image.new('RGBA', (width, height), (20, 10, 40, 255))
    draw = ImageDraw.Draw(img)
    for y in range(height):
        ratio = y / height
        r = int(40 + ratio * 60)
        g = int(10 + ratio * 80)
        b = int(70 + ratio * 150)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255), width=1)
    return img

@app.route('/outfit-image', methods=['GET'])
def outfit_image():
    uid = request.args.get('uid')
    key = request.args.get('key')
    if not uid:
        return jsonify({'error': 'Missing uid'}), 400
    if key != main_key:
        return jsonify({'error': 'Invalid key'}), 403
    data = fetch_player_info(uid)
    if not data:
        return jsonify({'error': 'Failed to fetch'}), 500
    profile_info = data.get("profileInfo", {})
    clothes_ids = profile_info.get("clothes", [])
    equipped_skills = profile_info.get("equipedSkills", [])
    pet_id = data.get("petInfo", {}).get("id")
    weapon_id = data.get("basicInfo", {}).get("weaponSkinShows", [None])[0]
    player_name = data.get("basicInfo", {}).get("nickname", "WARRIOR")
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
    background = create_background()
    W, H = 1200, 1200
    draw = ImageDraw.Draw(background)
    try:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    except:
        title_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    circles = [
        (250, 280, (0, 255, 255), "HELMET"),
        (250, 500, (255, 0, 255), "VISOR"),
        (250, 720, (255, 255, 0), "ARMOR"),
        (950, 280, (0, 255, 0), "LEG"),
        (950, 500, (255, 100, 0), "BOOTS"),
        (950, 720, (255, 0, 255), "PET"),
    ]
    for idx, future in enumerate(futures):
        if idx >= len(circles):
            break
        x, y, color, name = circles[idx]
        img = future.result()
        if img:
            circular = make_circle_with_border(img, 130, color)
            background.paste(circular, (x - 75, y - 75), circular)
    weapon_x, weapon_y = W//2, 950
    if weapon_id:
        weapon_url = f'{INFO_URL}/weapon_{weapon_id}.png'
        weapon_img = fetch_image(weapon_url, size=(150, 90))
        if weapon_img:
            background.paste(weapon_img, (weapon_x - 75, weapon_y - 45), weapon_img)
    avatar_id = "406"
    for skill in equipped_skills:
        if str(skill).endswith("06"):
            avatar_id = str(skill)
            break
    avatar_url = f'https://characteriroxmar.vercel.app/chars?id={avatar_id}'
    avatar_img = fetch_image(avatar_url, size=(340, 400))
    if avatar_img:
        ax = (W - avatar_img.width) // 2
        ay = 380
        background.paste(avatar_img, (ax, ay), avatar_img)
    img_io = BytesIO()
    background.save(img_io, 'PNG')
    img_io.seek(0)
    return send_file(img_io, mimetype='image/png')

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        'status': '✅ OUTFIT API WORKING!',
        'creator': 'DRAGONX1M@',
        'endpoint': '/outfit-image?uid=ID&key=DRAGON-TEAM'
    })

# هذا السطر مهم جداً لـ Vercel
app = app