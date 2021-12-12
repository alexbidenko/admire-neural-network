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
        result = sorted(random.choice(items)["sizes"], key=lambda x: x["height"], reverse=True)[0]["url"]
        return result
    return None


def resizer(image_name):
    pil_image = Image.open(image_name).resize((1000, 1000)).convert('RGB')
    return pil_image

def get_random_style():
    random_tags = random.choice(os.listdir(f"imagereturner/styles/"))
    random_style = random.choice(os.listdir(f"imagereturner/styles/{random_tags}"))
    random_style_path = f"imagereturner/styles/{random_tags}/{random_style}"
    return random_style_path


def get_label(phrase):
    font_size = random.randint(100, 300)
    random_font_file = random.choice(os.listdir("imagereturner/fonts"))
    print(random_font_file)
    font = ImageFont.truetype(f"imagereturner/fonts/{random_font_file}", font_size)
    string_size_in_pixels = font.getsize(phrase)
    print("start size", string_size_in_pixels)
    label = Image.new(size=string_size_in_pixels, mode="RGB", color="white")
    ImageDraw.Draw(label).text((0, 0), phrase,
                               (0, 0, 0),
                               font=font)
    name = f"trash/text{uuid.uuid4()}.png"
    label.save(name)
    generated_image = style_transfer(name, get_random_style(), if_text=True)
    generated_image.putalpha(255)
    generated_image.convert("RGBA") #.quantize(method=2)
    datas = generated_image.getdata()

    newData = []
    for item in datas:
        if item[0] in range(150, 255) or item[1] in range(150, 255) or item[2] in range(150, 255):
            newData.append((255, 255, 255, 0))
        else:
            newData.append(item)
    generated_image.putdata(newData)
    datas = generated_image.getdata()
    random_color = (random.randint(0, 255), random.randint(0, 255), random.randint(0, 255), 255)
    newData = []
    for item in datas:
        if item[0] != 255 and item[1] != 255 and item[2] != 255:
            newData.append(random_color)
        else:
            newData.append(item)
    generated_image.putdata(newData)
    generated_image.save(name)
    new_image = Image.open(name).resize(string_size_in_pixels)
    print("new size", new_image.size)
    return [new_image, new_image.size]



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
        result = vk_search(phrase, access_token)
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
            #generated_image.putalpha(256)
            phrase_label, size = get_label(phrase)
            print(size)
            if size[0] > 1000:
                wight = random.randint(800, 900)
                height = int(size[1] * wight / size[0])
                phrase_label = phrase_label.resize((wight, height))
                x, y = random.randint(0, 1000 - wight), random.randint(0, 1000 - height)
                print(x, y, "cords")
                generated_image.paste(phrase_label, (x, y),
                                phrase_label.convert("RGBA"))
            else:
                x, y = random.randint(0, 1000 - size[0]), random.randint(0, 1000 - size[1])
                print(x, y, "cords")
                generated_image.paste(phrase_label, (x, y),
                                phrase_label.convert("RGBA"))

            datas = generated_image.getdata()
            newData = []
            for i in range(len(datas)):
                item = datas[i]
                if item[0] in range(220, 256) and item[1] in range(220, 256) and item[2] in range(220, 256):
                    step = 1
                    while True:
                        try:
                            next_item = datas[i+step]
                            if not (next_item[0] in range(220, 256) and next_item[1] in range(220, 256) and next_item[2] in range(220, 256)):
                                newData.append((next_item[0], next_item[1], next_item[2]))
                                break
                            else:
                                step +=1
                        except Exception as ex:
                            print(ex)
                            break
                else:
                    newData.append(item)
            generated_image.putdata(newData)
            generated_image.save(name)
            return FileResponse(open(name, "rb"))
        return HttpResponse(status=404)
