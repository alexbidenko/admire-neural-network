from django.http import JsonResponse, HttpResponse
from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from django.http import FileResponse
from .neuro import style_transfer
import uuid
import random
import requests
import json
import os
import platform
import time

access_token = "94b8c4c694b8c4c694b8c4c68894c2ab6e994b894b8c4c6f50b01863e04926b911fb650"


def vk_search(phrase, token):
    result = requests.get(url="https://api.vk.com/method/photos.search", params={
        'q': f"{phrase} -цена -руб -₽ -оплата",
        'access_token': token,
        'v': '5.81',
    })
    if items := json.loads(result.text)["response"]["items"]:
        random_item = random.choice(items)
        text = random_item["text"]
        item = sorted(random_item["sizes"], key=lambda x: x["height"], reverse=True)
        item = item[0]
        result = item["url"]
        return result, text
    return None, None


def resizer(image_name):
    pil_image = Image.open(image_name).resize((1000, 1000)).convert('RGB')
    return pil_image

def get_random_style():
    random_tags = random.choice(os.listdir(f"imagereturner/styles/"))
    random_style = random.choice(os.listdir(f"imagereturner/styles/{random_tags}"))
    random_style_path = f"imagereturner/styles/{random_tags}/{random_style}"
    return random_style_path


def get_label(phrase):
    phrase = phrase.split()
    len_phrase = len(phrase)
    random_num = random.randint(2, 5) if len_phrase>=5 else random.randint(2, len_phrase)
    phrase = " ".join(random.choices(phrase, k=random_num))
    font_size = random.randint(100, 300)
    random_font_file = random.choice(os.listdir("imagereturner/fonts"))
    print(random_font_file)
    font = ImageFont.truetype(f"imagereturner/fonts/{random_font_file}", font_size)
    string_size_in_pixels = font.getsize(phrase)
    label = Image.new(size=string_size_in_pixels, mode="RGBA")
    ImageDraw.Draw(label).text((0, 0), phrase,
                               (random.randint(0, 255), random.randint(0,255), random.randint(0, 255)),
                               font=font)
    return [label, string_size_in_pixels]


def creation_date(path_to_file):
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            return stat.st_mtime


def delete_old_files(filename):
    file_path = "trash/" + filename
    date_in_ms = creation_date(file_path)
    if int(time.time()) - date_in_ms > 3600:
        os.remove(file_path)
    return date_in_ms


def return_tags(request):
    if request.method == "GET":
        tags = [
            {
                "value": "abstractions",
                "label": "Абстракции"
            },
            {
                "value": "ar_deco",
                "label": "Ар-деко"
            },
            {
                "value": "bosch",
                "label": "Босх"
            },
            {
                "value": "food",
                "label": "Съедобный"
            },
            {
                "value": "giger",
                "label": "Эрото-механика"
            },
            {
                "value": "medieval",
                "label": "Средневековый"
            },
            {
                "value": "ornaments",
                "label": "Этнические узоры"
            },
            {
                "value": "pop_art",
                "label": "Поп-арт"
            },
            {
                "value": "van_goh",
                "label": "Импрессионизм"
            },
        ]
        return JsonResponse(tags, safe=False)


def return_image(request):
    if request.method == "POST":
        downloaded_files = os.listdir("trash")
        list(map(delete_old_files, downloaded_files))
        request = json.loads(request.body)
        phrase = request["phrase"]
        print(phrase)
        tags = request["tags"]
        result, text = vk_search(phrase, access_token)
        if result:
            img_data = requests.get(result).content
            name = f"trash/{uuid.uuid4()}.png"
            with open(name, 'wb') as handler:
                handler.write(img_data)
            pil_image = resizer(image_name=name)
            pil_image.save(name)
            print(tags)
            if tags:
                tags = tags[0]
                random_style = random.choice(os.listdir(f"imagereturner/styles/{tags}"))
                random_style_path = f"imagereturner/styles/{tags}/{random_style}"
            else:
                random_style_path = get_random_style()
            print(random_style_path)
            generated_image = style_transfer(name, random_style_path)
            phrase_label, size = get_label(text)
            if size[0] > 1000:
                wight = random.randint(800, 900)
                height = int(size[1] * wight / size[0])
                phrase_label = phrase_label.resize((wight, height))
                generated_image.paste(phrase_label, (random.randint(0, 1000 - wight), random.randint(0, 1000 - height)),
                                phrase_label.convert("RGBA"))
            else:
                generated_image.paste(phrase_label, (random.randint(0, 1000 - size[0]), random.randint(0, 1000 - size[1])),
                                phrase_label.convert("RGBA"))
            generated_image.save(name)
            return FileResponse(open(name, "rb"))
        return HttpResponse(status=404)
